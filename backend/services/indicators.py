"""
Technical Indicators using pandas-ta.
All functions accept a pandas DataFrame with OHLCV columns.
"""
import logging
from typing import Optional

import pandas as pd

# pandas_ta has some annoying DeprecationWarnings from numpy
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
import pandas_ta as ta  # noqa: E402

logger = logging.getLogger(__name__)


def to_df(candles: list[dict]) -> pd.DataFrame:
    """Convert list of OHLCV dicts to DataFrame."""
    df = pd.DataFrame(candles)
    df.columns = [c.lower() for c in df.columns]
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)
    df["volume"] = df["volume"].astype(float)
    return df


def calculate_rsi(candles: list[dict], period: int = 14) -> Optional[float]:
    try:
        df = to_df(candles)
        rsi = ta.rsi(df["close"], length=period)
        return round(float(rsi.iloc[-1]), 2) if rsi is not None else None
    except Exception as e:
        logger.warning(f"RSI calculation failed: {e}")
        return None


def calculate_macd(candles: list[dict]) -> dict:
    try:
        df = to_df(candles)
        macd = ta.macd(df["close"])
        if macd is None or macd.empty:
            return {"macd": None, "signal": None, "histogram": None}
        return {
            "macd": round(float(macd["MACD_12_26_9"].iloc[-1]), 4),
            "signal": round(float(macd["MACDs_12_26_9"].iloc[-1]), 4),
            "histogram": round(float(macd["MACDh_12_26_9"].iloc[-1]), 4),
        }
    except Exception as e:
        logger.warning(f"MACD calculation failed: {e}")
        return {"macd": None, "signal": None, "histogram": None}


def calculate_bollinger(candles: list[dict], period: int = 20) -> dict:
    try:
        df = to_df(candles)
        bb = ta.bbands(df["close"], length=period)
        if bb is None or bb.empty:
            return {"upper": None, "middle": None, "lower": None, "width": None}
        current_price = float(df["close"].iloc[-1])
        upper = float(bb[f"BBU_{period}_2.0"].iloc[-1])
        mid = float(bb[f"BBM_{period}_2.0"].iloc[-1])
        lower = float(bb[f"BBL_{period}_2.0"].iloc[-1])
        return {
            "upper": round(upper, 2),
            "middle": round(mid, 2),
            "lower": round(lower, 2),
            "width": round((upper - lower) / mid * 100, 2),
            "price_position": round((current_price - lower) / (upper - lower) * 100, 1),
        }
    except Exception as e:
        logger.warning(f"Bollinger Bands calculation failed: {e}")
        return {"upper": None, "middle": None, "lower": None, "width": None}


def calculate_sma(candles: list[dict], period: int) -> Optional[float]:
    try:
        df = to_df(candles)
        sma = ta.sma(df["close"], length=period)
        return round(float(sma.iloc[-1]), 2) if sma is not None else None
    except Exception as e:
        logger.warning(f"SMA({period}) calculation failed: {e}")
        return None


def calculate_atr(candles: list[dict], period: int = 14) -> Optional[float]:
    try:
        df = to_df(candles)
        atr = ta.atr(df["high"], df["low"], df["close"], length=period)
        return round(float(atr.iloc[-1]), 4) if atr is not None else None
    except Exception as e:
        logger.warning(f"ATR calculation failed: {e}")
        return None


def calculate_volume_trend(candles: list[dict], period: int = 10) -> str:
    """Returns 'rising', 'falling', or 'flat'."""
    try:
        df = to_df(candles)
        recent = df["volume"].tail(period)
        avg = recent.mean()
        current = float(df["volume"].iloc[-1])
        if current > avg * 1.3:
            return "rising"
        if current < avg * 0.7:
            return "falling"
        return "flat"
    except Exception:
        return "unknown"


def calculate_all_indicators(candles: list[dict]) -> dict:
    """Compute all indicators in one call."""
    return {
        "sma_20": calculate_sma(candles, 20),
        "sma_50": calculate_sma(candles, 50),
        "sma_200": calculate_sma(candles, 200),
        "rsi": calculate_rsi(candles, 14),
        "macd": calculate_macd(candles),
        "bollinger": calculate_bollinger(candles),
        "atr": calculate_atr(candles),
        "volume_trend": calculate_volume_trend(candles),
    }


def build_narrative(symbol: str, price: float, indicators: dict) -> str:
    """Build a human-readable summary of the symbol's technical state."""
    rsi = indicators.get("rsi")
    macd = indicators.get("macd", {})
    bb = indicators.get("bollinger", {})
    sma20 = indicators.get("sma_20")
    sma50 = indicators.get("sma_50")
    vol = indicators.get("volume_trend", "unknown")

    parts = [f"{symbol} @ ₹{price:.2f}"]

    if rsi is not None:
        rsi_label = "overbought" if rsi > 70 else ("oversold" if rsi < 30 else "neutral")
        parts.append(f"RSI={rsi:.1f} ({rsi_label})")

    if macd.get("histogram") is not None:
        direction = "bullish" if macd["histogram"] > 0 else "bearish"
        parts.append(f"MACD {direction} (hist={macd['histogram']:.4f})")

    if bb.get("price_position") is not None:
        pp = bb["price_position"]
        if pp > 80:
            parts.append("price near upper Bollinger Band")
        elif pp < 20:
            parts.append("price near lower Bollinger Band")

    if sma20 and sma50:
        trend = "above" if price > sma20 > sma50 else ("below" if price < sma20 < sma50 else "mixed")
        parts.append(f"price {trend} SMAs (20={sma20:.0f}, 50={sma50:.0f})")

    parts.append(f"volume {vol}")

    return ". ".join(parts) + "."
