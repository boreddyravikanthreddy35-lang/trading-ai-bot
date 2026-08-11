"""Plan-based entitlement helpers.
Call these from routes to enforce Free/Pro/Elite limits server-side.
"""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException

from services.plans import PLANS, get_plan


def _now():
    return datetime.now(tz=timezone.utc)


async def get_effective_plan(db, user_id: str) -> Dict[str, Any]:
    """Return the plan dict for the user (auto-downgrades if expired)."""
    sub = await db.subscriptions.find_one({"user_id": user_id}, {"_id": 0})
    plan_id = (sub or {}).get("plan_id") or "free"
    expires = (sub or {}).get("expires_at")
    if expires:
        try:
            if datetime.fromisoformat(expires) < _now():
                plan_id = "free"
        except Exception:
            plan_id = "free"
    return get_plan(plan_id) or PLANS["free"]


async def enforce_signal_quota(db, user_id: str):
    """Raise 402 if the user has already used their daily signal allowance."""
    plan = await get_effective_plan(db, user_id)
    limit = plan["limits"].get("signals_per_day", 5)
    if limit == -1:
        return  # unlimited
    today_key = _now().strftime("%Y-%m-%d")
    used = await db.signal_runs.count_documents({
        "user_id": user_id,
        "created_at": {"$regex": f"^{today_key}"},
    })
    if used >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Daily AI signal limit reached ({used}/{limit}). Upgrade your plan for more.",
        )


async def enforce_bot_quota(db, user_id: str):
    """Raise 402 if the user cannot create any more bots."""
    plan = await get_effective_plan(db, user_id)
    limit = plan["limits"].get("max_bots", 0)
    if limit == -1:
        return  # unlimited
    count = await db.bots.count_documents({"user_id": user_id})
    if count >= limit:
        raise HTTPException(
            status_code=402,
            detail=(f"Bot limit reached ({count}/{limit}). "
                    "Upgrade to Pro for 3 bots or Elite for unlimited."),
        )


async def enforce_testnet(db, user_id: str):
    plan = await get_effective_plan(db, user_id)
    if not plan["limits"].get("testnet"):
        raise HTTPException(
            status_code=402,
            detail="Binance testnet execution is an Elite plan feature. Upgrade to enable.",
        )
