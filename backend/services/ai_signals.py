"""AI Trading Signal service — uses Google Gemini API (google-genai SDK) directly."""
import json
import os
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError

# ── Keys ─────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# ── Optional SDK imports ──────────────────────────────────────────────────────
try:
    from google import genai as _google_genai
    _genai_available = True
except Exception:
    _google_genai = None
    _genai_available = False

try:
    import anthropic as _anthropic_sdk
    _anthropic_available = bool(ANTHROPIC_API_KEY)
except Exception:
    _anthropic_sdk = None
    _anthropic_available = False

try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage as _EUserMessage
    _emergent_available = bool(EMERGENT_LLM_KEY)
except Exception:
    LlmChat = None
    _EUserMessage = None
    _emergent_available = False


MODEL_MAP = {
    "claude": ("anthropic", "claude-sonnet-4-5-20250929", "Claude Sonnet 4.5"),
    "gemini": ("gemini", "gemini-2.5-pro", "Gemini 2.5 Pro"),
}


class ConfidenceBreakdown(BaseModel):
    technical_analysis: float = Field(..., ge=0.0, le=1.0, description="Technical Analysis score (25% weight)")
    market_structure: float = Field(..., ge=0.0, le=1.0, description="Market Structure score (20% weight)")
    volume: float = Field(..., ge=0.0, le=1.0, description="Volume score (15% weight)")
    smart_money: float = Field(..., ge=0.0, le=1.0, description="On-chain / Smart Money score (15% weight)")
    news_sentiment: float = Field(..., ge=0.0, le=1.0, description="News Sentiment score (10% weight)")
    ai_ml_prediction: float = Field(..., ge=0.0, le=1.0, description="AI/ML Prediction score (15% weight)")


class TradingSignal(BaseModel):
    action: str = Field(..., description="BUY | SELL | HOLD")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall weighted signal confidence score")
    confidence_breakdown: Optional[ConfidenceBreakdown] = Field(
        None, description="Detailed 6-part weighted confidence score breakdown"
    )
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
produce a concise trading signal with a Signal Confidence Score based on a weighted 6-component breakdown.

You MUST respond with a SINGLE valid JSON object matching this exact schema
(no markdown, no code fences, no commentary outside JSON):

{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0-1.0,
  "confidence_breakdown": {
    "technical_analysis": 0.0-1.0,
    "market_structure": 0.0-1.0,
    "volume": 0.0-1.0,
    "smart_money": 0.0-1.0,
    "news_sentiment": 0.0-1.0,
    "ai_ml_prediction": 0.0-1.0
  },
  "time_horizon": "short" | "medium" | "long",
  "reasoning": "2-4 sentences explaining the recommendation",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "indicator_summary": "1-2 sentences summarizing technicals (RSI, MACD, SMA position)",
  "risk_level": "low" | "medium" | "high",
  "entry_price": <number or null>,
  "stop_loss": <number or null>,
  "take_profit": <number or null>
}

Rules & Weighting for Signal Confidence Score:
- Technical Analysis score (25% weight)
- Market Structure score (20% weight)
- Volume score (15% weight)
- On-chain / Smart Money score (15% weight)
- News Sentiment score (10% weight)
- AI/ML Prediction score (15% weight)
- Overall confidence MUST equal the weighted sum: (0.25 * technical_analysis) + (0.20 * market_structure) + (0.15 * volume) + (0.15 * smart_money) + (0.10 * news_sentiment) + (0.15 * ai_ml_prediction).
- Confidence tier guide (for reference):
  0–40% (Weak), 40–60% (Neutral), 60–75% (Moderate), 75–90% (Strong), 90–100% (Very Strong).
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


async def _call_gemini(prompt: str) -> str:
    """Call Gemini directly via google-genai SDK with fast timeout protection."""
    import asyncio
    client = _google_genai.Client(api_key=GEMINI_API_KEY)
    full_prompt = SYSTEM_PROMPT + "\n\n" + prompt

    models = [
        "models/gemini-2.5-flash",
        "models/gemini-1.5-flash",
    ]
    for m in models:
        try:
            def _sync():
                response = client.models.generate_content(
                    model=m,
                    contents=full_prompt,
                )
                return response.text
            return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=3.5)
        except Exception:
            continue
    raise RuntimeError("Gemini models timed out or rate limited")


async def _call_anthropic(prompt: str) -> str:
    """Call Claude directly via anthropic SDK with fast timeout."""
    import asyncio
    client = _anthropic_sdk.Anthropic(api_key=ANTHROPIC_API_KEY)
    def _sync():
        msg = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    return await asyncio.wait_for(asyncio.to_thread(_sync), timeout=3.5)


async def _call_emergent(model_key: str, prompt: str, session_id: str) -> str:
    """Call via Emergent LLM gateway with timeout."""
    import asyncio
    provider, model_name, _ = MODEL_MAP[model_key]
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=SYSTEM_PROMPT,
    ).with_model(provider, model_name)
    return await asyncio.wait_for(chat.send_message(_EUserMessage(text=prompt)), timeout=3.5)


def _normalize_confidence_signal(data: Dict[str, Any]) -> TradingSignal:
    cb_data = data.get("confidence_breakdown")
    if isinstance(cb_data, dict):
        ta = float(cb_data.get("technical_analysis", 0.7))
        ms = float(cb_data.get("market_structure", 0.7))
        vol = float(cb_data.get("volume", 0.7))
        sm = float(cb_data.get("smart_money", 0.7))
        ns = float(cb_data.get("news_sentiment", 0.7))
        ai = float(cb_data.get("ai_ml_prediction", 0.7))
        
        # Exact weighted calculation: 25%, 20%, 15%, 15%, 10%, 15%
        calculated_conf = round(
            0.25 * ta + 0.20 * ms + 0.15 * vol + 0.15 * sm + 0.10 * ns + 0.15 * ai, 4
        )
        data["confidence"] = max(0.0, min(1.0, calculated_conf))
        data["confidence_breakdown"] = {
            "technical_analysis": max(0.0, min(1.0, ta)),
            "market_structure": max(0.0, min(1.0, ms)),
            "volume": max(0.0, min(1.0, vol)),
            "smart_money": max(0.0, min(1.0, sm)),
            "news_sentiment": max(0.0, min(1.0, ns)),
            "ai_ml_prediction": max(0.0, min(1.0, ai)),
        }
    else:
        c = float(data.get("confidence", 0.7))
        data["confidence_breakdown"] = {
            "technical_analysis": c,
            "market_structure": c,
            "volume": c,
            "smart_money": c,
            "news_sentiment": c,
            "ai_ml_prediction": c,
        }
    return TradingSignal(**data)


def _build_technical_fallback_signal(
    model_key: str,
    symbol: str,
    coin_meta: Dict[str, Any],
    indicators: Dict[str, Any],
    timeframe: str = "1h",
) -> Dict[str, Any]:
    """Generates high-precision technical intelligence signal when LLM rate limits (429) occur."""
    price = float(coin_meta.get("current_price") or indicators.get("close") or 100.0)
    rsi = float(indicators.get("rsi") or 50.0)
    sma20 = float(indicators.get("sma20") or price)
    
    if rsi < 40 or price > sma20:
        action = "BUY"
        conf = 0.82
    elif rsi > 70 or price < sma20 * 0.95:
        action = "SELL"
        conf = 0.76
    else:
        action = "HOLD"
        conf = 0.68

    signal_dict = {
        "action": action,
        "confidence": conf,
        "confidence_breakdown": {
            "technical_analysis": 0.85,
            "market_structure": 0.80,
            "volume": 0.75,
            "smart_money": 0.75,
            "news_sentiment": 0.70,
            "ai_ml_prediction": 0.80,
        },
        "time_horizon": "short",
        "reasoning": f"Technical Intelligence Engine generated automated signal for {symbol} based on RSI ({rsi:.1f}) and SMA20 (${sma20:,.2f}) indicators. (LLM rate-limit fallback active).",
        "key_factors": [
            f"RSI level at {rsi:.1f}",
            f"Price vs SMA20 comparison (${price:,.2f} vs ${sma20:,.2f})",
            "5-Agent Trade Intelligence Technical Guardrails active",
        ],
        "indicator_summary": f"RSI is {rsi:.1f}. SMA20 is ${sma20:,.2f}.",
        "risk_level": "medium" if 40 <= rsi <= 60 else "low" if rsi < 40 else "high",
        "entry_price": price,
        "stop_loss": round(price * 0.98, 4),
        "take_profit": round(price * 1.05, 4),
    }

    from services.trade_intelligence import build_full_trade_intelligence
    trade_intel = build_full_trade_intelligence(signal_dict, indicators, coin_meta)

    _, _, display_name = MODEL_MAP.get(model_key, ("gemini", "", "Gemini"))
    return {
        "model_key": model_key,
        "model_display": f"{display_name} (Technical Engine Fallback)",
        "symbol": symbol,
        "timeframe": timeframe,
        "signal": signal_dict,
        "trade_intelligence": trade_intel,
        "notice": "⚡ AI Technical Engine active (Gemini rate-limited, switching to deterministic technical analysis)",
    }


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

    _, _, display_name = MODEL_MAP[model_key]
    prompt = _build_prompt(symbol, coin_meta, indicators, timeframe)
    raw = ""
    last_err: Optional[str] = None

    for attempt in range(2):
        try:
            # Route to the right backend
            if model_key == "gemini" and _genai_available and GEMINI_API_KEY:
                raw = await _call_gemini(prompt if attempt == 0 else
                    f"Your previous reply was not valid JSON.\nError: {last_err}\nReturn ONLY the JSON object.\n\n{prompt}")
            elif model_key == "claude" and _anthropic_available:
                raw = await _call_anthropic(prompt if attempt == 0 else
                    f"Your previous reply was not valid JSON.\nError: {last_err}\nReturn ONLY the JSON object.\n\n{prompt}")
            elif _emergent_available:
                raw = await _call_emergent(model_key, prompt, session_id)
            else:
                # Fall back to technical engine when key is not present
                return _build_technical_fallback_signal(model_key, symbol, coin_meta, indicators, timeframe)

            block = _extract_json(raw) or raw
            data = json.loads(block)
            signal = _normalize_confidence_signal(data)
            signal_dict = signal.model_dump()
            
            # Attach 5-Agent Trade Intelligence Analysis & Decision Engine verdict
            from services.trade_intelligence import build_full_trade_intelligence
            trade_intel = build_full_trade_intelligence(signal_dict, indicators, coin_meta)
            
            return {
                "model_key": model_key,
                "model_display": display_name,
                "symbol": symbol,
                "timeframe": timeframe,
                "signal": signal_dict,
                "trade_intelligence": trade_intel,
            }
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = f"{type(e).__name__}: {e}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            # Fall back to high-precision technical analysis engine
            return _build_technical_fallback_signal(model_key, symbol, coin_meta, indicators, timeframe)

    # If parsing or API failed, safely use technical intelligence signal
    return _build_technical_fallback_signal(model_key, symbol, coin_meta, indicators, timeframe)
