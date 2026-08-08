"""Paper trading endpoints — portfolio, orders, holdings, trade history."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services import market_data as md
from services.auth import current_user

router = APIRouter(prefix="/paper", tags=["paper"])

STARTING_CASH = 10_000.0
FEE_RATE = 0.001  # 0.1% simulated


def _db():
    from server import db as _database
    return _database


class PlaceOrderRequest(BaseModel):
    symbol: str = Field(..., description="e.g. BTCUSDT")
    side: str = Field(..., description="BUY | SELL")
    quantity: Optional[float] = None
    quote_amount: Optional[float] = None  # USD amount to spend
    use_testnet: bool = Field(False, description="If true and testnet is enabled, route via Binance testnet")


async def _ensure_portfolio(user_id: str) -> Dict[str, Any]:
    doc = await _db().portfolios.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        return doc
    doc = {
        "user_id": user_id,
        "cash": STARTING_CASH,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    await _db().portfolios.insert_one(dict(doc))
    return doc


async def _current_price(symbol: str) -> float:
    df, _src = await md.get_klines(symbol, "1m", 5)
    if df is None or df.empty:
        raise HTTPException(status_code=502, detail=f"Unable to price {symbol}")
    return float(df.iloc[-1]["close"])


@router.get("/portfolio")
async def portfolio(user: Dict[str, Any] = Depends(current_user)):
    p = await _ensure_portfolio(user["id"])
    positions = await _db().positions.find({"user_id": user["id"]}, {"_id": 0}).to_list(200)

    holdings: List[Dict[str, Any]] = []
    total_position_value = 0.0
    unrealized = 0.0
    for pos in positions:
        if pos["quantity"] <= 0:
            continue
        try:
            price = await _current_price(pos["symbol"])
        except Exception:
            price = pos.get("avg_price", 0.0)
        value = pos["quantity"] * price
        pnl = (price - pos["avg_price"]) * pos["quantity"]
        pnl_pct = (price / pos["avg_price"] - 1) * 100 if pos["avg_price"] else 0.0
        total_position_value += value
        unrealized += pnl
        holdings.append({
            "symbol": pos["symbol"],
            "quantity": pos["quantity"],
            "avg_price": pos["avg_price"],
            "current_price": price,
            "market_value": value,
            "unrealized_pnl": pnl,
            "unrealized_pnl_pct": pnl_pct,
        })

    equity = p["cash"] + total_position_value
    return {
        "user_id": user["id"],
        "cash": p["cash"],
        "holdings": holdings,
        "equity": equity,
        "total_pnl": equity - STARTING_CASH,
        "total_pnl_pct": (equity / STARTING_CASH - 1) * 100,
        "starting_cash": STARTING_CASH,
        "unrealized_pnl": unrealized,
    }


@router.post("/order")
async def place_order(req: PlaceOrderRequest, user: Dict[str, Any] = Depends(current_user)):
    if req.side.upper() not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")
    side = req.side.upper()
    if not req.quantity and not req.quote_amount:
        raise HTTPException(status_code=400, detail="Provide quantity or quote_amount")

    # ─── Testnet route (best-effort; falls back to paper on failure) ──────
    if req.use_testnet:
        from services.binance_client import BinanceTestnetClient, BinanceError, GeoRestrictedError
        creds = await _db().exchange_settings.find_one(
            {"user_id": user["id"], "exchange": "binance_testnet"}, {"_id": 0}
        )
        if not creds or not creds.get("enabled"):
            raise HTTPException(status_code=400, detail="Enable Binance testnet in Settings first")
        client = BinanceTestnetClient(creds["api_key"], creds["api_secret"])
        try:
            order = await client.market_order(
                req.symbol, side,
                quantity=req.quantity, quote_amount=req.quote_amount,
            )
            # Log this as a testnet trade too, so history shows it
            trade = {
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "symbol": req.symbol,
                "side": side,
                "quantity": float(order.get("executedQty", 0) or 0),
                "price": float((order.get("fills") or [{}])[0].get("price", 0) or 0),
                "fee": 0.0,
                "realized_pnl": 0.0,
                "cash_after": None,
                "created_at": datetime.now(tz=timezone.utc).isoformat(),
                "source": "binance_testnet",
                "testnet_order": order,
            }
            await _db().trades.insert_one(dict(trade))
            return trade
        except GeoRestrictedError as e:
            raise HTTPException(status_code=503, detail=f"Testnet unavailable from this region: {e}")
        except BinanceError as e:
            raise HTTPException(status_code=502, detail=f"Testnet error: {e}")

    # ─── Paper broker (default) ───────────────────────────────────────────
    p = await _ensure_portfolio(user["id"])
    price = await _current_price(req.symbol)

    # Compute qty
    if req.quantity:
        qty = float(req.quantity)
    else:
        qty = float(req.quote_amount) / price

    cost = qty * price
    fee = cost * FEE_RATE

    pos = await _db().positions.find_one({"user_id": user["id"], "symbol": req.symbol}, {"_id": 0})

    if side == "BUY":
        needed = cost + fee
        if needed > p["cash"] + 1e-9:
            raise HTTPException(status_code=400, detail=f"Insufficient cash. Need ${needed:,.2f}, have ${p['cash']:,.2f}")
        new_cash = p["cash"] - needed
        if pos:
            new_qty = pos["quantity"] + qty
            new_avg = ((pos["avg_price"] * pos["quantity"]) + (price * qty)) / new_qty
            await _db().positions.update_one(
                {"user_id": user["id"], "symbol": req.symbol},
                {"$set": {"quantity": new_qty, "avg_price": new_avg}},
            )
        else:
            await _db().positions.insert_one({
                "user_id": user["id"],
                "symbol": req.symbol,
                "quantity": qty,
                "avg_price": price,
            })
        realized = 0.0
    else:  # SELL
        if not pos or pos["quantity"] < qty - 1e-9:
            raise HTTPException(status_code=400, detail="Insufficient position size")
        proceeds = cost - fee
        realized = (price - pos["avg_price"]) * qty
        new_cash = p["cash"] + proceeds
        remaining = pos["quantity"] - qty
        if remaining < 1e-9:
            await _db().positions.delete_one({"user_id": user["id"], "symbol": req.symbol})
        else:
            await _db().positions.update_one(
                {"user_id": user["id"], "symbol": req.symbol},
                {"$set": {"quantity": remaining}},
            )

    await _db().portfolios.update_one(
        {"user_id": user["id"]},
        {"$set": {"cash": new_cash}},
    )

    trade = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "symbol": req.symbol,
        "side": side,
        "quantity": qty,
        "price": price,
        "fee": fee,
        "realized_pnl": realized,
        "cash_after": new_cash,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
        "source": "paper",
    }
    await _db().trades.insert_one(dict(trade))
    return trade


@router.get("/trades")
async def trade_history(user: Dict[str, Any] = Depends(current_user), limit: int = 100):
    cursor = _db().trades.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return {"trades": docs}


@router.post("/reset")
async def reset_portfolio(user: Dict[str, Any] = Depends(current_user)):
    await _db().portfolios.update_one(
        {"user_id": user["id"]},
        {"$set": {"cash": STARTING_CASH}},
        upsert=True,
    )
    await _db().positions.delete_many({"user_id": user["id"]})
    await _db().trades.delete_many({"user_id": user["id"]})
    return {"status": "ok", "cash": STARTING_CASH}
