"""Autonomous AI Portfolio Manager Endpoints.

Routes:
  POST /api/portfolio-manager/run-cycle : Trigger 1-click autonomous scan-score-decide-allocate-execute cycle
  GET  /api/portfolio-manager/status    : Retrieve current allocations, prediction score board, and logs
  POST /api/portfolio-manager/config    : Update allocated capital ($1,000 / $10,000) and settings
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.auth import current_user, optional_user
from services.autonomous_portfolio import (
    run_autonomous_cycle,
    get_latest_cycle,
    DEFAULT_CAPITAL,
    ASSET_UNIVERSE,
)

router = APIRouter(prefix="/portfolio-manager", tags=["portfolio_manager"])


def _db():
    from server import db as _database
    return _database


class PortfolioConfig(BaseModel):
    allocated_capital: float = Field(1000.0, description="Allocated trading capital USD")
    auto_rebalance: bool = Field(True, description="Enable automated background rebalancing")


class RunCycleRequest(BaseModel):
    capital: Optional[float] = Field(None, description="Optional capital allocation override")


@router.get("/status")
async def get_manager_status(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"

    # Safely fetch config — table may not exist yet
    try:
        config_doc = await _db().portfolio_manager_configs.find_one({"user_id": user_id}, {"_id": 0})
    except Exception:
        config_doc = None
    allocated_capital = float(config_doc.get("allocated_capital") if config_doc else DEFAULT_CAPITAL)
    auto_rebalance = bool(config_doc.get("auto_rebalance") if config_doc else True)

    # Safely fetch portfolio cash
    try:
        portfolio_doc = await _db().portfolios.find_one({"user_id": user_id}, {"_id": 0})
    except Exception:
        portfolio_doc = None
    cash_buffer = float(portfolio_doc.get("cash") if portfolio_doc else allocated_capital)

    # Get positions
    try:
        positions = await _db().positions.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    except Exception:
        positions = []

    # Get recent cycles — fallback to memory cache or auto-run initial cycle on first load
    try:
        cycles = await _db().autonomous_cycles.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)
    except Exception:
        cycles = []

    if not cycles:
        latest = get_latest_cycle(user_id)
        if latest:
            cycles = [latest]
        else:
            try:
                first_cycle = await run_autonomous_cycle(_db(), user_id, allocated_capital)
                cycles = [first_cycle]
            except Exception:
                cycles = []

    return {
        "user_id": user_id,
        "allocated_capital": allocated_capital,
        "auto_rebalance": auto_rebalance,
        "cash_buffer": cash_buffer,
        "positions": positions,
        "recent_cycles": cycles,
        "asset_universe": ASSET_UNIVERSE,
    }


@router.post("/run-cycle")
async def execute_autonomous_cycle(
    req: Optional[RunCycleRequest] = None,
    user: Optional[Dict[str, Any]] = Depends(optional_user),
):
    user_id = user["id"] if user else "demo-user"

    try:
        config_doc = await _db().portfolio_manager_configs.find_one({"user_id": user_id}, {"_id": 0})
    except Exception:
        config_doc = None
    capital = (req.capital if req and req.capital else None) or (config_doc.get("allocated_capital") if config_doc else DEFAULT_CAPITAL)

    try:
        cycle_result = await run_autonomous_cycle(_db(), user_id, allocated_capital=capital)
        return {
            "status": "ok",
            "message": "Autonomous 5-Brain rebalance cycle completed successfully.",
            "cycle": cycle_result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Autonomous cycle failed: {e}")


@router.post("/config")
async def save_manager_config(
    cfg: PortfolioConfig,
    user: Optional[Dict[str, Any]] = Depends(optional_user),
):
    user_id = user["id"] if user else "demo-user"

    doc = {
        "user_id": user_id,
        "allocated_capital": cfg.allocated_capital,
        "auto_rebalance": cfg.auto_rebalance,
    }
    try:
        await _db().portfolio_manager_configs.update_one(
            {"user_id": user_id},
            {"$set": doc},
            upsert=True,
        )
    except Exception:
        pass  # Config save skipped — table may not exist yet; still acknowledge the setting
    return {"status": "ok", "config": doc}
