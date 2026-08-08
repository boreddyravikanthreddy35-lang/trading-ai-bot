"""Settings endpoints — Binance testnet placeholder, user preferences."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.auth import current_user

router = APIRouter(prefix="/settings", tags=["settings"])


def _db():
    from server import db as _database
    return _database


class BinanceTestnetKeys(BaseModel):
    api_key: str
    api_secret: str
    enabled: bool = False


@router.get("/exchange/binance-testnet")
async def get_binance_testnet(user: Dict[str, Any] = Depends(current_user)):
    doc = await _db().exchange_settings.find_one(
        {"user_id": user["id"], "exchange": "binance_testnet"}, {"_id": 0}
    )
    if not doc:
        return {"configured": False, "enabled": False, "api_key_masked": None}
    api_key = doc.get("api_key", "")
    masked = (api_key[:4] + "•" * 12 + api_key[-4:]) if len(api_key) >= 8 else None
    return {"configured": True, "enabled": doc.get("enabled", False), "api_key_masked": masked}


@router.post("/exchange/binance-testnet")
async def save_binance_testnet(req: BinanceTestnetKeys, user: Dict[str, Any] = Depends(current_user)):
    doc = {
        "user_id": user["id"],
        "exchange": "binance_testnet",
        "api_key": req.api_key,
        "api_secret": req.api_secret,  # NOTE: in production, encrypt at rest
        "enabled": req.enabled,
    }
    await _db().exchange_settings.update_one(
        {"user_id": user["id"], "exchange": "binance_testnet"},
        {"$set": doc},
        upsert=True,
    )
    masked = (req.api_key[:4] + "•" * 12 + req.api_key[-4:]) if len(req.api_key) >= 8 else None
    return {"configured": True, "enabled": req.enabled, "api_key_masked": masked}


@router.delete("/exchange/binance-testnet")
async def delete_binance_testnet(user: Dict[str, Any] = Depends(current_user)):
    await _db().exchange_settings.delete_one(
        {"user_id": user["id"], "exchange": "binance_testnet"}
    )
    return {"configured": False, "enabled": False}
