"""Backtest endpoints — run strategies, list saved backtests."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services import market_data as md
from services.auth import current_user, optional_user
from services.backtest import STRATEGIES

router = APIRouter(prefix="/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    symbol: str = Field(..., description="e.g. BTCUSDT")
    interval: str = "1h"
    limit: int = 500
    strategy: str = Field("sma_crossover", description="sma_crossover | rsi | macd")
    initial_cash: float = 10000.0
    fee_rate: float = 0.001
    # Optional strategy params
    fast: Optional[int] = None
    slow: Optional[int] = None
    rsi_period: Optional[int] = None
    oversold: Optional[float] = None
    overbought: Optional[float] = None


def _db():
    from server import db as _database
    return _database


@router.post("/run")
async def run_backtest(req: BacktestRequest, user: Optional[Dict[str, Any]] = Depends(optional_user)):
    if req.strategy not in STRATEGIES:
        raise HTTPException(status_code=400, detail=f"strategy must be one of: {list(STRATEGIES.keys())}")
    try:
        df, source = await md.get_klines(req.symbol, req.interval, min(req.limit, 1000))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Klines unavailable: {e}")
    if df is None or len(df) < 60:
        raise HTTPException(status_code=400, detail="Not enough candles to backtest")

    fn = STRATEGIES[req.strategy]
    if req.strategy == "sma_crossover":
        result = fn(df, fast=req.fast or 20, slow=req.slow or 50,
                    initial_cash=req.initial_cash, fee_rate=req.fee_rate)
    elif req.strategy == "rsi":
        result = fn(df, period=req.rsi_period or 14, oversold=req.oversold or 30.0,
                    overbought=req.overbought or 70.0, initial_cash=req.initial_cash, fee_rate=req.fee_rate)
    else:
        result = fn(df, initial_cash=req.initial_cash, fee_rate=req.fee_rate)

    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"] if user else None,
        "symbol": req.symbol,
        "interval": req.interval,
        "limit": req.limit,
        "strategy": req.strategy,
        "initial_cash": req.initial_cash,
        "fee_rate": req.fee_rate,
        "kline_source": source,
        "result": result,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    await _db().backtest_runs.insert_one(dict(doc))
    return {
        "id": doc["id"],
        "symbol": req.symbol,
        "interval": req.interval,
        "strategy": req.strategy,
        "result": result,
        "created_at": doc["created_at"],
    }


@router.get("/history")
async def history(user: Dict[str, Any] = Depends(current_user), limit: int = 20):
    cursor = _db().backtest_runs.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return {"backtests": docs}
