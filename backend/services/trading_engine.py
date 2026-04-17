"""
Core Trading Engine — runs the AI-driven strategy loop continuously during market hours.

Key fixes vs original:
- Imports `manager` (not `ws_manager`) from routes.websocket
- Updates daily PnL in risk manager after every trade close
- Clears _active_engines entry + updates BotSession on EOD close
- Passes totp_secret to broker factory
- Uses claude-3-5-haiku-latest correctly
"""
import asyncio
import logging
import uuid
from datetime import datetime, date, time, timedelta
from typing import Dict, List, Optional

import pytz
from sqlalchemy.orm import Session

from database.session import SessionLocal
from database.models import (
    BotSession, BotStatus, Trade, TradeStatus,
    TradingConfiguration, SystemLog, TradeSignal,
)
from services.broker_connector import create_broker
from services.claude_service import ClaudeService
from services.risk_manager import RiskManager
from services.email_service import EmailService
from services.indicators import calculate_all_indicators, build_narrative
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
IST = pytz.timezone("Asia/Kolkata")

DEFAULT_SYMBOLS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
    "SBIN", "TITAN", "BHARTIARTL", "WIPRO", "MARUTI",
]


def _get_ws_manager():
    """Lazy import to avoid circular dependencies."""
    from routes.websocket import manager
    return manager


def _get_active_engines() -> dict:
    """Get the canonical engines registry from bot_routes."""
    from routes.bot_routes import _active_engines
    return _active_engines


class TradingEngine:
    """
    One instance per user per trading session.
    Registered in bot_routes._active_engines[user_id].
    """

    def __init__(self, config: TradingConfiguration, session_id: str, user_id: str):
        self.config = config
        self.session_id = session_id
        self.user_id = user_id

        # ── Broker ──────────────────────────────────────────────
        self.broker = create_broker(
            broker_type=config.broker_type,
            api_key=config.broker_api_key or "",
            api_secret=config.broker_api_secret or "",
            access_token=config.broker_access_token or "",
            totp_secret=getattr(config, "broker_totp_secret", "") or "",
            balance=config.account_balance,
        )

        # ── AI brain ────────────────────────────────────────────
        self.claude: Optional[ClaudeService] = None
        try:
            self.claude = ClaudeService()
        except Exception as e:
            logger.warning(f"Claude unavailable: {e}. Running without AI signals.")

        self.risk_manager = RiskManager(config)
        self.email_service = EmailService(to_email=config.alert_email or "")

        # ── State ───────────────────────────────────────────────
        # open_trades: {symbol: {"trade_id", "entry", "stop_loss", "target", "signal", "qty"}}
        self.open_trades: Dict[str, dict] = {}
        self.is_running: bool = False
        self.is_paused: bool = False
        self.last_update: Optional[str] = None
        self.engine_id = str(uuid.uuid4())
        self._monitor_task: Optional[asyncio.Task] = None

    # ─────────────────────────────────────────────────────────
    # Main loop
    # ─────────────────────────────────────────────────────────
    async def run_trading_loop(self):
        self.is_running = True

        # Start position monitor in background
        self._monitor_task = asyncio.create_task(self._run_monitoring_loop())

        # Start Zerodha WebSocket if applicable
        if self.config.broker_type == "zerodha":
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, self.broker.start_websocket)
                self.broker.subscribe_symbols(self._get_symbols())
            except Exception as e:
                logger.warning(f"Zerodha WS start failed: {e}")

        await self._log("info", "bot_started", "🤖 Trading bot started")

        while self.is_running:
            try:
                if self.is_paused:
                    await asyncio.sleep(10)
                    continue

                if not self._is_market_open():
                    await self._log("info", "market_closed", "Market closed — waiting…")
                    await asyncio.sleep(60)
                    continue

                if self._is_near_market_close():
                    await self._log("info", "eod_exit", "⏰ Near market close — closing all positions")
                    await self.close_all_positions()
                    await self._finalize_session("EOD")
                    break

                await self._log("info", "cycle_start", "🔄 Analysis cycle started")

                # ── Strategy cycle ─────────────────────────────
                market_data = await self._collect_market_data()
                if not market_data:
                    await self._log("warning", "no_data", "No market data collected — skipping cycle")
                    await asyncio.sleep(60)
                    continue

                features = self._engineer_features(market_data)

                signals = []
                if self.claude and features:
                    try:
                        signals = self.claude.get_signals(features, self.config)
                        await self._log(
                            "info", "signals_received",
                            f"📊 Claude returned {len(signals)} signals for {len(features)} symbols"
                        )
                    except Exception as e:
                        await self._log("error", "claude_error", f"Claude API error: {e}")

                for signal in signals:
                    if signal["signal"] in ("HOLD", "EXIT"):
                        continue
                    allowed, reason = self.risk_manager.can_execute(signal)
                    if allowed:
                        await self._execute_trade(signal)
                    else:
                        await self._log(
                            "warning", "signal_skipped",
                            f"⚠️ {signal['symbol']} skipped: {reason}"
                        )

                # Update metrics after cycle
                await self._refresh_daily_pnl()
                self.last_update = datetime.now(IST).isoformat()
                await self._broadcast_metrics()

                interval = self.config.analysis_interval_minutes * 60
                await self._log("info", "cycle_done", f"✅ Cycle done. Next in {self.config.analysis_interval_minutes}m")
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                err = f"Engine error: {e}"
                logger.exception(err)
                await self._log("error", "engine_error", f"❌ {err}")
                await self.email_service.bot_error(err)
                await asyncio.sleep(30)

        await self._log("info", "bot_stopped", "🛑 Trading bot stopped")

        # Cancel monitoring
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()

    # ─────────────────────────────────────────────────────────
    # Data
    # ─────────────────────────────────────────────────────────
    async def _collect_market_data(self) -> dict:
        symbols = self._get_symbols()
        market_data = {}
        for symbol in symbols:
            try:
                candles = self.broker.get_ohlcv(symbol, bars=100, interval="5minute")
                current_price = self.broker.get_price(symbol)
                if candles and current_price > 0:
                    market_data[symbol] = {
                        "candles": candles,
                        "current_price": current_price,
                    }
                    logger.debug(f"Fetched {len(candles)} candles for {symbol} @ ₹{current_price}")
            except Exception as e:
                logger.warning(f"Data collection failed for {symbol}: {e}")
        return market_data

    def _engineer_features(self, market_data: dict) -> dict:
        features = {}
        for symbol, data in market_data.items():
            try:
                candles = data["candles"]
                price = data["current_price"]
                indicators = calculate_all_indicators(candles)
                narrative = build_narrative(symbol, price, indicators)
                features[symbol] = {
                    "current_price": price,
                    "indicators": indicators,
                    "narrative": narrative,
                }
            except Exception as e:
                logger.warning(f"Feature engineering failed for {symbol}: {e}")
        return features

    # ─────────────────────────────────────────────────────────
    # Trade execution
    # ─────────────────────────────────────────────────────────
    async def _execute_trade(self, signal: dict):
        symbol = signal["symbol"]
        if symbol in self.open_trades:
            await self._log("info", "already_open", f"{symbol} already has open position — skipping")
            return

        entry = signal["entry_level"]
        sl = signal.get("stop_loss") or self.risk_manager.suggest_stop_loss(
            signal["signal"], entry, None
        )
        tgt = signal.get("target") or self.risk_manager.suggest_target(
            signal["signal"], entry, sl
        )

        if sl <= 0 or tgt <= 0:
            await self._log("warning", "bad_levels", f"{symbol}: invalid SL/target in signal — skipping")
            return

        qty = self.risk_manager.calculate_position_size(entry, sl)
        if qty <= 0:
            await self._log("warning", "bad_qty", f"{symbol}: calculated qty=0 — skipping")
            return

        # Place order
        order = self.broker.place_order(symbol, signal["signal"], qty, "MARKET", entry)
        if order.get("status") == "FAILED":
            await self._log("error", "order_failed", f"❌ Order failed for {symbol}: {order.get('error')}")
            return

        # Persist to DB
        db = SessionLocal()
        try:
            trade = Trade(
                user_id=self.user_id,
                bot_session_id=self.session_id,
                symbol=symbol,
                signal=signal["signal"],
                entry_price=entry,
                stop_loss=sl,
                target=tgt,
                quantity=qty,
                confidence=signal["confidence"],
                claude_reasoning=signal.get("reasoning", ""),
                main_order_id=order.get("order_id", ""),
                status=TradeStatus.OPEN,
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)

            self.open_trades[symbol] = {
                "trade_id": trade.id,
                "entry": entry,
                "stop_loss": sl,
                "target": tgt,
                "signal": signal["signal"],
                "qty": qty,
                "symbol": symbol,
            }
        finally:
            db.close()

        self.risk_manager.update_open_positions(len(self.open_trades))

        await self._log(
            "info", "trade_opened",
            f"🟢 OPENED {signal['signal']} {symbol} @ ₹{entry:.2f} | "
            f"SL ₹{sl:.2f} | Target ₹{tgt:.2f} | Qty {qty} | Conf {signal['confidence']:.0f}%"
        )
        await self.email_service.trade_opened(symbol, signal["signal"], entry, signal["confidence"])
        await _get_ws_manager().send_to_user(self.user_id, {
            "type": "trade_update",
            "data": {
                "action": "opened",
                "symbol": symbol,
                "signal": signal["signal"],
                "entry": entry,
                "qty": qty,
            },
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def exit_trade(self, trade_id: str, reason: str = "MANUAL_EXIT", exit_price: float = 0):
        """Exit a single trade by trade_id."""
        db = SessionLocal()
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if not trade or trade.status != TradeStatus.OPEN:
                return

            if exit_price <= 0:
                exit_price = self.broker.get_price(trade.symbol)
            if exit_price <= 0:
                exit_price = trade.entry_price  # last resort fallback

            # Place exit order
            opp = "SELL" if "BUY" in trade.signal.value else "BUY"
            self.broker.place_order(trade.symbol, opp, trade.quantity, "MARKET")

            pnl = self._calc_pnl(trade.signal, trade.entry_price, exit_price, trade.quantity)
            trade.exit_price = exit_price
            trade.exit_reason = reason
            trade.exit_time = datetime.utcnow()
            trade.status = TradeStatus.CLOSED
            trade.pnl = pnl
            trade.pnl_percent = (pnl / (trade.entry_price * trade.quantity)) * 100 if trade.entry_price else 0
            db.commit()

            self.open_trades.pop(trade.symbol, None)
            self.risk_manager.update_open_positions(len(self.open_trades))

            # Refresh daily PnL so risk limits stay accurate
            await self._refresh_daily_pnl()

            emoji = "🟢" if pnl >= 0 else "🔴"
            await self._log(
                "info", "trade_closed",
                f"{emoji} CLOSED {trade.symbol} [{reason}] @ ₹{exit_price:.2f} | P&L ₹{pnl:+.2f}"
            )
            await self.email_service.trade_closed(trade.symbol, trade.signal.value, exit_price, pnl, reason)

        finally:
            db.close()

        await _get_ws_manager().send_to_user(self.user_id, {
            "type": "trade_update",
            "data": {"action": "closed", "trade_id": trade_id, "reason": reason},
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def close_all_positions(self) -> list:
        """Close every open position. Returns list of closed symbols."""
        closed = []
        for symbol, pos in list(self.open_trades.items()):
            await self.exit_trade(pos["trade_id"], reason="EOD_CLOSE")
            closed.append(symbol)
        return closed

    # ─────────────────────────────────────────────────────────
    # Monitoring loop (runs every 5 seconds)
    # ─────────────────────────────────────────────────────────
    async def _run_monitoring_loop(self):
        """Check SL/Target hits continuously."""
        while self.is_running:
            try:
                if not self.is_paused and self._is_market_open():
                    await self._check_sl_target()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Monitor loop error: {e}")
                await asyncio.sleep(10)

    async def _check_sl_target(self):
        for symbol, pos in list(self.open_trades.items()):
            try:
                price = self.broker.get_price(symbol)
                if not price or price <= 0:
                    continue

                sl = pos["stop_loss"]
                tgt = pos["target"]
                sig = pos["signal"]

                if "BUY" in sig:
                    if price <= sl:
                        await self.exit_trade(pos["trade_id"], "SL_HIT", price)
                    elif price >= tgt:
                        await self.exit_trade(pos["trade_id"], "TARGET_HIT", price)
                else:  # SELL
                    if price >= sl:
                        await self.exit_trade(pos["trade_id"], "SL_HIT", price)
                    elif price <= tgt:
                        await self.exit_trade(pos["trade_id"], "TARGET_HIT", price)

            except Exception as e:
                logger.warning(f"SL/Target check error for {symbol}: {e}")

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────
    def pause(self):
        self.is_paused = True
        logger.info(f"Engine paused for user {self.user_id}")

    def resume(self):
        self.is_paused = False
        logger.info(f"Engine resumed for user {self.user_id}")

    def stop(self):
        self.is_running = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        logger.info(f"Engine stopped for user {self.user_id}")

    def _get_symbols(self) -> list[str]:
        if self.config.symbol_selection_mode == "manual" and self.config.manual_symbols:
            return list(self.config.manual_symbols)
        return DEFAULT_SYMBOLS

    def _is_market_open(self) -> bool:
        now = datetime.now(IST)
        if now.weekday() >= 5:
            return False
        return time(9, 15) <= now.time() <= time(15, 30)

    def _is_near_market_close(self) -> bool:
        return datetime.now(IST).time() >= time(15, 25)

    @staticmethod
    def _calc_pnl(signal, entry: float, exit_price: float, qty: int) -> float:
        val = signal.value if hasattr(signal, "value") else str(signal)
        result = (exit_price - entry) * qty if "BUY" in val else (entry - exit_price) * qty
        return round(result, 2)

    def _get_todays_pnl(self) -> float:
        db = SessionLocal()
        try:
            from sqlalchemy import func
            today = date.today()
            start = datetime.combine(today, datetime.min.time())
            res = (
                db.query(func.sum(Trade.pnl))
                .filter(
                    Trade.user_id == self.user_id,
                    Trade.status == TradeStatus.CLOSED,
                    Trade.exit_time >= start,
                )
                .scalar()
            )
            return float(res or 0)
        finally:
            db.close()

    async def _refresh_daily_pnl(self):
        pnl = self._get_todays_pnl()
        self.risk_manager.update_daily_pnl(pnl)
        return pnl

    async def _finalize_session(self, reason: str = "STOPPED"):
        """Mark bot session as stopped in DB and remove from active engines."""
        db = SessionLocal()
        try:
            db.query(BotSession).filter(BotSession.id == self.session_id).update({
                "status": BotStatus.stopped,
                "stopped_at": datetime.utcnow(),
            })
            db.commit()
        finally:
            db.close()

        engines = _get_active_engines()
        engines.pop(self.user_id, None)
        logger.info(f"Session {self.session_id} finalized ({reason})")

    # ─────────────────────────────────────────────────────────
    # Broadcasting
    # ─────────────────────────────────────────────────────────
    async def _log(self, severity: str, event_type: str, message: str):
        db = SessionLocal()
        try:
            db.add(SystemLog(
                user_id=self.user_id,
                event_type=event_type,
                message=message,
                severity=severity,
            ))
            db.commit()
        except Exception as e:
            logger.error(f"DB log failed: {e}")
        finally:
            db.close()

        # Also stream to frontend
        try:
            await _get_ws_manager().send_to_user(self.user_id, {
                "type": "log_event",
                "data": {
                    "event_type": event_type,
                    "message": message,
                    "severity": severity,
                },
                "timestamp": datetime.now(IST).isoformat(),
            })
        except Exception:
            pass

    async def _broadcast_metrics(self):
        try:
            pnl = self._get_todays_pnl()
            await _get_ws_manager().send_to_user(self.user_id, {
                "type": "metrics_update",
                "data": {
                    "open_positions": len(self.open_trades),
                    "daily_pnl": pnl,
                    "last_update": self.last_update,
                },
            })
        except Exception:
            pass
