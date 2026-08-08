"""AI Chat Analyst endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.auth import current_user
from services import chat_analyst

router = APIRouter(prefix="/chat", tags=["chat"])


def _db():
    from server import db as _database
    return _database


class ChatMessageRequest(BaseModel):
    signal_id: str = Field(..., description="The AI signal to discuss")
    model: str = Field("claude", description="claude | gemini")
    message: str = Field(..., min_length=1, max_length=2000)


@router.get("/{signal_id}")
async def get_conversation(signal_id: str, user: Dict[str, Any] = Depends(current_user)):
    signal = await _db().signal_runs.find_one({"id": signal_id, "user_id": user["id"]}, {"_id": 0})
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    conv = await _db().chat_conversations.find_one({"signal_id": signal_id, "user_id": user["id"]}, {"_id": 0})
    return {"signal": signal, "conversation": conv or {"signal_id": signal_id, "user_id": user["id"], "messages": []}}


@router.post("/{signal_id}/message")
async def send_message(signal_id: str, req: ChatMessageRequest, user: Dict[str, Any] = Depends(current_user)):
    if req.model not in {"claude", "gemini"}:
        raise HTTPException(status_code=400, detail="model must be 'claude' or 'gemini'")

    signal = await _db().signal_runs.find_one({"id": signal_id, "user_id": user["id"]}, {"_id": 0})
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    conv = await _db().chat_conversations.find_one({"signal_id": signal_id, "user_id": user["id"]}, {"_id": 0})
    if not conv:
        conv = {
            "id": str(uuid.uuid4()),
            "signal_id": signal_id,
            "user_id": user["id"],
            "messages": [],
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }

    history = conv.get("messages", [])
    try:
        reply = await chat_analyst.chat_reply(
            model_key=req.model, signal_doc=signal, history=history, user_message=req.message
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI chat failed: {e}")

    now = datetime.now(tz=timezone.utc).isoformat()
    new_messages = history + [
        {"role": "user", "content": req.message, "created_at": now},
        {"role": "assistant", "model": req.model, "content": reply, "created_at": now},
    ]
    conv["messages"] = new_messages
    conv["updated_at"] = now

    await _db().chat_conversations.update_one(
        {"signal_id": signal_id, "user_id": user["id"]},
        {"$set": conv},
        upsert=True,
    )
    return {"messages": new_messages, "reply": reply}
