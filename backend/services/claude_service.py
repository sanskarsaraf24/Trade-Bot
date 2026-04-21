"""
Claude / Anthropic service — builds prompts and parses structured trade signals.
"""
import json
import logging
import re
from typing import Optional

import anthropic

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ClaudeService:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not set. Add it to .env")
        self.client = anthropic.Anthropic(api_key=key)
        # Use the latest efficient model
        self.model = "claude-haiku-4-5"

    def get_signals(self, features: dict, config, open_positions: int = 0) -> list[dict]:
        """
        Analyze market features and return structured trade signals.
        Returns list of signal dicts.
        """
        prompt = self._build_prompt(features, config, open_positions=open_positions)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text
            signals = self._parse_response(response_text, features)
            logger.info(f"Claude returned {len(signals)} signals")
            return signals

        except anthropic.APIStatusError as e:
            logger.error(f"Anthropic API error {e.status_code}: {e.message}")
            # Try fallback model
            try:
                message = self.client.messages.create(
                    model="claude-3-5-haiku-latest",
                    max_tokens=2048,
                    messages=[{"role": "user", "content": prompt}],
                )
                return self._parse_response(message.content[0].text, features)
            except Exception as e2:
                logger.error(f"Fallback model also failed: {e2}")
                return []
        except Exception as e:
            logger.error(f"Claude service error: {e}")
            return []

    def _build_prompt(self, features: dict, config, open_positions: int = 0) -> str:
        symbols_block = ""
        for symbol, feat in features.items():
            symbols_block += f"\n### {symbol}\n"
            symbols_block += f"Current Price: ₹{feat['current_price']:.2f}\n"
            symbols_block += f"Analysis: {feat['narrative']}\n"
            ind = feat.get("indicators", {})
            rsi = ind.get("rsi")
            macd = ind.get("macd", {})
            bb = ind.get("bollinger", {})
            sma20 = ind.get("sma_20")
            sma50 = ind.get("sma_50")
            atr = ind.get("atr")
            symbols_block += f"RSI(14): {rsi}\n"
            symbols_block += f"MACD Hist: {macd.get('histogram')}\n"
            symbols_block += f"BB Position: {bb.get('price_position')}%\n"
            symbols_block += f"SMA20/50: {sma20}/{sma50}\n"
            symbols_block += f"ATR(14): {atr}\n"
            symbols_block += f"Volume: {ind.get('volume_trend')}\n"

        risk_amt = config.account_balance * config.risk_per_trade_percent / 100
        strategies = ", ".join(config.enabled_strategies) if config.enabled_strategies else "all strategies"
        avoid = ", ".join(config.avoid_trading_during) if config.avoid_trading_during else "none"
        instructions = config.system_instructions or "Standard risk management."

        return f"""You are an expert NSE intraday trader. Analyze these symbols and provide precise trade signals.

SYSTEM INSTRUCTIONS: {instructions}

ACCOUNT:
- Balance: ₹{config.account_balance:,.0f}
- Risk Per Trade: ₹{risk_amt:,.0f} ({config.risk_per_trade_percent}%)
- Min Confidence: {config.min_confidence_threshold}%
- Timeframe: {config.timeframe}
- Open Positions: {open_positions}/{config.max_concurrent_positions}
- Strategy Focus: {strategies}
- Avoid: {avoid}

SYMBOLS:
{symbols_block}

RULES:
1. Only recommend a trade if confidence >= {config.min_confidence_threshold}%
2. Stop-loss MUST be meaningful (not too tight or wide) — use ATR as guide
3. Risk:Reward must be minimum 1:1.5
4. DO NOT FORCE TRADES. If there is no high-probability, clear setup, you MUST return "HOLD". Refusing to trade in choppy or unclear markets is exactly what you are supposed to do.
5. Return ONLY valid JSON, no markdown, no commentary

JSON FORMAT (include ALL analyzed symbols):
{{
  "SYMBOL": {{
    "signal": "BUY_STOCK | SELL_STOCK | BUY_CALL | BUY_PUT | HOLD",
    "confidence": 0-100,
    "reasoning": "Concise technical reason (max 80 words)",
    "entry_level": <number>,
    "stop_loss": <number>,
    "target": <number>,
    "risk_reward": "1:X"
  }}
}}"""

    def _parse_response(self, response_text: str, features: dict) -> list[dict]:
        """Parse Claude's JSON response into structured signal dicts."""
        try:
            # Strip markdown code fences if present
            cleaned = response_text.strip()
            # Remove ```json ... ``` or ``` ... ```
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            signals = []
            for symbol, signal_data in data.items():
                if symbol not in features:
                    logger.debug(f"Claude returned signal for unknown symbol {symbol} — skipping")
                    continue

                raw_signal = signal_data.get("signal", "HOLD")
                confidence = float(signal_data.get("confidence", 0))
                entry = float(signal_data.get("entry_level") or features[symbol]["current_price"])
                sl = float(signal_data.get("stop_loss") or 0)
                tgt = float(signal_data.get("target") or 0)

                signals.append({
                    "symbol": symbol,
                    "signal": raw_signal,
                    "confidence": confidence,
                    "reasoning": signal_data.get("reasoning", ""),
                    "entry_level": entry,
                    "stop_loss": sl,
                    "target": tgt,
                    "risk_reward": signal_data.get("risk_reward", "1:2"),
                })

            actionable = [s for s in signals if s["signal"] != "HOLD"]
            logger.info(f"Parsed {len(signals)} signals ({len(actionable)} actionable)")
            return signals

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse Claude response: {e}\nRaw (first 500): {response_text[:500]}")
            return []
