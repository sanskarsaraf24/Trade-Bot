"""
Risk Manager — enforces all trading safety rules before any order is placed.
"""
import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


class RiskManager:
    def __init__(self, config, db_session=None):
        self.config = config
        self._db = db_session
        self._daily_pnl: float = 0.0           # updated in real-time
        self._open_position_count: int = 0     # updated by trading engine

    # ─── Gate checks ─────────────────────────────────────────
    def can_execute(self, signal: dict) -> tuple[bool, str]:
        """
        Returns (True, "") if trade is allowed, else (False, reason).
        """
        # 1. Confidence threshold
        confidence = signal.get("confidence", 0)
        if confidence < self.config.min_confidence_threshold:
            return False, f"Confidence {confidence}% < threshold {self.config.min_confidence_threshold}%"

        # 2. Max open positions
        if self._open_position_count >= self.config.max_concurrent_positions:
            return False, f"Max positions reached ({self.config.max_concurrent_positions})"

        # 3. Daily loss limit
        if self._daily_pnl <= -abs(self.config.daily_loss_limit):
            return False, f"Daily loss limit hit (₹{self.config.daily_loss_limit})"

        # 4. Daily profit target (stop trading if we've already hit it)
        if self._daily_pnl >= self.config.daily_profit_target:
            return False, f"Daily target already reached (₹{self.config.daily_profit_target})"

        # 5. Signal type must be actionable
        if signal.get("signal") in ("HOLD", "EXIT", None):
            return False, "Signal is HOLD/EXIT — no new trade"

        return True, ""

    # ─── Position sizing ─────────────────────────────────────
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """
        1% risk rule: risk only (risk_per_trade_percent)% of capital per trade.
        Qty = (capital × risk%) / |entry - SL|
        """
        capital = self.config.account_balance
        margin = getattr(self.config, "margin_multiplier", 1.0) or 1.0
        risk_amount = (capital * margin) * (self.config.risk_per_trade_percent / 100)
        price_risk = abs(entry_price - stop_loss)

        if price_risk <= 0:
            logger.warning("SL == entry price; defaulting to qty=1")
            return 1

        qty = int(risk_amount / price_risk)
        return max(1, qty)

    # ─── State updates (called by trading engine) ─────────────
    def update_daily_pnl(self, pnl: float):
        self._daily_pnl = pnl

    def update_open_positions(self, count: int):
        self._open_position_count = count

    # ─── Suggested SL/Target ─────────────────────────────────
    def suggest_stop_loss(self, signal_type: str, entry: float, atr: Optional[float] = None) -> float:
        """Fallback SL distance from global percentage setting."""
        pct = getattr(self.config, "default_stop_loss_percent", 0.5) / 100.0
        distance = entry * pct
        return round(entry - distance if "BUY" in signal_type else entry + distance, 2)

    def suggest_target(self, signal_type: str, entry: float, stop_loss: Optional[float] = None,
                       risk_reward: float = 2.0) -> float:
        """Fallback Target distance from global percentage setting."""
        pct = getattr(self.config, "default_target_percent", 1.0) / 100.0
        distance = entry * pct
        return round(entry + distance if "BUY" in signal_type else entry - distance, 2)
