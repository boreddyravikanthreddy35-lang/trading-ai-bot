"""
Orders API - /api/orders/*

Order lifecycle management endpoints.
"""
from fastapi import APIRouter, HTTPException
import server
from services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
async def get_orders(user_id: str = "default_user", limit: int = 50, status: str = None):
    """Get order history for a user."""
    db = server.db
    try:
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        orders = await db.orders.find(
            query, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        return {"status": "ok", "orders": orders, "count": len(orders)}
    except Exception as e:
        return {"status": "ok", "orders": [], "count": 0}


@router.get("/{order_id}/events")
async def get_order_events(order_id: str):
    """
    Get the full lifecycle event trail for a specific order.
    Returns all state transitions: CREATED -> RISK_APPROVED -> FUNDS_RESERVED
    -> FILLED -> SETTLED
    """
    db = server.db
    try:
        events = await order_service.get_order_events(db, order_id)
        order = await db.orders.find_one({"id": order_id}, {"_id": 0})
        return {
            "status": "ok",
            "order": order,
            "lifecycle": events,
            "event_count": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/open")
async def get_open_orders(user_id: str = "default_user"):
    """Get all open orders."""
    db = server.db
    try:
        orders = await db.orders.find(
            {"user_id": user_id, "status": "OPEN"}, {"_id": 0}
        ).to_list(50)
        return {"status": "ok", "orders": orders}
    except Exception:
        return {"status": "ok", "orders": []}
