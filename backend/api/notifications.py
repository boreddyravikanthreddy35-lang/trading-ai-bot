"""In-app notifications."""
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends

from services.auth import current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _db():
    from server import db as _database
    return _database


@router.get("")
async def list_notifications(user: Dict[str, Any] = Depends(current_user), limit: int = 50, only_unread: bool = False):
    q: Dict[str, Any] = {"user_id": user["id"]}
    if only_unread:
        q["read"] = False
    cursor = _db().notifications.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    unread_count = await _db().notifications.count_documents({"user_id": user["id"], "read": False})
    return {"notifications": docs, "unread_count": unread_count}


@router.post("/mark-read")
async def mark_all_read(user: Dict[str, Any] = Depends(current_user)):
    r = await _db().notifications.update_many(
        {"user_id": user["id"], "read": False}, {"$set": {"read": True, "read_at": datetime.now(tz=timezone.utc).isoformat()}}
    )
    return {"updated": r.modified_count}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, user: Dict[str, Any] = Depends(current_user)):
    await _db().notifications.update_one(
        {"id": notification_id, "user_id": user["id"]},
        {"$set": {"read": True, "read_at": datetime.now(tz=timezone.utc).isoformat()}},
    )
    return {"status": "ok"}
