"""Automatic AI Trader API - Production Pipeline Edition."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.auto_ai_trader import (
    get_auto_trader_trades,
    get_live_positions_with_pnl,
    get_user_capital,
    set_user_capital,
    get_user_budget_summary,
    set_user_budget,
    get_user_coins,
    set_user_coins,
    scan_coins,
    run_ai_cycle,
    set_ai_enabled,
    get_ai_enabled,
    reset_all_user_trading_data,
    DEFAULT_CAPITAL,
    DEFAULT_COINS,
)

router = APIRouter(prefix="/auto-trader", tags=["auto_trader"])


def _db():
    from server import db as _database
    return _database


class SetBudgetRequest(BaseModel):
    user_id: str = "default_user"
    budget_usdt: float = Field(..., gt=0, description="Allocated budget in USDT (e.g. 500 for $500.00 USDT)")


class SetCapitalRequest(BaseModel):
    user_id: str = "default_user"
    capital: float = Field(..., description="Fixed capital in USDT for AI trading")

class SetCoinsRequest(BaseModel):
    user_id: str = "default_user"
    coins: List[str] = Field(..., description="List of coins/symbols to trade e.g. ['BTCUSDT', 'SOLUSDT']")

class TradeCoinRequest(BaseModel):
    user_id: str = "default_user"
    symbol: str = Field(..., description="e.g. BTCUSDT")
    side: Optional[str] = Field(None, description="Force BUY or SELL, or let AI decide")

class RunCycleRequest(BaseModel):
    user_id: str = "default_user"
    symbols: Optional[List[str]] = None

class AiToggleRequest(BaseModel):
    user_id: str = "default_user"
    enabled: bool


@router.post("/set-capital")
async def set_capital(req: SetCapitalRequest):
    """Set fixed capital for AI trading. Persists until user changes it and syncs with wallet balance."""
    if req.capital < 10:
        raise HTTPException(status_code=400, detail="Minimum capital is $10")
    set_user_capital(req.user_id, req.capital)
    
    # Sync with ledger wallet: ensure user has at least this capital deposited
    db = _db()
    try:
        from services import wallet_service, ledger_service
        bal = await wallet_service.get_balance(db, req.user_id, "USDT")
        if bal["total"] < req.capital:
            diff = req.capital - bal["total"]
            import uuid
            dep_id = str(uuid.uuid4())
            # Record deposit in deposits table
            wallet = await wallet_service.get_or_create_wallet(db, req.user_id)
            try:
                await db.deposits.insert_one({
                    "id": dep_id,
                    "user_id": req.user_id,
                    "wallet_id": wallet["id"],
                    "asset": "USDT",
                    "amount": round(diff, 8),
                    "fee": 0.0,
                    "net_amount": round(diff, 8),
                    "status": "CREDITED",
                    "simulated": True,
                    "tx_hash": f"SIM_CAP_{dep_id[:8].upper()}",
                    "ledger_transaction_id": "",
                    "created_at": datetime.now(tz=timezone.utc).isoformat(),
                    "confirmed_at": datetime.now(tz=timezone.utc).isoformat(),
                })
            except Exception:
                pass
            ltx = await ledger_service.post_deposit(
                db, req.user_id, "USDT", diff,
                deposit_id=dep_id,
                metadata={"note": f"AI Trader Capital Allocation ({req.capital} USDT)", "simulated": True, "wallet_id": wallet["id"]}
            )
            try:
                await db.deposits.update_one({"id": dep_id}, {"$set": {"ledger_transaction_id": ltx["id"]}})
            except Exception:
                pass
    except Exception as e:
        print(f"[auto_trader] Wallet sync on set_capital: {e}")

    return {"status": "ok", "user_id": req.user_id, "capital": get_user_capital(req.user_id)}


@router.get("/capital")
async def get_capital(user_id: str = "default_user"):
    """Get current AI trading capital for a user."""
    return {"status": "ok", "user_id": user_id, "capital": get_user_capital(user_id)}


@router.get("/budget")
async def get_budget(user_id: str = "default_user"):
    """
    Get user's allocated AI trading budget, active utilized capital,
    remaining budget, and utilization percentage.
    """
    db = _db()
    summary = await get_user_budget_summary(db, user_id)
    return {"status": "ok", **summary}


@router.post("/set-budget")
async def set_budget(req: SetBudgetRequest):
    """
    Set the user's allocated AI trading budget in USDT (e.g. $500.00 USDT).
    AI will strictly NEVER spend more than this amount.
    """
    db = _db()
    summary = await set_user_budget(db, req.user_id, req.budget_usdt)
    return {"status": "ok", "message": f"AI budget set to ${req.budget_usdt:,.2f} USDT", **summary}


@router.post("/set-coins")
async def set_coins(req: SetCoinsRequest):
    """Set fixed coins for AI trading."""
    if not req.coins or len(req.coins) == 0:
        raise HTTPException(status_code=400, detail="At least one coin must be selected")
    saved = set_user_coins(req.user_id, req.coins)
    return {"status": "ok", "user_id": req.user_id, "coins": saved}


@router.get("/coins")
async def get_coins(user_id: str = "default_user"):
    """Get list of active coins tracked by AI for user."""
    return {"status": "ok", "user_id": user_id, "coins": get_user_coins(user_id), "available_coins": DEFAULT_COINS}


@router.post("/toggle")
async def toggle_ai(req: AiToggleRequest):
    """Enable or disable AI auto trading for a user."""
    set_ai_enabled(req.user_id, req.enabled)
    return {"status": "ok", "user_id": req.user_id, "ai_enabled": req.enabled}


@router.get("/status")
async def get_status(user_id: str = "default_user"):
    """
    Full AI trader status:
    - Live positions with P&L
    - Recent trades (memory cache + DB)
    - Budget allocation & utilization
    - Selected coins
    - AI enabled state
    """
    db = _db()
    try:
        capital = get_user_capital(user_id)
        budget_info = await get_user_budget_summary(db, user_id)
        
        # Ensure wallet exists and is funded with at least the user's allocated capital
        try:
            from services import wallet_service
            usdt_bal = await wallet_service.get_balance(db, user_id, "USDT")
            cash_available = float(usdt_bal.get("available", 0.0))
            cash_locked = float(usdt_bal.get("locked", 0.0))
        except Exception as e:
            print(f"[auto_trader] Wallet status error: {e}")
            cash_available = 0.0
            cash_locked = 0.0

        positions = await get_live_positions_with_pnl(db, user_id)
        trades = await get_auto_trader_trades(db, user_id)
        ai_enabled = get_ai_enabled(user_id)
        coins = get_user_coins(user_id)

        total_pos_val = sum(p.get("current_value", 0) for p in positions)
        total_unrealized = sum(p.get("unrealized_pnl", 0) for p in positions)

        try:
            all_pos = await db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
            total_realized = sum(float(p.get("realized_pnl", 0)) for p in all_pos if p.get("status") == "CLOSED" or float(p.get("quantity", 0)) == 0)
        except Exception:
            total_realized = 0.0

        return {
            "status": "ok",
            "user_id": user_id,
            "ai_enabled": ai_enabled,
            "capital": capital,
            "budget": budget_info,
            "coins": coins,
            "available_coins": DEFAULT_COINS,
            "cash_available": round(cash_available, 2),
            "cash_locked": round(cash_locked, 2),
            "position_value": round(total_pos_val, 2),
            "total_portfolio": round(cash_available + cash_locked + total_pos_val, 2),
            "total_unrealized_pnl": round(total_unrealized, 4),
            "total_realized_pnl": round(total_realized, 4),
            "positions": positions,
            "recent_trades": trades[:50],
            "trades": trades[:50],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/live-positions")
async def live_positions(user_id: str = "default_user"):
    """Get live positions with current prices and unrealized P&L."""
    db = _db()
    try:
        positions = await get_live_positions_with_pnl(db, user_id)
        return {"status": "ok", "positions": positions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trade-coin")
async def trade_coin(req: TradeCoinRequest):
    """
    Trigger AI analysis and trade on a specific coin.
    Full pipeline: AI -> Risk Engine -> Order -> Execute -> Ledger -> Balance
    """
    db = _db()
    symbol = req.symbol.upper()
    if not symbol.endswith("USDT"):
        symbol = symbol + "USDT"
    try:
        result = await run_ai_cycle(db, req.user_id, symbol, force_trade=req.side)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-cycle")
async def run_cycle(req: RunCycleRequest):
    """
    Run AI scan on multiple coins.
    Each coin goes through the full AI -> Risk -> Order -> Ledger pipeline.
    """
    db = _db()
    symbols = req.symbols or get_user_coins(req.user_id)
    try:
        results = await scan_coins(db, req.user_id, symbols)
        actions = {r.get("action", "UNKNOWN") for r in results}
        return {
            "status": "ok",
            "user_id": req.user_id,
            "coins_scanned": len(symbols),
            "results": results,
            "summary": {
                "buys": sum(1 for r in results if r.get("action") == "BUY"),
                "sells": sum(1 for r in results if r.get("action") == "SELL"),
                "holds": sum(1 for r in results if r.get("action") == "HOLD"),
                "rejected": sum(1 for r in results if "REJECTED" in r.get("action", "")),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades")
async def get_trades(user_id: str = "default_user"):
    """Get recent AI trade history (in-memory cache + persistent DB)."""
    db = _db()
    trades = await get_auto_trader_trades(db, user_id)
    return {"status": "ok", "trades": trades, "count": len(trades)}


class ResetRequest(BaseModel):
    user_id: str = "default_user"
    initial_usdt: float = 0.0


@router.post("/reset")
async def reset_trader(req: ResetRequest):
    """
    Completely wipe all trade history, open positions, ledger records, and balances to 0.
    Gives a 100% clean slate to start from trade #1 with 0 trades.
    """
    db = _db()
    res = await reset_all_user_trading_data(db, req.user_id, req.initial_usdt)
    return res

