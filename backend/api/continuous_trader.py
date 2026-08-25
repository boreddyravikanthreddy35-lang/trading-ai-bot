from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.auth import optional_user
from services.continuous_trader import (
    start_continuous_trading,
    pause_continuous_trading,
    resume_continuous_trading,
    stop_continuous_trading,
    sell_position_now,
    sell_all_positions,
    get_dashboard_data,
    get_trader_status,
)

router = APIRouter(prefix="/continuous-trader", tags=["continuous_trader"])


def _db():
    from server import db as _database
    return _database


class StartTraderRequest(BaseModel):
    capital: Optional[float] = Field(None, description="Initial capital allocation")
    symbols: Optional[List[str]] = Field(None, description="List of symbols to trade")
    interval_minutes: Optional[int] = Field(None, description="Trading interval in minutes")
    stop_loss_pct: Optional[float] = Field(None, description="Stop loss percentage")
    take_profit_pct: Optional[float] = Field(None, description="Take profit percentage")
    buy_threshold: Optional[int] = Field(None, description="Buy threshold score")
    sell_threshold: Optional[int] = Field(None, description="Sell threshold score")


class StopTraderRequest(BaseModel):
    sell_all: bool = Field(False, description="Whether to sell all positions when stopping")


@router.post("/start")
async def start_trading(
    req: StartTraderRequest = StartTraderRequest(),
    user: Optional[Dict[str, Any]] = Depends(optional_user),
):
    user_id = user["id"] if user else "demo-user"
    try:
        config = await start_continuous_trading(
            _db(),
            user_id,
            capital=req.capital,
            symbols=req.symbols,
            interval_minutes=req.interval_minutes,
            stop_loss_pct=req.stop_loss_pct,
            take_profit_pct=req.take_profit_pct,
            buy_threshold=req.buy_threshold,
            sell_threshold=req.sell_threshold,
        )
        return {
            "status": "ok",
            "message": "Continuous trading started successfully",
            "config": config,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to start continuous trading: {e}")


@router.post("/pause")
async def pause_trading(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    try:
        pause_continuous_trading(user_id)
        return {"status": "ok", "message": "AI trading paused"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to pause continuous trading: {e}")


@router.post("/resume")
async def resume_trading(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    try:
        resume_continuous_trading(user_id)
        return {"status": "ok", "message": "AI trading resumed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to resume continuous trading: {e}")


@router.post("/stop")
async def stop_trading(
    req: StopTraderRequest = StopTraderRequest(),
    user: Optional[Dict[str, Any]] = Depends(optional_user),
):
    user_id = user["id"] if user else "demo-user"
    try:
        await stop_continuous_trading(_db(), user_id, req.sell_all)
        return {"status": "ok", "message": "Continuous trading stopped successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to stop continuous trading: {e}")


@router.post("/sell-now/{symbol}")
async def sell_now(
    symbol: str,
    user: Optional[Dict[str, Any]] = Depends(optional_user),
):
    user_id = user["id"] if user else "demo-user"
    try:
        result = await sell_position_now(_db(), user_id, symbol)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to sell position: {e}")


@router.post("/sell-all")
async def sell_all(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    try:
        results = await sell_all_positions(_db(), user_id)
        return {"status": "ok", "results": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to sell all positions: {e}")


@router.get("/dashboard")
async def get_dashboard(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    try:
        data = await get_dashboard_data(_db(), user_id)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get dashboard data: {e}")


@router.get("/status")
async def get_status(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    try:
        status = get_trader_status(user_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get trader status: {e}")
