"""Utility calculations (standalone, no DB deps)."""


def calculate_pnl(signal: str, entry: float, current: float, qty: int) -> float:
    if "BUY" in signal:
        return round((current - entry) * qty, 2)
    return round((entry - current) * qty, 2)


def pnl_percent(pnl: float, entry: float, qty: int) -> float:
    cost = entry * qty
    return round(pnl / cost * 100, 2) if cost else 0.0


def position_size_1pct(capital: float, risk_pct: float, entry: float, stop_loss: float) -> int:
    """Risk (risk_pct)% of capital per trade."""
    risk_amount = capital * (risk_pct / 100)
    price_risk = abs(entry - stop_loss)
    if price_risk <= 0:
        return 1
    return max(1, int(risk_amount / price_risk))
