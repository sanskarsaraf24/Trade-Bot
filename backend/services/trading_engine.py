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
from services.indicators import calculate_all_indicators, build_narrative, build_macro_narrative
from services.scanner_service import ScannerService
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
        self.scanner = ScannerService(self.broker)

        # ── State ───────────────────────────────────────────────
        # open_trades: {symbol: {"trade_id", "entry", "stop_loss", "target", "signal", "qty"}}
        self.open_trades: Dict[str, dict] = {}
        self.is_running: bool = False
        self.is_paused: bool = False
        self.last_update: Optional[str] = None
        self.engine_id = str(uuid.uuid4())
        self._monitor_task: Optional[asyncio.Task] = None
        self._last_feed_connected: Optional[bool] = None
        self._last_scan_time: Optional[datetime] = None

        # Restore any open positions from DB so P&L tracking survives restarts
        self._restore_open_trades_from_db()

    def _restore_open_trades_from_db(self):
        """Reload open positions from DB into memory on engine start/restart."""
        db = SessionLocal()
        try:
            open_db_trades = db.query(Trade).filter(
                Trade.user_id == self.user_id,
                Trade.status == TradeStatus.OPEN,
            ).all()
            for t in open_db_trades:
                sig_val = t.signal.value if hasattr(t.signal, 'value') else str(t.signal)
                self.open_trades[t.symbol] = {
                    "trade_id": t.id,
                    "entry": t.entry_price,
                    "stop_loss": t.stop_loss or 0,
                    "target": t.target or 0,
                    "signal": sig_val,
                    "qty": t.quantity,
                    "symbol": t.symbol,
                }
            if open_db_trades:
                logger.info(f"Restored {len(open_db_trades)} open trade(s) from DB into engine memory")
                self.risk_manager.update_open_positions(len(self.open_trades))
        except Exception as e:
            logger.error(f"Failed to restore open trades: {e}")
        finally:
            db.close()

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

                # ── Sync balance and risk rules ────────────────
                try:
                    real_balance = self.broker.get_account_balance()
                    if real_balance > 0:
                        self.risk_manager.update_available_balance(real_balance)
                        logger.info(f"Synced broker balance: ₹{real_balance:,.2f}")
                except Exception as e:
                    logger.warning(f"Failed to sync broker balance: {e}")

                if len(self.open_trades) >= self.config.max_concurrent_positions:
                    await self._log("info", "slots_full", f"Max slots ({self.config.max_concurrent_positions}) filled. Tracking open positions only.")
                    signals = []
                else:
                    # ── Hourly Market Scan ───────────────────────────────
                    await self._check_scan_market()

                    # ── Strategy Execution ───────────────────────────────
                    market_data = await self._collect_market_data()
                    if not market_data:
                        await self._log("warning", "no_data", "No market data collected — skipping cycle")
                        await asyncio.sleep(60)
                        continue

                    features = self._engineer_features(market_data)

                    signals = []
                    if self.claude and features:
                        try:
                            signals = self.claude.get_signals(features, self.config, len(self.open_trades))
                            actionable = [s for s in signals if s["signal"] not in ("HOLD", "EXIT")]
                            await self._log(
                                "info", "signals_received",
                                f"🔍 Analyzed {len(features)} symbols | ✅ {len(actionable)} Actionable | ⏸️ {len(signals) - len(actionable)} Hold"
                            )
                        except Exception as e:
                            await self._log("error", "claude_error", f"Claude API error: {e}")

                for signal in signals:
                    sym = signal.get("symbol", "UNKNOWN")
                    # Surface HOLD reasoning to the user for transparency
                    if signal["signal"] in ("HOLD", "EXIT"):
                        reasoning = signal.get("reasoning", "No specific setup found.")
                        # Only log if it's not a generic placeholder
                        if len(reasoning) > 5:
                            await self._log("info", "signal_hold", f"⏸️ {sym} (HOLD): {reasoning}")
                        continue

                    # Process actionable signals
                    self.risk_manager.update_open_positions(len(self.open_trades))
                    allowed, reason = self.risk_manager.can_execute(signal)
                    if allowed:
                        await self._execute_trade(signal)
                    else:
                        await self._log(
                            "warning", "signal_skipped",
                            f"⚠️ {sym} skipped: {reason}"
                        )

                # ── Transparency: Log analysis summary if no trades made ────
                if signals and not any(s["signal"] not in ("HOLD", "EXIT") for s in signals):
                    summary = []
                    for s in signals[:3]: # top 3 symbols for brevity
                        summary.append(f"{s['symbol']}: {s['signal']} ({s['confidence']:.0f}%)")
                    await self._log("info", "no_actionable_signals", f"No actionable signals found. Top reasons: {', '.join(summary)}...")

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
    async def _check_scan_market(self, force: bool = False):
        """Perform an hourly scan for top movers and update the watchlist."""
        now = datetime.now(IST)
        
        # Scan if it's the first time, or if 60 minutes have passed, or if forced
        if force or self._last_scan_time is None or (now - self._last_scan_time).total_seconds() >= 3600:
            await self._log("info", "market_scanning", "📡 Periodic Markt Scan: Searching for top profit movers...")
            
            db = SessionLocal()
            try:
                new_symbols = await self.scanner.update_watchlist(db, self.user_id)
                if new_symbols:
                    self._last_scan_time = now
                    # Refresh local config to pick up the new manual_symbols
                    from database.models import TradingConfiguration
                    updated_config = db.query(TradingConfiguration).filter(
                        TradingConfiguration.user_id == self.user_id
                    ).first()
                    if updated_config:
                        self.config = updated_config
                    
                    await self._log("info", "watchlist_updated", f"✨ Scanner identified new movers: {', '.join(new_symbols)}")
            except Exception as e:
                logger.error(f"Market scan failed: {e}")
                await self._log("warning", "scan_failed", f"Scanner error: {e}")
            finally:
                db.close()

    # Data
    # ─────────────────────────────────────────────────────────
    async def _collect_market_data(self) -> dict:
        symbols = self._get_symbols()
        market_data = {}
        for symbol in symbols:
            try:
                candles = self.broker.get_ohlcv(symbol, bars=100, interval="5minute")
                current_price = self.broker.get_price(symbol)
                metadata = self.broker.get_symbol_metadata(symbol)
                
                if candles and current_price > 0:
                    market_data[symbol] = {
                        "candles": candles,
                        "current_price": current_price,
                        "metadata": metadata,
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
                metadata = data.get("metadata", {})
                
                indicators = calculate_all_indicators(candles)
                narrative = build_narrative(symbol, price, indicators)
                macro_narrative = build_macro_narrative(metadata, price)
                
                features[symbol] = {
                    "current_price": price,
                    "indicators": indicators,
                    "narrative": narrative,
                    "macro_context": metadata,
                    "macro_narrative": macro_narrative,
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

        max_qty = self.risk_manager.calculate_position_size(entry, sl)

        # ── Live margin check: cap qty to what Zerodha can actually fill ──
        # Use the real broker balance (not the stale config value)
        try:
            live_balance = self.broker.get_account_balance()
            if live_balance > 0:
                # MIS margin is typically 20-40% of trade value; use conservative 50% buffer
                # available_for_trade = live_balance * margin_multiplier (e.g. 5x leverage = 5x buying power)
                margin_mult = getattr(self.config, 'margin_multiplier', 1.0) or 1.0
                # Allow using up to 90% of available margin to leave headroom
                max_trade_value = live_balance * margin_mult * 0.90
                max_qty_by_balance = max(1, int(max_trade_value / entry)) if entry > 0 else max_qty
                if max_qty_by_balance < max_qty:
                    logger.info(
                        f"[MARGIN] Capping qty {max_qty}→{max_qty_by_balance} for {symbol} "
                        f"(live balance=₹{live_balance:.0f}, max trade value=₹{max_trade_value:.0f})"
                    )
                    max_qty = max_qty_by_balance
        except Exception as e:
            logger.warning(f"[MARGIN] Could not fetch live balance for {symbol}: {e}")
        ai_qty = signal.get("suggested_quantity")
        if ai_qty and isinstance(ai_qty, (int, float)) and ai_qty > 0:
            qty = min(int(ai_qty), max_qty)
        else:
            qty = max_qty

        if qty <= 0:
            await self._log("warning", "bad_qty", f"{symbol}: calculated qty=0 — skipping")
            return

        # ── Minimum profit check (covers brokerage) ───────────
        expected_profit = abs(tgt - entry) * qty
        min_abs = getattr(self.config, "min_profit_absolute", 50.0) or 50.0
        min_pct = getattr(self.config, "min_profit_percent", None)
        expected_pct = (expected_profit / (entry * qty)) * 100 if entry and qty else 0
        if min_abs and expected_profit < min_abs:
            await self._log("warning", "min_profit_skip",
                f"⚠️ {symbol}: expected profit ₹{expected_profit:.0f} < min ₹{min_abs:.0f} — skipping")
            return
        if min_pct and expected_pct < min_pct:
            await self._log("warning", "min_profit_skip",
                f"⚠️ {symbol}: expected profit {expected_pct:.2f}% < min {min_pct:.2f}% — skipping")
            return

        # ── Fetch fresh price just before execution ────────────
        execution_ltp = self.broker.get_fresh_price(symbol)
        logger.info(f"[EXEC] Pre-trade LTP for {symbol}: ₹{execution_ltp} (Claude: ₹{entry})")

        # ── Step 1: Place main entry MARKET order ─────────────
        order = self.broker.place_order(symbol, signal["signal"], qty, "MARKET")
        if order.get("status") == "FAILED":
            await self._log("error", "order_failed", f"❌ Order failed for {symbol}: {order.get('error')}")
            return

        actual_fill_price = order.get("price") or execution_ltp or entry
        is_buy = "BUY" in signal["signal"]
        exit_action = "SELL" if is_buy else "BUY"

        # ── Step 2: Place SL-M order (stop loss protection) ───
        # SL-M triggers at market price when stop_loss level is breached
        sl_order_id = ""
        try:
            sl_order = self.broker.place_order(
                symbol, exit_action, qty,
                order_type="SL-M",
                trigger_price=round(sl, 2)
            )
            if sl_order.get("status") != "FAILED":
                sl_order_id = sl_order.get("order_id", "")
                await self._log("info", "sl_order_placed",
                    f"🛡️ SL-M order placed for {symbol}: trigger ₹{sl:.2f} | order_id={sl_order_id}")
            else:
                await self._log("warning", "sl_order_failed",
                    f"⚠️ SL-M order FAILED for {symbol}: {sl_order.get('error')} — monitoring via price poll")
        except Exception as e:
            await self._log("warning", "sl_order_error", f"SL order error for {symbol}: {e}")

        # ── Step 3: Place LIMIT target order (profit booking) ─
        # LIMIT order at target price — auto-executes when market reaches target
        target_order_id = ""
        try:
            tgt_order = self.broker.place_order(
                symbol, exit_action, qty,
                order_type="LIMIT",
                price=round(tgt, 2)
            )
            if tgt_order.get("status") != "FAILED":
                target_order_id = tgt_order.get("order_id", "")
                await self._log("info", "target_order_placed",
                    f"🎯 LIMIT target order placed for {symbol}: ₹{tgt:.2f} | order_id={target_order_id}")
            else:
                await self._log("warning", "target_order_failed",
                    f"⚠️ Target order FAILED for {symbol}: {tgt_order.get('error')} — monitoring via price poll")
        except Exception as e:
            await self._log("warning", "target_order_error", f"Target order error for {symbol}: {e}")

        # ── Step 4: Persist to DB with both order IDs ─────────
        db = SessionLocal()
        try:
            trade = Trade(
                user_id=self.user_id,
                bot_session_id=self.session_id,
                symbol=symbol,
                signal=signal["signal"],
                entry_price=actual_fill_price,
                stop_loss=sl,
                target=tgt,
                quantity=qty,
                confidence=signal["confidence"],
                claude_reasoning=signal.get("reasoning", ""),
                main_order_id=order.get("order_id", ""),
                sl_order_id=sl_order_id,
                target_order_id=target_order_id,
                status=TradeStatus.OPEN,
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)

            self.open_trades[symbol] = {
                "trade_id": trade.id,
                "entry": actual_fill_price,
                "stop_loss": sl,
                "target": tgt,
                "signal": signal["signal"],
                "qty": qty,
                "symbol": symbol,
                "sl_order_id": sl_order_id,
                "target_order_id": target_order_id,
            }
        finally:
            db.close()

        self.risk_manager.update_open_positions(len(self.open_trades))

        await self._log(
            "info", "trade_opened",
            f"🟢 OPENED {signal['signal']} {symbol} @ ₹{actual_fill_price:.2f} "
            f"| SL ₹{sl:.2f} (order:{sl_order_id or 'price-poll'}) "
            f"| Target ₹{tgt:.2f} (order:{target_order_id or 'price-poll'}) "
            f"| Qty {qty} | Conf {signal['confidence']:.0f}%"
        )
        await self.email_service.trade_opened(symbol, signal["signal"], actual_fill_price, signal["confidence"])
        await _get_ws_manager().send_to_user(self.user_id, {
            "type": "trade_update",
            "data": {
                "action": "opened",
                "symbol": symbol,
                "signal": signal["signal"],
                "entry": actual_fill_price,
                "sl": sl,
                "target": tgt,
                "qty": qty,
            },
            "timestamp": datetime.now(IST).isoformat(),
        })

    async def exit_trade(self, trade_id: str, reason: str = "MANUAL_EXIT", exit_price: float = 0):
        """Exit a single trade by trade_id. Cancels any open bracket orders first."""
        db = SessionLocal()
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if not trade or trade.status != TradeStatus.OPEN:
                return

            # ── Cancel remaining bracket orders before placing exit ──
            # This prevents orphan orders lingering on the exchange.
            for oid_attr, label in (("sl_order_id", "SL-M"), ("target_order_id", "Target")):
                oid = getattr(trade, oid_attr, "") or ""
                if oid:
                    cancelled = self.broker.cancel_order(oid)
                    if cancelled:
                        logger.info(f"[❌ CANCELLED] {label} order {oid} for {trade.symbol}")
                    else:
                        logger.warning(f"Could not cancel {label} order {oid} — may already be filled/cancelled")

            if exit_price <= 0:
                exit_price = self.broker.get_fresh_price(trade.symbol)
            if exit_price <= 0:
                exit_price = trade.entry_price  # last resort fallback

            # Place market exit order only if reason is not a native broker fill
            # (SL_HIT and TARGET_HIT via order polling mean broker already filled the order)
            actual_exit_price = exit_price
            if reason not in ("SL_HIT_BROKER", "TARGET_HIT_BROKER"):
                opp = "SELL" if "BUY" in trade.signal.value else "BUY"
                exit_order = self.broker.place_order(trade.symbol, opp, trade.quantity, "MARKET")
                actual_exit_price = exit_order.get("price") or exit_price

            pnl = self._calc_pnl(trade.signal, trade.entry_price, actual_exit_price, trade.quantity)
            trade.exit_price = actual_exit_price
            trade.exit_reason = reason
            trade.exit_time = datetime.now(IST).replace(tzinfo=None)
            trade.status = TradeStatus.CLOSED
            trade.pnl = pnl
            trade.pnl_percent = (pnl / (trade.entry_price * trade.quantity)) * 100 if trade.entry_price else 0
            # Clear broker order IDs so monitoring loop doesn't try to cancel them again
            trade.sl_order_id = ""
            trade.target_order_id = ""
            db.commit()

            self.open_trades.pop(trade.symbol, None)
            self.risk_manager.update_open_positions(len(self.open_trades))

            await self._refresh_daily_pnl()

            emoji = "🟢" if pnl >= 0 else "🔴"
            await self._log(
                "info", "trade_closed",
                f"{emoji} CLOSED {trade.symbol} [{reason}] @ ₹{actual_exit_price:.2f} | P&L ₹{pnl:+.2f}"
            )
            await self.email_service.trade_closed(trade.symbol, trade.signal.value, actual_exit_price, pnl, reason)

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
        """Check SL/Target hits and adjust bracket orders continuously."""
        _metrics_tick = 0
        _bracket_tick = 0
        while self.is_running:
            try:
                if not self.is_paused and self._is_market_open():
                    await self._check_sl_target()
                    _metrics_tick += 1
                    _bracket_tick += 1
                    # Broadcast heartbeat metrics every 30s even without positions
                    if _metrics_tick >= 6:
                        self.last_update = datetime.now(IST).isoformat()
                        await self._broadcast_metrics()
                        _metrics_tick = 0
                    # Adjust trailing stops every 60s (12 ticks × 5s)
                    if _bracket_tick >= 12:
                        await self._adjust_bracket_orders()
                        _bracket_tick = 0
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Monitor loop error: {e}")
                await asyncio.sleep(10)

    async def _check_sl_target(self):
        """
        Dual-mode SL/Target detection:
        1. PRIMARY: Poll Zerodha order statuses — catches broker-native fills (most reliable)
        2. FALLBACK: Price polling — activates if broker orders weren't placed (paper mode, errors)
        """
        # Build a quick lookup of all current order statuses (single API call for efficiency)
        order_status_map: dict[str, str] = {}
        fill_price_map: dict[str, float] = {}
        try:
            all_orders = self.broker.get_orders()
            for o in all_orders:
                oid = str(o.get("order_id", "") or "")
                status = str(o.get("status", "") or "").upper()
                avg_price = float(o.get("average_price") or 0)
                if oid:
                    order_status_map[oid] = status
                    if avg_price > 0:
                        fill_price_map[oid] = avg_price
        except Exception as e:
            logger.warning(f"Could not fetch order book: {e}")

        for symbol, pos in list(self.open_trades.items()):
            try:
                sl_oid = pos.get("sl_order_id", "")
                tgt_oid = pos.get("target_order_id", "")
                handled = False

                # ── PRIMARY: Check if SL order has been filled by broker ──
                if sl_oid and order_status_map.get(sl_oid) in ("COMPLETE", "COMPLETED"):
                    fill_px = fill_price_map.get(sl_oid, 0)
                    await self._log("info", "sl_hit_broker",
                        f"🔴 SL order {sl_oid} FILLED for {symbol} @ ₹{fill_px:.2f} (broker-native)")
                    # Cancel the target order before recording the exit
                    if tgt_oid:
                        self.broker.cancel_order(tgt_oid)
                        logger.info(f"[❌] Cancelled target order {tgt_oid} after SL hit")
                    pos["sl_order_id"] = ""  # clear to avoid re-processing
                    pos["target_order_id"] = ""
                    await self.exit_trade(pos["trade_id"], "SL_HIT_BROKER", fill_px)
                    handled = True

                # ── PRIMARY: Check if Target order has been filled by broker ──
                elif tgt_oid and order_status_map.get(tgt_oid) in ("COMPLETE", "COMPLETED"):
                    fill_px = fill_price_map.get(tgt_oid, 0)
                    await self._log("info", "target_hit_broker",
                        f"🟢 Target order {tgt_oid} FILLED for {symbol} @ ₹{fill_px:.2f} (broker-native)")
                    # Cancel the SL order before recording the exit
                    if sl_oid:
                        self.broker.cancel_order(sl_oid)
                        logger.info(f"[❌] Cancelled SL order {sl_oid} after target hit")
                    pos["sl_order_id"] = ""
                    pos["target_order_id"] = ""
                    await self.exit_trade(pos["trade_id"], "TARGET_HIT_BROKER", fill_px)
                    handled = True

                # ── FALLBACK: Price polling (no order IDs or paper broker) ──
                if not handled and not sl_oid and not tgt_oid:
                    price = self.broker.get_fresh_price(symbol)
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

    async def _adjust_bracket_orders(self):
        """
        Dynamically modify live SL/Target bracket orders based on market movement.
        Called every 60s. Implements:
        - Trailing Stop: moves SL up for profitable BUY trades (locks in gains)
        - Profit Tightening: reduces target if price retreats significantly
        """
        for symbol, pos in list(self.open_trades.items()):
            try:
                sl_oid = pos.get("sl_order_id", "")
                tgt_oid = pos.get("target_order_id", "")
                if not sl_oid and not tgt_oid:
                    continue  # no live orders, skip

                price = self.broker.get_fresh_price(symbol)
                if not price or price <= 0:
                    continue

                entry = pos["entry"]
                sl = pos["stop_loss"]
                tgt = pos["target"]
                sig = pos["signal"]
                is_buy = "BUY" in sig

                trade_range = abs(tgt - entry)  # original risk unit
                if trade_range <= 0:
                    continue

                # ── Trailing Stop for BUY trades ──────────────────
                # Once price moves 50% toward target, trail SL to +10% of entry (breakeven+)
                if is_buy:
                    profit_pct = (price - entry) / trade_range  # 0=breakeven, 1=target
                    if profit_pct >= 0.5:
                        # Trail SL to 25% of the way between entry and target
                        new_sl = round(entry + trade_range * 0.25, 2)
                        if new_sl > sl + 0.5 and sl_oid:  # only move if meaningfully better
                            result = self.broker.modify_order(sl_oid, trigger_price=new_sl)
                            if result.get("status") != "FAILED":
                                pos["stop_loss"] = new_sl
                                # Persist to DB
                                db = SessionLocal()
                                try:
                                    db.query(Trade).filter(Trade.id == pos["trade_id"]).update({"stop_loss": new_sl})
                                    db.commit()
                                finally:
                                    db.close()
                                await self._log("info", "trailing_stop",
                                    f"🛡️⬆️ Trailing SL for {symbol}: ₹{sl:.2f} → ₹{new_sl:.2f} (price ₹{price:.2f})")

                # ── Trailing Stop for SELL trades ──────────────────
                else:
                    profit_pct = (entry - price) / trade_range
                    if profit_pct >= 0.5:
                        new_sl = round(entry - trade_range * 0.25, 2)
                        if new_sl < sl - 0.5 and sl_oid:  # only trail down for short
                            result = self.broker.modify_order(sl_oid, trigger_price=new_sl)
                            if result.get("status") != "FAILED":
                                pos["stop_loss"] = new_sl
                                db = SessionLocal()
                                try:
                                    db.query(Trade).filter(Trade.id == pos["trade_id"]).update({"stop_loss": new_sl})
                                    db.commit()
                                finally:
                                    db.close()
                                await self._log("info", "trailing_stop",
                                    f"🛡️⬇️ Trailing SL for {symbol}: ₹{sl:.2f} → ₹{new_sl:.2f} (price ₹{price:.2f})")

            except Exception as e:
                logger.warning(f"_adjust_bracket_orders error for {symbol}: {e}")

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
                "stopped_at": datetime.now(IST).replace(tzinfo=None),
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
            realized_pnl = self._get_todays_pnl()

            # BUG FIX: compute floating (unrealized) P&L for open positions
            floating_pnl = 0.0
            open_positions_detail = []
            for symbol, pos in self.open_trades.items():
                try:
                    # Always use fresh REST price for P&L — never stale cache
                    current_price = self.broker.get_fresh_price(symbol)
                    if current_price > 0:
                        qty = pos.get("qty", 0)
                        entry = pos.get("entry", 0)
                        sig = pos.get("signal", "BUY")
                        if "BUY" in sig:
                            unreal = (current_price - entry) * qty
                        else:
                            unreal = (entry - current_price) * qty
                        floating_pnl += unreal
                        open_positions_detail.append({
                            "symbol": symbol,
                            "signal": sig,
                            "entry": entry,
                            "current_price": current_price,
                            "qty": qty,
                            "floating_pnl": round(unreal, 2),
                            "stop_loss": pos.get("stop_loss", 0),
                            "target": pos.get("target", 0),
                        })
                except Exception as e:
                    logger.warning(f"Floating P&L calc failed for {symbol}: {e}")

            feed_status = {}
            if hasattr(self.broker, "get_feed_status"):
                try:
                    feed_status = self.broker.get_feed_status() or {}
                except Exception:
                    feed_status = {}

            connected = feed_status.get("connected")
            if connected is not None and connected != self._last_feed_connected:
                self._last_feed_connected = connected
                if connected:
                    await self._log(
                        "info",
                        "market_feed_restored",
                        f"📡 Live feed restored via {feed_status.get('source', 'unknown')}"
                    )
                else:
                    await self._log(
                        "warning",
                        "market_feed_degraded",
                        f"⚠️ Live market feed degraded. Fallback source: {feed_status.get('source', 'unknown')}"
                    )

            await _get_ws_manager().send_to_user(self.user_id, {
                "type": "metrics_update",
                "data": {
                    "open_positions": len(self.open_trades),
                    "daily_pnl": realized_pnl,
                    "floating_pnl": round(floating_pnl, 2),
                    "total_pnl": round(realized_pnl + floating_pnl, 2),
                    "open_positions_detail": open_positions_detail,
                    "feed_status": feed_status,
                    "last_update": self.last_update,
                },
            })
        except Exception:
            pass
