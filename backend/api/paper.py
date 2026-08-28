"""Paper trading endpoints — portfolio, orders, holdings, trade history."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services import market_data as md
from services.auth import optional_user
from services.entitlements import enforce_testnet

router = APIRouter(prefix="/paper", tags=["paper"])

STARTING_CASH = 1_000_000.0  # $1,000,000 USD (10 Lakh Dollars)
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


class AddFundsRequest(BaseModel):
    amount: float = Field(1_000_000.0, description="Amount of demo cash to add (defaults to $1,000,000 USD)")


async def _ensure_portfolio(user_id: str) -> Dict[str, Any]:
    doc = await _db().portfolios.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        # Auto-fix old portfolios that were accidentally created with 0 cash
        if float(doc.get("cash", 0)) == 0.0:
            import asyncio
            trades_count = 0
            try:
                cursor = _db().trades.find({"user_id": user_id})
                docs = await cursor.to_list(1)
                trades_count = len(docs)
            except Exception:
                pass
            if trades_count == 0:
                # No trades yet — safe to auto-reset cash to starting amount
                doc["cash"] = STARTING_CASH
                await _db().portfolios.update_one(
                    {"user_id": user_id},
                    {"$set": {"cash": STARTING_CASH}},
                )
        return doc
    # Brand new user — start with full demo cash
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
async def portfolio(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    p = await _ensure_portfolio(user_id)
    positions = await _db().positions.find({"user_id": user_id}, {"_id": 0}).to_list(200)

    holdings: List[Dict[str, Any]] = []
    total_position_value = 0.0
    unrealized = 0.0
    for pos in positions:
        qty = float(pos.get("quantity", 0))
        if qty <= 0.000001:
            continue
        avg_p = float(pos.get("avg_price") or pos.get("average_entry_price") or pos.get("avg_buy_price") or pos.get("price") or 0.0)
        try:
            price = await _current_price(pos.get("symbol", "BTCUSDT"))
        except Exception:
            price = avg_p
        if price <= 0:
            price = avg_p

        value = round(qty * price, 4)
        pnl = round((price - avg_p) * qty, 4) if avg_p else 0.0
        pnl_pct = round(((price / avg_p - 1) * 100), 2) if avg_p > 0 else 0.0
        total_position_value += value
        unrealized += pnl
        holdings.append({
            "symbol": pos.get("symbol", "BTCUSDT"),
            "quantity": qty,
            "avg_price": avg_p,
            "average_entry_price": avg_p,
            "current_price": price,
            "market_value": value,
            "unrealized_pnl": pnl,
            "unrealized_pnl_pct": pnl_pct,
        })

    cash_val = float(p.get("cash", 0.0))
    equity = round(cash_val + total_position_value, 2)
    return {
        "user_id": user_id,
        "cash": cash_val,
        "holdings": holdings,
        "equity": equity,
        "total_pnl": round(equity - STARTING_CASH, 2),
        "total_pnl_pct": round((equity / STARTING_CASH - 1) * 100, 2) if STARTING_CASH > 0 else 0.0,
        "starting_cash": STARTING_CASH,
        "unrealized_pnl": round(unrealized, 2),
    }


@router.post("/order")
async def place_order(req: PlaceOrderRequest, user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    if req.side.upper() not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="side must be BUY or SELL")
    side = req.side.upper()
    if not req.quantity and not req.quote_amount:
        raise HTTPException(status_code=400, detail="Provide quantity or quote_amount")

    # ─── Testnet route (best-effort; falls back to paper on failure) ──────
    if req.use_testnet:
        if not user:
            raise HTTPException(status_code=401, detail="Sign in required for testnet execution")
        # Elite-plan gate
        await enforce_testnet(_db(), user_id)
        from services.binance_client import BinanceTestnetClient, BinanceError, GeoRestrictedError
        creds = await _db().exchange_settings.find_one(
            {"user_id": user_id, "exchange": "binance_testnet"}, {"_id": 0}
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
                "user_id": user_id,
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
    p = await _ensure_portfolio(user_id)
    price = await _current_price(req.symbol)

    # Compute qty
    if req.quantity:
        qty = float(req.quantity)
    else:
        qty = float(req.quote_amount) / price

    cost = qty * price
    fee = cost * FEE_RATE

    pos = await _db().positions.find_one({"user_id": user_id, "symbol": req.symbol}, {"_id": 0})

    if side == "BUY":
        needed = cost + fee
        if needed > p["cash"] + 1e-9:
            raise HTTPException(status_code=400, detail=f"Insufficient cash. Need ${needed:,.2f}, have ${p['cash']:,.2f}")
        new_cash = p["cash"] - needed
        if pos:
            old_qty = float(pos.get("quantity") or 0.0)
            old_avg = float(pos.get("avg_price") or pos.get("average_entry_price") or pos.get("avg_buy_price") or price)
            new_qty = old_qty + qty
            new_avg = ((old_avg * old_qty) + (price * qty)) / new_qty if new_qty > 0 else price
            await _db().positions.update_one(
                {"user_id": user_id, "symbol": req.symbol},
                {"$set": {"quantity": new_qty, "avg_price": new_avg, "average_entry_price": new_avg}},
            )
        else:
            await _db().positions.insert_one({
                "user_id": user_id,
                "symbol": req.symbol,
                "quantity": qty,
                "avg_price": price,
                "average_entry_price": price,
            })
        realized = 0.0
    else:  # SELL
        if not pos or float(pos.get("quantity", 0)) <= 0:
            raise HTTPException(status_code=400, detail=f"No open position for {req.symbol} to sell")

        available_qty = float(pos.get("quantity", 0))

        # If requested qty is slightly higher than available qty due to rounding (e.g. within 2% or 0.001 delta),
        # or if user entered rounded quantity from UI, automatically clamp to available holding quantity!
        if qty > available_qty:
            if (qty - available_qty) / available_qty < 0.02 or (qty - available_qty) < 0.001:
                qty = available_qty
                cost = qty * price
                fee = cost * FEE_RATE
            else:
                base_coin = req.symbol.replace("USDT", "")
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient position size. You hold {available_qty:.6f} {base_coin}, but tried to sell {qty:.6f}"
                )

        proceeds = cost - fee
        avg_entry = float(pos.get("avg_price") or pos.get("average_entry_price") or price)
        realized = (price - avg_entry) * qty
        new_cash = p["cash"] + proceeds
        remaining = max(0.0, available_qty - qty)
        if remaining < 1e-6:
            await _db().positions.delete_one({"user_id": user_id, "symbol": req.symbol})
        else:
            await _db().positions.update_one(
                {"user_id": user_id, "symbol": req.symbol},
                {"$set": {"quantity": remaining}},
            )

    await _db().portfolios.update_one(
        {"user_id": user_id},
        {"$set": {"cash": new_cash}},
    )

    trade = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
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
async def trade_history(user: Optional[Dict[str, Any]] = Depends(optional_user), limit: int = 100):
    user_id = user["id"] if user else "demo-user"
    cursor = _db().trades.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    return {"trades": docs}


@router.post("/reset")
async def reset_portfolio(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    await _db().portfolios.update_one(
        {"user_id": user_id},
        {"$set": {"cash": STARTING_CASH}},
        upsert=True,
    )
    await _db().positions.delete_many({"user_id": user_id})
    await _db().trades.delete_many({"user_id": user_id})
    return {"status": "ok", "cash": STARTING_CASH}


@router.post("/add-funds")
async def add_funds(req: Optional[AddFundsRequest] = None, user: Optional[Dict[str, Any]] = Depends(optional_user)):
    user_id = user["id"] if user else "demo-user"
    add_amount = (req.amount if req else 1_000_000.0) or 1_000_000.0
    p = await _ensure_portfolio(user_id)
    new_cash = p["cash"] + add_amount
    await _db().portfolios.update_one(
        {"user_id": user_id},
        {"$set": {"cash": new_cash}},
        upsert=True,
    )
    return {"status": "ok", "cash": new_cash, "added": add_amount}


