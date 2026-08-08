"""Strategy presets — save/load named backtest parameter sets."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.auth import current_user

router = APIRouter(prefix="/presets", tags=["presets"])


def _db():
    from server import db as _database
    return _database


class PresetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    strategy: str = Field(..., description="sma_crossover | rsi | macd")
    interval: str = "1h"
    limit: int = 500
    initial_cash: float = 10000.0
    fee_rate: float = 0.001
    fast: Optional[int] = None
    slow: Optional[int] = None
    rsi_period: Optional[int] = None
    oversold: Optional[float] = None
    overbought: Optional[float] = None


class PresetUpdate(BaseModel):
    name: Optional[str] = None
    strategy: Optional[str] = None
    interval: Optional[str] = None
    limit: Optional[int] = None
    initial_cash: Optional[float] = None
    fee_rate: Optional[float] = None
    fast: Optional[int] = None
    slow: Optional[int] = None
    rsi_period: Optional[int] = None
    oversold: Optional[float] = None
    overbought: Optional[float] = None


@router.get("")
async def list_presets(user: Dict[str, Any] = Depends(current_user)):
    cursor = _db().strategy_presets.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    docs = await cursor.to_list(200)
    return {"presets": docs}


@router.post("")
async def create_preset(req: PresetCreate, user: Dict[str, Any] = Depends(current_user)):
    if req.strategy not in {"sma_crossover", "rsi", "macd"}:
        raise HTTPException(status_code=400, detail="invalid strategy")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": req.name,
        "strategy": req.strategy,
        "interval": req.interval,
        "limit": req.limit,
        "initial_cash": req.initial_cash,
        "fee_rate": req.fee_rate,
        "fast": req.fast,
        "slow": req.slow,
        "rsi_period": req.rsi_period,
        "oversold": req.oversold,
        "overbought": req.overbought,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    await _db().strategy_presets.insert_one(dict(doc))
    return doc


@router.patch("/{preset_id}")
async def update_preset(preset_id: str, req: PresetUpdate, user: Dict[str, Any] = Depends(current_user)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    r = await _db().strategy_presets.update_one(
        {"id": preset_id, "user_id": user["id"]}, {"$set": updates}
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Preset not found")
    return await _db().strategy_presets.find_one({"id": preset_id}, {"_id": 0})


@router.delete("/{preset_id}")
async def delete_preset(preset_id: str, user: Dict[str, Any] = Depends(current_user)):
    r = await _db().strategy_presets.delete_one({"id": preset_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"status": "ok"}
