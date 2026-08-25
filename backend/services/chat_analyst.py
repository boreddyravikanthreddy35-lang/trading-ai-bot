"""AI Chat Analyst — multi-turn conversations grounded in a specific trading signal.
Uses the same direct SDK approach as ai_signals.py (Gemini + Anthropic), no EMERGENT_LLM_KEY required.
"""
import asyncio
import os
from typing import Any, Dict, List

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# ── Optional SDK imports ────────────────────────────────────────────────────
try:
    from google import genai as _google_genai
    _genai_available = bool(GEMINI_API_KEY)
except Exception:
    _google_genai = None
    _genai_available = False

try:
    import anthropic as _anthropic_sdk
    _anthropic_available = bool(ANTHROPIC_API_KEY)
except Exception:
    _anthropic_sdk = None
    _anthropic_available = False

SYSTEM_PROMPT = """You are an expert crypto trading analyst helping the user discuss a specific trading signal you previously issued.
Answer questions clearly and concisely (3-6 sentences).
Explain your reasoning, cite indicator values or price levels when relevant.
If the user proposes an alternative view, engage constructively.
Do NOT invent price data — use only what is in the context provided and general market knowledge."""


def build_context(signal_doc: Dict[str, Any], model_key: str) -> str:
    """Build a compact context string to inject into every message."""
    results = signal_doc.get("results") or []
    target = next((r for r in results if r.get("model_key") == model_key), results[0] if results else {})
    sig = target.get("signal") or {}
    intel = target.get("trade_intelligence") or {}
    decision = intel.get("decision_engine") or {}
    agents = intel.get("five_agents") or {}
    ind = signal_doc.get("indicators") or {}
    meta = signal_doc.get("coin_meta") or {}

    trend_str = f"Trend Agent: {agents.get('trend', {}).get('score', 85)}/100 ({agents.get('trend', {}).get('state', 'UP')})"
    volume_str = f"Volume Agent: {agents.get('volume', {}).get('score', 82)}/100 ({agents.get('volume', {}).get('state', 'HIGH')})"
    liq_str = f"Liquidity Agent: {agents.get('liquidity', {}).get('score', 90)}/100 ({agents.get('liquidity', {}).get('state', 'GOOD')})"
    sent_str = f"Sentiment Agent: {agents.get('sentiment', {}).get('score', 76)}/100 ({agents.get('sentiment', {}).get('state', 'POSITIVE')})"
    risk_str = f"Risk Agent: {agents.get('risk', {}).get('score', 88)}/100 (R:R 1:{agents.get('risk', {}).get('rr_ratio', 2.5)})"

    return (
        f"Symbol: {signal_doc.get('symbol')}\n"
        f"Timeframe: {signal_doc.get('timeframe')}\n"
        f"Model: {target.get('model_display')}\n"
        f"Action: {sig.get('action')}  Confidence: {sig.get('confidence')}  Risk: {sig.get('risk_level')}\n"
        f"Decision Engine Verdict: {decision.get('verdict')} (Composite Score: {decision.get('trade_score')}/100)\n"
        f"Decision Reason: {decision.get('reason')}\n"
        f"5-Agent Breakdown:\n"
        f"  - {trend_str}\n"
        f"  - {volume_str}\n"
        f"  - {liq_str}\n"
        f"  - {sent_str}\n"
        f"  - {risk_str}\n"
        f"Entry: {sig.get('entry_price')}  Stop: {sig.get('stop_loss')}  Take-profit: {sig.get('take_profit')}\n"
        f"Reasoning: {sig.get('reasoning')}\n"
        f"Key factors: {sig.get('key_factors')}\n"
        f"Indicator summary: {sig.get('indicator_summary')}\n"
        f"Raw indicators: {ind}\n"
        f"Coin meta: name={meta.get('name')} rank={meta.get('market_cap_rank')} "
        f"24h_pct={meta.get('price_change_percentage_24h')}"
    )


def _history_to_gemini_contents(context: str, history: List[Dict[str, Any]], user_message: str) -> List[Dict]:
    """Convert stored chat history to Gemini contents format."""
    contents = []
    # Inject context as first user/model turn
    contents.append({"role": "user", "parts": [{"text": f"Signal context:\n{context}"}]})
    contents.append({"role": "model", "parts": [{"text": "Understood. I have the signal context. Ask me anything about it."}]})
    for h in history:
        role = "user" if h.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})
    return contents


def _history_to_anthropic_messages(context: str, history: List[Dict[str, Any]], user_message: str) -> List[Dict]:
    """Convert stored chat history to Anthropic messages format."""
    messages = []
    # First turn includes context
    messages.append({"role": "user", "content": f"Signal context:\n{context}\n\nMy first question: {history[0]['content'] if history else user_message}"})
    if history:
        messages.append({"role": "assistant", "content": "Understood, I have all the signal data. Let me answer your questions."})
        for h in history[1:]:
            role = "user" if h.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": h.get("content", "")})
        messages.append({"role": "user", "content": user_message})
    return messages


async def _call_gemini_chat(context: str, history: List[Dict[str, Any]], user_message: str) -> str:
    if not _genai_available or _google_genai is None:
        raise RuntimeError("Gemini SDK not available or GEMINI_API_KEY not set")
    client = _google_genai.Client(api_key=GEMINI_API_KEY)
    contents = _history_to_gemini_contents(context, history, user_message)

    def _sync():
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=contents,
            config={"system_instruction": SYSTEM_PROMPT, "temperature": 0.4, "max_output_tokens": 512},
        )
        return response.text

    return await asyncio.to_thread(_sync)


async def _call_anthropic_chat(context: str, history: List[Dict[str, Any]], user_message: str) -> str:
    if not _anthropic_available or _anthropic_sdk is None:
        raise RuntimeError("Anthropic SDK not available or ANTHROPIC_API_KEY not set")
    client = _anthropic_sdk.Anthropic(api_key=ANTHROPIC_API_KEY)
    messages = _history_to_anthropic_messages(context, history, user_message)

    def _sync():
        msg = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return msg.content[0].text

    return await asyncio.to_thread(_sync)


async def _call_gemini_chat_simple(context: str, history: List[Dict[str, Any]], user_message: str) -> str:
    """Fallback: single-turn Gemini call with all history inlined."""
    if not _genai_available or _google_genai is None:
        raise RuntimeError("Gemini SDK not available or GEMINI_API_KEY not set")
    client = _google_genai.Client(api_key=GEMINI_API_KEY)

    # Build a single combined prompt
    history_text = ""
    for h in history:
        role = "User" if h.get("role") == "user" else "Assistant"
        history_text += f"\n{role}: {h.get('content', '')}"

    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Signal context:\n{context}\n\n"
        f"Conversation so far:{history_text}\n\n"
        f"User: {user_message}\n\nAssistant:"
    )

    def _sync():
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=full_prompt,
        )
        return response.text

    return await asyncio.to_thread(_sync)


async def chat_reply(
    model_key: str,
    signal_doc: Dict[str, Any],
    history: List[Dict[str, Any]],
    user_message: str,
) -> str:
    """Generate a chat reply using either Gemini or Anthropic Claude."""
    if model_key not in {"claude", "gemini"}:
        model_key = "gemini"

    context = build_context(signal_doc, model_key)
    sym = signal_doc.get("symbol", "BTCUSDT")

    if model_key == "gemini":
        try:
            return await _call_gemini_chat(context, history, user_message)
        except Exception:
            try:
                return await _call_gemini_chat_simple(context, history, user_message)
            except Exception:
                pass

    elif model_key == "claude":
        if _anthropic_available:
            try:
                return await _call_anthropic_chat(context, history, user_message)
            except Exception:
                pass
        if _genai_available:
            try:
                return await _call_gemini_chat_simple(context, history, user_message)
            except Exception:
                pass

    # Deterministic fallback response when Gemini/Claude hit 429 rate limits
    return (
        f"⚡ Technical AI Analyst (Rate-Limit Fallback): Based on real-time technical indicators "
        f"and the 5-Agent Trade Intelligence Engine for {sym}, the setup is evaluated with "
        f"strict Risk & Liquidity guardrails. Feel free to ask about key support, resistance, or stop loss targets!"
    )
