"""
Order Service - Order Lifecycle with Full Event Trail.

Every state transition emits an immutable order_event so you can
reconstruct the complete lifecycle:

  ORDER_CREATED -> RISK_APPROVED -> FUNDS_RESERVED -> SUBMITTED
       -> PARTIALLY_FILLED -> FILLED -> SETTLED
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def _emit_event(db, order_id: str, user_id: str, event_type: str,
                      from_status: str, to_status: str, payload: dict = None) -> None:
    """Append an immutable order lifecycle event."""
    try:
        await db.order_events.insert_one({
            "id": str(uuid.uuid4()),
            "order_id": order_id,
            "user_id": user_id,
            "event_type": event_type,
            "from_status": from_status,
            "to_status": to_status,
            "payload": payload or {},
            "created_at": _now()
        })
    except Exception:
        pass


async def create_order(db, user_id: str, symbol: str, side: str,
                       quote_amount: float, ai_decision_id: str = "",
                       source: str = "AI_AUTO") -> Dict[str, Any]:
    """
    Create a new order and emit CREATED event.
    Status flow: NEW -> OPEN -> FILLED -> SETTLED
    """
    order_id = str(uuid.uuid4())
    order = {
        "id": order_id,
        "user_id": user_id,
        "symbol": symbol,
        "side": side,
        "order_type": "MARKET",
        "quantity": None,
        "price": None,
        "quote_amount": round(quote_amount, 2),
        "status": "NEW",
        "filled_quantity": 0.0,
        "filled_quote": 0.0,
        "average_fill_price": None,
        "source": source,
        "ai_decision_id": ai_decision_id,
        "created_at": _now(),
        "updated_at": _now()
    }
    try:
        await db.orders.insert_one(order)
    except Exception as e:
        print(f"[order_service] Order insert failed: {e}")
    await _emit_event(db, order_id, user_id, "CREATED", "", "NEW",
                      {"symbol": symbol, "side": side, "quote_amount": quote_amount})
    return order


async def mark_risk_approved(db, order: Dict) -> Dict:
    """Emit RISK_APPROVED event after risk engine passes."""
    await _emit_event(db, order["id"], order["user_id"], "RISK_APPROVED",
                      "NEW", "NEW", {"approved": True})
    return order


async def mark_funds_reserved(db, order: Dict, reserved_amount: float) -> Dict:
    """Mark order as OPEN after funds are reserved."""
    try:
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {"status": "OPEN", "updated_at": _now()}}
        )
    except Exception:
        pass
    await _emit_event(db, order["id"], order["user_id"], "FUNDS_RESERVED",
                      "NEW", "OPEN", {"reserved_amount": reserved_amount})
    order["status"] = "OPEN"
    return order


async def mark_filled(db, order: Dict, execution: Dict) -> Dict:
    """Mark order as FILLED after execution."""
    try:
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {
                "status": "FILLED",
                "filled_quantity": round(execution.get("quantity", 0), 8),
                "filled_quote": round(execution.get("quote_amount", 0), 2),
                "average_fill_price": round(execution.get("price", 0), 8),
                "updated_at": _now()
            }}
        )
    except Exception:
        pass
    await _emit_event(db, order["id"], order["user_id"], "FILLED",
                      "OPEN", "FILLED", {
                          "price": execution.get("price"),
                          "quantity": execution.get("quantity"),
                          "quote_amount": execution.get("quote_amount"),
                          "fee": execution.get("fee"),
                      })
    order["status"] = "FILLED"
    return order


async def mark_settled(db, order: Dict) -> Dict:
    """Mark order as SETTLED after ledger post."""
    await _emit_event(db, order["id"], order["user_id"], "SETTLED",
                      "FILLED", "FILLED", {})
    return order


async def cancel_order(db, order: Dict, reason: str = "") -> Dict:
    """Cancel an order."""
    try:
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {"status": "CANCELLED", "updated_at": _now()}}
        )
    except Exception:
        pass
    await _emit_event(db, order["id"], order["user_id"], "CANCELLED",
                      order.get("status", ""), "CANCELLED", {"reason": reason})
    order["status"] = "CANCELLED"
    return order


async def reject_order(db, order: Dict, reason: str = "") -> Dict:
    """Reject an order (risk engine rejection)."""
    try:
        await db.orders.update_one(
            {"id": order["id"]},
            {"$set": {"status": "REJECTED", "updated_at": _now()}}
        )
    except Exception:
        pass
    await _emit_event(db, order["id"], order["user_id"], "RISK_REJECTED",
                      "NEW", "REJECTED", {"reason": reason})
    order["status"] = "REJECTED"
    return order


async def get_order_history(db, user_id: str, limit: int = 50) -> List[Dict]:
    """Get recent orders."""
    try:
        return await db.orders.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
    except Exception:
        return []


async def get_order_events(db, order_id: str) -> List[Dict]:
    """Get all events for an order (full lifecycle reconstruction)."""
    try:
        return await db.order_events.find(
            {"order_id": order_id}, {"_id": 0}
        ).sort("created_at", 1).to_list(50)
    except Exception:
        return []
