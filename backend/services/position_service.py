"""
Position Service - P&L Tracking.

Maintains running position state per user per symbol.
Calculates unrealized P&L, realized P&L, average entry price.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def upsert_buy(db, user_id: str, symbol: str, quantity: float,
                     price: float, cost: float) -> Dict[str, Any]:
    """
    Open or add to a position after a BUY execution.
    Uses weighted average for entry price.
    """
    existing = await db.positions.find_one({"user_id": user_id, "symbol": symbol})

    if existing and existing.get("status") == "OPEN" and float(existing.get("quantity", 0)) > 0:
        # Weighted average entry price
        old_qty = float(existing["quantity"])
        old_avg = float(existing["average_entry_price"])
        old_invested = float(existing.get("total_invested", old_qty * old_avg))
        new_qty = old_qty + quantity
        new_invested = old_invested + cost
        new_avg = new_invested / new_qty if new_qty > 0 else price

        try:
            await db.positions.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {
                    "quantity": round(new_qty, 8),
                    "average_entry_price": round(new_avg, 8),
                    "total_invested": round(new_invested, 2),
                    "current_price": round(price, 8),
                    "status": "OPEN",
                    "updated_at": _now()
                }}
            )
        except Exception as e:
            print(f"[position_service] upsert_buy update failed: {e}")
        return {**existing, "quantity": new_qty, "average_entry_price": new_avg}
    else:
        # New position or previously closed - reopen
        prev_realized = float(existing.get("realized_pnl", 0)) if existing else 0.0
        pos = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "symbol": symbol,
            "quantity": round(quantity, 8),
            "average_entry_price": round(price, 8),
            "current_price": round(price, 8),
            "unrealized_pnl": 0.0,
            "realized_pnl": prev_realized,
            "total_invested": round(cost, 2),
            "status": "OPEN",
            "opened_at": _now(),
            "closed_at": None,
            "updated_at": _now()
        }
        if existing:
            try:
                await db.positions.update_one(
                    {"user_id": user_id, "symbol": symbol},
                    {"$set": pos}
                )
            except Exception as e:
                print(f"[position_service] upsert_buy update failed: {e}")
        else:
            try:
                await db.positions.insert_one(pos)
            except Exception as e:
                print(f"[position_service] upsert_buy insert failed: {e}")
        return pos


async def close_sell(db, user_id: str, symbol: str, sell_price: float,
                     quantity: float, realized_pnl: float) -> Dict[str, Any]:
    """Update or close position after a SELL execution."""
    existing = await db.positions.find_one({"user_id": user_id, "symbol": symbol})
    if not existing:
        return {}

    old_qty = float(existing.get("quantity", 0))
    remaining_qty = max(0.0, round(old_qty - quantity, 8))
    cum_realized = float(existing.get("realized_pnl", 0)) + realized_pnl
    old_invested = float(existing.get("total_invested", 0))
    sold_fraction = quantity / old_qty if old_qty > 0 else 1.0
    remaining_invested = old_invested * (1 - sold_fraction)

    if remaining_qty <= 0.000001:
        # Fully closed
        try:
            await db.positions.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {
                    "quantity": 0.0,
                    "unrealized_pnl": 0.0,
                    "realized_pnl": round(cum_realized, 4),
                    "total_invested": 0.0,
                    "current_price": round(sell_price, 8),
                    "status": "CLOSED",
                    "closed_at": _now(),
                    "updated_at": _now()
                }}
            )
        except Exception as e:
            print(f"[position_service] close_sell failed: {e}")
    else:
        # Partially closed
        try:
            await db.positions.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {
                    "quantity": remaining_qty,
                    "realized_pnl": round(cum_realized, 4),
                    "total_invested": round(remaining_invested, 2),
                    "current_price": round(sell_price, 8),
                    "updated_at": _now()
                }}
            )
        except Exception as e:
            print(f"[position_service] partial close failed: {e}")
    return existing


async def update_prices(db, user_id: str, price_map: Dict[str, float]) -> None:
    """Update current prices and unrealized P&L for all open positions."""
    try:
        positions = await db.positions.find(
            {"user_id": user_id, "status": "OPEN"}, {"_id": 0}
        ).to_list(50)
        for pos in positions:
            symbol = pos["symbol"]
            base = symbol.replace("USDT", "")
            current_price = price_map.get(base) or price_map.get(symbol, 0)
            if current_price <= 0:
                continue
            qty = float(pos.get("quantity", 0))
            avg_entry = float(pos.get("average_entry_price", current_price))
            unrealized = round((current_price - avg_entry) * qty, 4)
            try:
                await db.positions.update_one(
                    {"user_id": user_id, "symbol": symbol},
                    {"$set": {
                        "current_price": current_price,
                        "unrealized_pnl": unrealized,
                        "updated_at": _now()
                    }}
                )
            except Exception:
                pass
    except Exception as e:
        print(f"[position_service] update_prices failed: {e}")


async def get_open_positions(db, user_id: str) -> List[Dict]:
    """Get all open positions for user strictly grouped by symbol (1 row per coin)."""
    try:
        uid = user_id or "default_user"
        rows = await db.positions.find({"user_id": uid}, {"_id": 0}).to_list(100)
        if not rows and uid != "default_user":
            rows = await db.positions.find({"user_id": "default_user"}, {"_id": 0}).to_list(100)

        by_symbol: Dict[str, Dict] = {}
        for r in rows:
            sym = r.get("symbol")
            if not sym:
                continue
            qty = float(r.get("quantity", 0))
            if qty > 0.000001 and r.get("status") != "CLOSED":
                avg_p = float(r.get("average_entry_price") or r.get("avg_price") or r.get("price") or 0)
                cost = float(r.get("total_invested") or (qty * avg_p))

                if sym in by_symbol:
                    existing = by_symbol[sym]
                    total_qty = existing["quantity"] + qty
                    total_cost = existing["total_invested"] + cost
                    new_avg = (total_cost / total_qty) if total_qty > 0 else avg_p
                    existing["quantity"] = total_qty
                    existing["average_entry_price"] = new_avg
                    existing["avg_buy_price"] = new_avg
                    existing["total_invested"] = total_cost
                else:
                    by_symbol[sym] = {
                        **r,
                        "symbol": sym,
                        "quantity": qty,
                        "average_entry_price": avg_p,
                        "avg_buy_price": avg_p,
                        "total_invested": cost,
                        "status": "OPEN",
                    }
        return list(by_symbol.values())
    except Exception as e:
        print(f"[position_service] get_open_positions error: {e}")
        return []


async def get_all_positions(db, user_id: str) -> List[Dict]:
    """Get all positions (open + closed)."""
    try:
        return await db.positions.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("updated_at", -1).to_list(100)
    except Exception:
        return []
