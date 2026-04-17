"""
Claude / Anthropic service — builds prompts and parses trade signals.
"""
import json
import logging
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
        self.model = "claude-3-5-haiku-latest"

    def get_signals(self, features: dict, config) -> list[dict]:
        """
        Build a prompt from market features and call Claude.
        Returns a list of structured trade signals.
        """
        prompt = self._build_prompt(features, config)

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = message.content[0].text
            return self._parse_response(response_text, features)

        except anthropic.APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Claude service unexpected error: {e}")
            return []

    def _build_prompt(self, features: dict, config) -> str:
        account_state = (
            f"Account Balance: ₹{config.account_balance:,.0f}\n"
            f"Open Positions: (injected by engine)\n"
            f"Max Positions: {config.max_concurrent_positions}\n"
            f"Risk Per Trade: ₹{config.account_balance * config.risk_per_trade_percent / 100:,.0f} "
            f"({config.risk_per_trade_percent}%)\n"
            f"Min Confidence Required: {config.min_confidence_threshold}%\n"
        )

        symbols_block = ""
        for symbol, feat in features.items():
            symbols_block += f"\n## {symbol}\n"
            symbols_block += f"Current Price: ₹{feat['current_price']:.2f}\n"
            symbols_block += f"Technical Summary: {feat['narrative']}\n"
            indicators = feat.get("indicators", {})
            symbols_block += f"RSI: {indicators.get('rsi', 'N/A')}\n"
            macd = indicators.get("macd", {})
            symbols_block += f"MACD Histogram: {macd.get('histogram', 'N/A')}\n"

        strategies = ", ".join(config.enabled_strategies) if config.enabled_strategies else "all"
        avoid = ", ".join(config.avoid_trading_during) if config.avoid_trading_during else "none"
        instructions = config.system_instructions or "No custom instructions."

        prompt = f"""You are an expert Indian stock market trader specializing in NSE intraday and options trading.

SYSTEM INSTRUCTIONS:
{instructions}

ACCOUNT STATE:
{account_state}

STRATEGY FOCUS: {strategies}
AVOID TRADING DURING: {avoid}
TIMEFRAME: {config.timeframe} (Analysis based on recent 5-minute candles)

SYMBOLS TO ANALYZE:
{symbols_block}

Analyze each symbol carefully using the technical context provided.
Return ONLY a single valid JSON object with no markdown, no backticks, no explanation.
JSON format:
{{
  "SYMBOL": {{
    "signal": "BUY_STOCK | SELL_STOCK | BUY_CALL | BUY_PUT | HOLD",
    "confidence": 0-100,
    "reasoning": "Brief analysis",
    "entry_level": price_number,
    "stop_loss": price_number,
    "target": price_number,
    "risk_reward": "1:X"
  }}
}}

Rules:
- Only include symbols where you have a high-conviction signal (confidence >= {config.min_confidence_threshold})
- For HOLD signals, still include them so we know you reviewed the symbol
- All prices must be realistic numbers reflecting current LTP
- entry_level MUST be specified. Provide conservative execution stops (stop_loss) and reasonable take-profit (target).
- reasoning must be concise (≤100 words), highlighting actionable setups based on real-time price action.
"""
        return prompt

    def _parse_response(self, response_text: str, features: dict) -> list[dict]:
        """Parse Claude's JSON response into a list of signal dicts."""
        try:
            # Strip any accidental markdown fences
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[1:])
            if cleaned.endswith("```"):
                cleaned = "\n".join(cleaned.split("\n")[:-1])

            data = json.loads(cleaned)
            signals = []
            for symbol, signal_data in data.items():
                if symbol not in features:
                    continue
                signals.append({
                    "symbol": symbol,
                    "signal": signal_data.get("signal", "HOLD"),
                    "confidence": float(signal_data.get("confidence", 0)),
                    "reasoning": signal_data.get("reasoning", ""),
                    "entry_level": float(signal_data.get("entry_level", features[symbol]["current_price"])),
                    "stop_loss": float(signal_data.get("stop_loss", 0)),
                    "target": float(signal_data.get("target", 0)),
                    "risk_reward": signal_data.get("risk_reward", "1:2"),
                })
            return signals

        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse Claude response: {e}\nRaw: {response_text[:500]}")
            return []
