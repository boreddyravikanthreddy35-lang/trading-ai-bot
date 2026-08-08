"""AI Signal endpoints — generate signals, list history."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services import market_data as md
from services import ai_signals as ai
from services.auth import current_user, optional_user
from services.indicators import compute_indicators

router = APIRouter(prefix="/ai", tags=["ai"])


class SignalRequest(BaseModel):
    symbol: str = Field(..., description="e.g. BTCUSDT")
    timeframe: str = "1h"
    model: str = Field("claude", description="claude | gemini | both")


def _db():
    # Import inline to avoid circular imports
    from server import db as _database
    return _database


@router.post("/signal")
async def generate_signal(req: SignalRequest, user: Optional[Dict[str, Any]] = Depends(optional_user)):
    if req.model not in {"claude", "gemini", "both"}:
        raise HTTPException(status_code=400, detail="model must be one of: claude | gemini | both")

    # 1) Fetch klines + indicators
    try:
        df, kline_source = await md.get_klines(req.symbol, req.timeframe, 250)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch klines: {e}")
    if df is None or len(df) < 30:
        raise HTTPException(status_code=400, detail="Not enough candles to compute indicators")

    indicators = compute_indicators(df)

    # 2) Build coin meta (try CoinGecko markets, fall back to on-chain synth)
    cg_id = md.SYMBOL_TO_COINGECKO.get(req.symbol)
    coin_meta: Dict[str, Any] = {
        "name": req.symbol.replace("USDT", ""),
        "symbol": req.symbol,
        "market_cap_rank": None,
        "current_price": indicators.get("price"),
        "price_change_percentage_24h": indicators.get("pct_change_24h"),
        "total_volume": indicators.get("volume_24h"),
    }
    if cg_id:
        try:
            all_markets = await md.coingecko_markets(per_page=100)
            match = next((m for m in all_markets if m["id"] == cg_id), None)
            if match:
                coin_meta = {
                    "name": match.get("name", coin_meta["name"]),
                    "symbol": req.symbol,
                    "market_cap_rank": match.get("market_cap_rank"),
                    "current_price": match.get("current_price"),
                    "price_change_percentage_24h": match.get("price_change_percentage_24h"),
                    "total_volume": match.get("total_volume"),
                }
        except Exception:
            pass

    session_base = f"signal-{req.symbol}-{uuid.uuid4().hex[:8]}"

    # 3) Call one or both models
    results: List[Dict[str, Any]] = []
    models = [req.model] if req.model != "both" else ["claude", "gemini"]
    for m in models:
        res = await ai.generate_signal(
            model_key=m,
            symbol=req.symbol,
            coin_meta=coin_meta,
            indicators=indicators,
            timeframe=req.timeframe,
            session_id=f"{session_base}-{m}",
        )
        results.append(res)

    # 4) Persist to DB
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"] if user else None,
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "model": req.model,
        "kline_source": kline_source,
        "indicators": indicators,
        "coin_meta": coin_meta,
        "results": results,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    await _db().signal_runs.insert_one(dict(doc))

    return {
        "id": doc["id"],
        "symbol": req.symbol,
        "timeframe": req.timeframe,
        "model": req.model,
        "indicators": indicators,
        "coin_meta": coin_meta,
        "results": results,
        "created_at": doc["created_at"],
    }


@router.get("/history")
async def list_signals(user: Dict[str, Any] = Depends(current_user), limit: int = 50):
    cursor = _db().signal_runs.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return {"signals": docs}


@router.get("/history/anonymous")
async def list_anonymous_signals(limit: int = 20):
    """Recent signals not tied to a user (for demo/preview)."""
    cursor = _db().signal_runs.find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return {"signals": docs}
