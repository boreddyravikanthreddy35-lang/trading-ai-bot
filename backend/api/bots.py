"""AI auto-trading bot CRUD + run history + manual run."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.auth import current_user
from services import scheduler as sched
from services.bot_runner import run_bot_once
from services.entitlements import enforce_bot_quota, enforce_testnet

router = APIRouter(prefix="/bots", tags=["bots"])


def _db():
    from server import db as _database
    return _database


class BotCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    symbol: str = Field("BTCUSDT")
    timeframe: str = Field("1h")
    model: str = Field("claude", description="claude | gemini")
    interval_minutes: int = Field(60, ge=1, le=1440, description="How often the bot runs")
    size_usd: float = Field(100.0, gt=0)
    min_confidence: float = Field(0.65, ge=0.0, le=1.0)
    allow_actions: List[str] = Field(default_factory=lambda: ["BUY", "SELL"])
    use_testnet: bool = False
    max_daily_loss: float = 500.0
    active: bool = False


class BotUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    model: Optional[str] = None
    interval_minutes: Optional[int] = None
    size_usd: Optional[float] = None
    min_confidence: Optional[float] = None
    allow_actions: Optional[List[str]] = None
    use_testnet: Optional[bool] = None
    max_daily_loss: Optional[float] = None
    active: Optional[bool] = None


def _serialize(bot: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in bot.items() if k != "_id"}


@router.get("")
async def list_bots(user: Dict[str, Any] = Depends(current_user)):
    docs = await _db().bots.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"bots": docs}


@router.post("")
async def create_bot(req: BotCreate, user: Dict[str, Any] = Depends(current_user)):
    if req.model not in {"claude", "gemini"}:
        raise HTTPException(status_code=400, detail="model must be 'claude' or 'gemini'")
    # Entitlements
    await enforce_bot_quota(_db(), user["id"])
    if req.use_testnet:
        await enforce_testnet(_db(), user["id"])
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        **req.model_dump(),
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "updated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    await _db().bots.insert_one(dict(doc))
    if doc["active"]:
        sched.schedule_bot(doc)
    return _serialize(doc)


@router.patch("/{bot_id}")
async def update_bot(bot_id: str, req: BotUpdate, user: Dict[str, Any] = Depends(current_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "model" in updates and updates["model"] not in {"claude", "gemini"}:
        raise HTTPException(status_code=400, detail="model must be 'claude' or 'gemini'")
    if updates.get("use_testnet") is True:
        await enforce_testnet(_db(), user["id"])
    updates["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    r = await _db().bots.update_one({"id": bot_id, "user_id": user["id"]}, {"$set": updates})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bot not found")
    bot = await _db().bots.find_one({"id": bot_id}, {"_id": 0})
    # Sync scheduler
    if bot.get("active"):
        sched.schedule_bot(bot)
    else:
        sched.unschedule_bot(bot_id)
    return bot


@router.delete("/{bot_id}")
async def delete_bot(bot_id: str, user: Dict[str, Any] = Depends(current_user)):
    r = await _db().bots.delete_one({"id": bot_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bot not found")
    sched.unschedule_bot(bot_id)
    return {"status": "ok"}


@router.post("/{bot_id}/run")
async def run_bot_now(bot_id: str, user: Dict[str, Any] = Depends(current_user)):
    bot = await _db().bots.find_one({"id": bot_id, "user_id": user["id"]}, {"_id": 0})
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    result = await run_bot_once(_db(), bot)
    return {k: v for k, v in result.items() if k != "_id"}


@router.get("/{bot_id}/runs")
async def bot_run_history(bot_id: str, user: Dict[str, Any] = Depends(current_user), limit: int = 50):
    bot = await _db().bots.find_one({"id": bot_id, "user_id": user["id"]}, {"_id": 0})
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    runs = await _db().bot_runs.find({"bot_id": bot_id}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    trades_24h = await _db().trades.count_documents({"user_id": user["id"], "source": "bot"})
    return {"bot": bot, "runs": runs, "total_bot_trades": trades_24h}
