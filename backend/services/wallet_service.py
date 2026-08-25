"""
Wallet Service - State Management.

Responsibilities:
  - get balance (available + locked per asset)
  - reserve funds (available down, locked up) before order
  - release reservation (available up, locked down) on cancel
  - expose wallet state to API layer

NOTE: Actual financial mutations (credit/debit) go through ledger_service.
This service manages only the reservation (lock/unlock) layer.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services import ledger_service


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def get_or_create_wallet(db, user_id: str) -> Dict[str, Any]:
    return await ledger_service._get_or_create_wallet(db, user_id)


async def get_balances(db, user_id: str) -> List[Dict[str, Any]]:
    """Return all asset balances for this user. available + locked per asset."""
    wallet = await get_or_create_wallet(db, user_id)
    try:
        rows = await db.wallet_balances.find(
            {"wallet_id": wallet["id"]}, {"_id": 0}
        ).to_list(100)
    except Exception:
        rows = []
    result = []
    for row in rows:
        avail = float(row.get("available", 0))
        locked = float(row.get("locked", 0))
        result.append({
            "asset": row["asset"],
            "available": avail,
            "locked": locked,
            "total": round(avail + locked, 8),
            "wallet_id": wallet["id"],
        })
    return result


async def get_balance(db, user_id: str, asset: str) -> Dict[str, Any]:
    """Get single asset balance."""
    wallet = await get_or_create_wallet(db, user_id)
    row = await db.wallet_balances.find_one({"wallet_id": wallet["id"], "asset": asset})
    if not row:
        return {"asset": asset, "available": 0.0, "locked": 0.0, "total": 0.0}
    avail = float(row.get("available", 0))
    locked = float(row.get("locked", 0))
    return {"asset": asset, "available": avail, "locked": locked, "total": round(avail + locked, 8)}


async def reserve_funds(db, user_id: str, asset: str, amount: float) -> bool:
    """
    Reserve (lock) funds before placing an order.
    available down, locked up.
    Returns True if successful, False if insufficient balance.
    """
    bal = await get_balance(db, user_id, asset)
    if bal["available"] < amount:
        return False
    wallet = await get_or_create_wallet(db, user_id)
    try:
        await db.wallet_balances.update_one(
            {"wallet_id": wallet["id"], "asset": asset},
            {"$set": {
                "available": round(bal["available"] - amount, 8),
                "locked": round(bal["locked"] + amount, 8),
                "updated_at": _now()
            }}
        )
    except Exception as e:
        print(f"[wallet_service] reserve_funds failed: {e}")
        return False
    return True


async def release_reservation(db, user_id: str, asset: str, amount: float) -> None:
    """
    Release a reservation (on order cancel).
    locked down, available up.
    """
    bal = await get_balance(db, user_id, asset)
    wallet = await get_or_create_wallet(db, user_id)
    release = min(amount, bal["locked"])
    try:
        await db.wallet_balances.update_one(
            {"wallet_id": wallet["id"], "asset": asset},
            {"$set": {
                "available": round(bal["available"] + release, 8),
                "locked": round(bal["locked"] - release, 8),
                "updated_at": _now()
            }}
        )
    except Exception as e:
        print(f"[wallet_service] release_reservation failed: {e}")


async def get_portfolio_summary(db, user_id: str, price_map: Dict[str, float] = None) -> Dict:
    """
    Portfolio value summary: total value in USDT.
    price_map: {asset: current_price_in_usdt}
    """
    balances = await get_balances(db, user_id)
    price_map = price_map or {}
    total_value = 0.0
    assets_detail = []
    for b in balances:
        asset = b["asset"]
        total_qty = b["total"]
        if total_qty == 0:
            continue
        if asset == "USDT":
            value_usdt = total_qty
        else:
            price = price_map.get(asset, 0.0)
            value_usdt = total_qty * price
        total_value += value_usdt
        assets_detail.append({
            **b,
            "price_usdt": price_map.get(asset, 0.0) if asset != "USDT" else 1.0,
            "value_usdt": round(value_usdt, 2),
        })
    return {
        "total_value_usdt": round(total_value, 2),
        "assets": assets_detail,
    }


async def initialize_wallet_with_usdt(db, user_id: str, amount: float) -> Dict:
    """One-time wallet initialization with USDT for paper trading."""
    bal = await get_balance(db, user_id, "USDT")
    if bal["total"] > 0:
        return {"status": "already_initialized", "balance": bal}
    result = await ledger_service.post_deposit(
        db, user_id, "USDT", amount,
        metadata={"note": "Initial paper trading balance"}
    )
    return {"status": "initialized", "amount": amount, "ledger_tx": result["id"]}
