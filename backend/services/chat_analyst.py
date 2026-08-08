"""AI Chat Analyst — multi-turn conversations grounded in a specific trading signal."""
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

MODEL_MAP = {
    "claude": ("anthropic", "claude-sonnet-4-5-20250929", "Claude Sonnet 4.5"),
    "gemini": ("gemini", "gemini-2.5-pro", "Gemini 2.5 Pro"),
}

SYSTEM_TEMPLATE = """You are an expert crypto trading analyst helping the user
discuss a specific trading signal you previously issued.

Context (data you already used to produce the signal):
{context}

Answer the user's questions clearly and concisely (3-6 sentences).
Explain your reasoning, cite indicator values or price levels when relevant.
If the user proposes an alternative view, engage constructively.
Do NOT invent price data — use only what is in the context above and general market knowledge.
Do NOT claim to have real-time market access during this chat.
"""


def build_context(signal_doc: Dict[str, Any], model_key: str) -> str:
    """Build a compact context string for the system prompt."""
    results = signal_doc.get("results") or []
    target = next((r for r in results if r.get("model_key") == model_key), results[0] if results else {})
    sig = target.get("signal") or {}
    ind = signal_doc.get("indicators") or {}
    meta = signal_doc.get("coin_meta") or {}
    return (
        f"Symbol: {signal_doc.get('symbol')}\n"
        f"Timeframe: {signal_doc.get('timeframe')}\n"
        f"Model: {target.get('model_display')}\n"
        f"Action: {sig.get('action')}  Confidence: {sig.get('confidence')}  Risk: {sig.get('risk_level')}\n"
        f"Entry: {sig.get('entry_price')}  Stop: {sig.get('stop_loss')}  Take-profit: {sig.get('take_profit')}\n"
        f"Reasoning: {sig.get('reasoning')}\n"
        f"Key factors: {sig.get('key_factors')}\n"
        f"Indicator summary: {sig.get('indicator_summary')}\n"
        f"Raw indicators: {ind}\n"
        f"Coin meta: name={meta.get('name')} rank={meta.get('market_cap_rank')} 24h_pct={meta.get('price_change_percentage_24h')}"
    )


async def chat_reply(
    model_key: str,
    signal_doc: Dict[str, Any],
    history: List[Dict[str, Any]],
    user_message: str,
) -> str:
    if model_key not in MODEL_MAP:
        raise ValueError(f"Unknown model_key: {model_key}")
    if not EMERGENT_LLM_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY not configured")

    provider, model_name, _display = MODEL_MAP[model_key]
    session_id = f"chat-{signal_doc.get('id') or uuid.uuid4().hex[:12]}-{model_key}"
    context = build_context(signal_doc, model_key)
    system = SYSTEM_TEMPLATE.format(context=context)

    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system).with_model(provider, model_name)

    # Replay history so the model has memory across turns
    for h in history:
        if h.get("role") == "user":
            # We fire-and-forget the message; the reply is discarded because we already have it stored
            try:
                await chat.send_message(UserMessage(text=h["content"]))
            except Exception:
                pass

    reply = await chat.send_message(UserMessage(text=user_message))
    return reply
