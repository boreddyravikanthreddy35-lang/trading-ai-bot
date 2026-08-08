"""Settings endpoints — Binance testnet, user preferences."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.auth import current_user
from services.binance_client import BinanceTestnetClient, BinanceError, GeoRestrictedError

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


@router.post("/exchange/binance-testnet/test")
async def test_binance_testnet(user: Dict[str, Any] = Depends(current_user)):
    """Verify Binance testnet connectivity + signed account access."""
    doc = await _db().exchange_settings.find_one(
        {"user_id": user["id"], "exchange": "binance_testnet"}, {"_id": 0}
    )
    if not doc:
        raise HTTPException(status_code=400, detail="No Binance testnet keys configured")
    client = BinanceTestnetClient(doc["api_key"], doc["api_secret"])
    result: Dict[str, Any] = {"ping": None, "account": None, "error": None}
    try:
        await client.ping()
        result["ping"] = "ok"
        acc = await client.account()
        # Trim balances to non-zero
        balances = [
            {"asset": b["asset"], "free": float(b["free"]), "locked": float(b["locked"])}
            for b in (acc.get("balances") or [])
            if float(b.get("free", 0)) > 0 or float(b.get("locked", 0)) > 0
        ]
        result["account"] = {"canTrade": acc.get("canTrade"), "balances": balances[:20]}
        result["status"] = "ok"
    except GeoRestrictedError as e:
        result["error"] = str(e)
        result["status"] = "geo_restricted"
    except BinanceError as e:
        result["error"] = str(e)
        result["status"] = "error"
    return result

