import asyncio
import logging
import uuid
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional

import pytz
from sqlalchemy.orm import Session

from database.session import SessionLocal
from database.models import BotSession, BotStatus, Trade, TradeStatus, TradingConfiguration, SystemLog, TradeSignal
from services.broker_connector import create_broker
from services.claude_service import ClaudeService
from services.risk_manager import RiskManager
from services.email_service import EmailService
from services.indicators import calculate_all_indicators, build_narrative
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
IST = pytz.timezone("Asia/Kolkata")

DEFAULT_SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "TITAN", "BHARTIARTL"]

# Global registry of active engines
_active_engines = {}

def _get_ws_manager():
    from routes.websocket import manager
    return manager

class TradingEngine:
    """
    Main execution engine. Runs the strategy cycle every N minutes.
    """
    def __init__(self, config: TradingConfiguration, session_id: str, user_id: str):
        self.config = config
        self.session_id = session_id
        self.user_id = user_id

        # Broker selection
        self.broker = create_broker(
            broker_type=config.broker_type,
            api_key=config.broker_api_key,
            api_secret=config.broker_api_secret,
            access_token=config.broker_access_token,
            balance=config.account_balance,
        )

        # AI brain
        self.claude: Optional[ClaudeService] = None
        if settings.anthropic_api_key:
            try:
                self.claude = ClaudeService()
            except Exception as e:
                logger.warning(f"Claude unavailable: {e}. Running without AI signals.")

        self.risk_manager = RiskManager(config)
        self.email_service = EmailService(to_email=config.alert_email)

        self.open_trades: dict[str, dict] = {} 
        self.is_running: bool = False
        self.is_paused: bool = False
        self.last_update: Optional[str] = None
        self.engine_id = str(uuid.uuid4())
        self.monitor_task: Optional[asyncio.Task] = None

    async def run_trading_loop(self):
        self.is_running = True
        
        # Start monitoring in background
        if not self.monitor_task or self.monitor_task.done():
            self.monitor_task = asyncio.create_task(self.run_monitoring_loop())
            
        # Start Zerodha WebSocket if applicable
        if hasattr(self.broker, "start_websocket") and self.config.broker_type == "zerodha":
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.broker.start_websocket)
            # Subscribe to current symbols
            self.broker.subscribe_symbols(self._get_symbols())

        await self._log_event("info", "bot_started", "Trading bot started ✅")

        while self.is_running:
            try:
                if self.is_paused:
                    await asyncio.sleep(10)
                    continue

                if not self._is_market_open():
                    await asyncio.sleep(60)
                    continue

                if self._is_near_market_close():
                    await self._log_event("info", "eod_exit", "Near market close — closing all positions")
                    await self.close_all_positions()
                    self.is_running = False
                    break

                # ── Trading cycle ──────────────────────────
                await self._log_event("info", "cycle_start", "Strategy cycle started…")

                # Step 1: Collect data
                market_data = await self._collect_market_data()

                # Step 2: Feature engineering
                features = self._engineer_features(market_data)

                # Step 3: AI signals
                signals = []
                if self.claude and features:
                    signals = self.claude.get_signals(features, self.config)
                    for s in signals:
                        if s["signal"] != "HOLD":
                            await self._log_event("info", "signal_gen", 
                                f"AI Signal for {s['symbol']}: {s['signal']} (Conf: {s['confidence']}%)")

                # Step 4: Risk validate and execute
                for signal in signals:
                    if signal["signal"] == "HOLD": continue
                    
                    allowed, reason = self.risk_manager.can_execute(signal)
                    if allowed:
                        await self._execute_trade(signal)
                    else:
                        await self._log_event("warning", "signal_skipped", f"{signal['symbol']}: {reason}")

                self.last_update = datetime.now(IST).isoformat()
                await self._broadcast_metrics()

                await asyncio.sleep(self.config.analysis_interval_minutes * 60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                err_msg = f"Engine error: {e}"
                logger.exception(err_msg)
                await self._log_event("error", "engine_error", err_msg)
                await asyncio.sleep(30)

        await self._log_event("info", "bot_stopped", "Trading bot stopped 🛑")

    async def _collect_market_data(self) -> dict:
        symbols = self._get_symbols()
        market_data = {}
        for symbol in symbols:
            try:
                candles = self.broker.get_ohlcv(symbol, bars=100, interval="5minute")
                current_price = self.broker.get_price(symbol)
                if candles:
                    market_data[symbol] = {"candles": candles, "current_price": current_price}
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

    async def _execute_trade(self, signal: dict):
        symbol = signal["symbol"]
        if symbol in self.open_trades:
            return

        entry = signal["entry_level"]
        sl = signal.get("stop_loss", 0)
        tgt = signal.get("target", 0)

        qty = self.risk_manager.calculate_position_size(entry, sl)

        # Place order
        order = self.broker.place_order(symbol, signal["signal"], qty, "MARKET", entry)
        if "error" in order:
            await self._log_event("error", "order_failed", f"Failed to place {symbol}: {order['error']}")
            return

        # DB persistence
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
                "qty": qty
            }
        finally:
            db.close()

        self.risk_manager.update_open_positions(len(self.open_trades))
        self.broker.subscribe_symbols([symbol])

        await self._log_event("info", "trade_opened", f"Opened {signal['signal']} {symbol} @ ₹{entry:.2f}")
        await self.email_service.trade_opened(symbol, signal["signal"], entry, signal["confidence"])
        await self._broadcast_trade_update()

    async def exit_trade(self, trade_id: str, reason: str = "MANUAL_EXIT", exit_price: float = 0):
        db = SessionLocal()
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if not trade or trade.status != TradeStatus.OPEN:
                return
            
            if exit_price <= 0:
                exit_price = self.broker.get_price(trade.symbol)

            # Close on broker
            opp_action = "SELL" if "BUY" in trade.signal.value else "BUY"
            self.broker.place_order(trade.symbol, opp_action, trade.quantity, "MARKET")

            pnl = self._calc_pnl(trade.signal, trade.entry_price, exit_price, trade.quantity)
            trade.exit_price = exit_price
            trade.exit_reason = reason
            trade.exit_time = datetime.utcnow()
            trade.status = TradeStatus.CLOSED
            trade.pnl = pnl
            trade.pnl_percent = pnl / (trade.entry_price * trade.quantity) * 100
            db.commit()

            self.open_trades.pop(trade.symbol, None)
            self.risk_manager.update_open_positions(len(self.open_trades))

            await self._log_event("info", "trade_closed", f"Closed {trade.symbol}: {reason} | P&L ₹{pnl:.2f}")
            await self.email_service.trade_closed(trade.symbol, trade.signal.value, exit_price, pnl, reason)
        finally:
            db.close()
        await self._broadcast_trade_update()

    async def close_all_positions(self) -> list:
        closed = []
        for symbol, pos in list(self.open_trades.items()):
            await self.exit_trade(pos["trade_id"], reason="EOD_CLOSE")
            closed.append(symbol)
        return closed

    async def _monitor_open_trades(self):
        for symbol, pos in list(self.open_trades.items()):
            try:
                price = self.broker.get_price(symbol)
                if not price: continue
                
                sl = pos["stop_loss"]
                tgt = pos["target"]
                
                if "BUY" in pos["signal"]:
                    if price <= sl: await self.exit_trade(pos["trade_id"], "SL_HIT", price)
                    elif price >= tgt: await self.exit_trade(pos["trade_id"], "TARGET_HIT", price)
                else:
                    if price >= sl: await self.exit_trade(pos["trade_id"], "SL_HIT", price)
                    elif price <= tgt: await self.exit_trade(pos["trade_id"], "TARGET_HIT", price)
            except Exception as e:
                logger.warning(f"Monitor error for {symbol}: {e}")

    async def run_monitoring_loop(self):
        while self.is_running:
            try:
                if not self.is_paused and self._is_market_open():
                    await self._monitor_open_trades()
                await asyncio.sleep(5)
            except asyncio.CancelledError: break
            except Exception: await asyncio.sleep(10)

    def pause(self): self.is_paused = True
    def resume(self): self.is_paused = False
    def stop(self): self.is_running = False

    def _get_symbols(self) -> list[str]:
        if self.config.symbol_selection_mode == "manual" and self.config.manual_symbols:
            return self.config.manual_symbols
        # Auto-mode: Use a curated Nifty list for Claude to analyze
        return DEFAULT_SYMBOLS

    def _is_market_open(self) -> bool:
        now = datetime.now(IST)
        if now.weekday() >= 5: return False
        return time(9, 15) <= now.time() <= time(15, 30)

    def _is_near_market_close(self) -> bool:
        return datetime.now(IST).time() >= time(15, 25)

    @staticmethod
    def _calc_pnl(signal, entry, exit_price, qty):
        val = signal.value if hasattr(signal, 'value') else signal
        return round((exit_price - entry) * qty, 2) if "BUY" in val else round((entry - exit_price) * qty, 2)

    async def _log_event(self, severity, event_type, message):
        db = SessionLocal()
        try:
            db.add(SystemLog(user_id=self.user_id, event_type=event_type, message=message, severity=severity))
            db.commit()
        finally: db.close()
        try:
            await _get_ws_manager().send_to_user(self.user_id, {
                "type": "log_event", "data": {"event_type": event_type, "message": message, "severity": severity},
                "timestamp": datetime.now(IST).isoformat()
            })
        except: pass

    async def _broadcast_trade_update(self):
        try: await _get_ws_manager().send_to_user(self.user_id, {"type": "trade_update", "timestamp": datetime.now(IST).isoformat()})
        except: pass

    async def _broadcast_metrics(self):
        try:
            pnl = self._get_todays_pnl()
            self.risk_manager.update_daily_pnl(pnl)
            await _get_ws_manager().send_to_user(self.user_id, {
                "type": "metrics_update", "data": {"open_positions": len(self.open_trades), "daily_pnl": pnl, "last_update": self.last_update}
            })
        except: pass

    def _get_todays_pnl(self) -> float:
        db = SessionLocal()
        try:
            from sqlalchemy import func
            from datetime import date
            today = date.today()
            start = datetime.combine(today, datetime.min.time())
            res = db.query(func.sum(Trade.pnl)).filter(Trade.user_id == self.user_id, Trade.status == TradeStatus.CLOSED, Trade.exit_time >= start).scalar()
            return float(res or 0)
        finally: db.close()
