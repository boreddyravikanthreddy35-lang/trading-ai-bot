"""AI Trading Signal service using Claude Sonnet 4.5 and Gemini 2.5 Pro via Emergent LLM key."""
import json
import os
import re
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage
from pydantic import BaseModel, Field, ValidationError

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

MODEL_MAP = {
    "claude": ("anthropic", "claude-sonnet-4-5-20250929", "Claude Sonnet 4.5"),
    "gemini": ("gemini", "gemini-2.5-pro", "Gemini 2.5 Pro"),
}


class TradingSignal(BaseModel):
    action: str = Field(..., description="BUY | SELL | HOLD")
    confidence: float = Field(..., ge=0.0, le=1.0)
    time_horizon: str
    reasoning: str
    key_factors: List[str]
    indicator_summary: str
    risk_level: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


SYSTEM_PROMPT = """You are an expert crypto quantitative analyst.
Given real market data and technical indicators for a cryptocurrency,
produce a concise trading signal.

You MUST respond with a SINGLE valid JSON object matching this exact schema
(no markdown, no code fences, no commentary outside JSON):

{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0-1.0,
  "time_horizon": "short" | "medium" | "long",
  "reasoning": "2-4 sentences explaining the recommendation",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "indicator_summary": "1-2 sentences summarizing technicals (RSI, MACD, SMA position)",
  "risk_level": "low" | "medium" | "high",
  "entry_price": <number or null>,
  "stop_loss": <number or null>,
  "take_profit": <number or null>
}

Rules:
- Confidence is 0.0-1.0 (e.g., 0.72).
- If RSI > 70 lean SELL/HOLD, RSI < 30 lean BUY/HOLD.
- Use MACD trend and SMA/EMA position to confirm.
- Never respond with anything except the JSON object.
- Numbers are plain numbers (no strings, no % signs, no $).
"""


def _extract_json(text: str) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return None


def _build_prompt(symbol: str, meta: Dict[str, Any], indicators: Dict[str, Any], timeframe: str) -> str:
    return f"""Analyze {symbol} on the {timeframe} timeframe and issue a trading signal.

Coin metadata:
- name: {meta.get('name')}
- symbol: {meta.get('symbol')}
- market_cap_rank: {meta.get('market_cap_rank')}
- current_price_usd: {meta.get('current_price')}
- 24h_change_pct: {meta.get('price_change_percentage_24h')}
- 24h_volume_usd: {meta.get('total_volume')}

Technical indicators (last close):
{json.dumps(indicators, indent=2)}

Return ONLY the JSON signal object per the schema."""


async def generate_signal(
    model_key: str,
    symbol: str,
    coin_meta: Dict[str, Any],
    indicators: Dict[str, Any],
    timeframe: str,
    session_id: str,
) -> Dict[str, Any]:
    """Call the chosen LLM and return validated TradingSignal dict."""
    if model_key not in MODEL_MAP:
        raise ValueError(f"Unknown model_key: {model_key}")
    if not EMERGENT_LLM_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    provider, model_name, display_name = MODEL_MAP[model_key]
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=SYSTEM_PROMPT,
    ).with_model(provider, model_name)

    prompt = _build_prompt(symbol, coin_meta, indicators, timeframe)
    raw = ""
    last_err: Optional[str] = None
    for attempt in range(2):
        try:
            raw = await chat.send_message(UserMessage(text=prompt))
            block = _extract_json(raw) or raw
            data = json.loads(block)
            signal = TradingSignal(**data)
            return {
                "model_key": model_key,
                "model_display": display_name,
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal.model_dump(),
            }
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = f"{type(e).__name__}: {e}"
            prompt = (
                "Your previous reply was not valid JSON matching the schema.\n"
                f"Error: {last_err}\nReturn ONLY the JSON object, no markdown.\n\n" + prompt
            )
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            break

    return {
        "model_key": model_key,
        "model_display": display_name,
        "symbol": symbol,
        "timeframe": timeframe,
        "error": last_err,
        "raw": raw[:600] if raw else "",
    }
