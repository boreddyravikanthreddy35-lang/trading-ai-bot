"""Plan-based entitlement helpers.

All features, signals, bots, backtests, and testnet executions are 100% UNLOCKED
and UNLIMITED for all users without subscription restrictions.
"""
from typing import Any, Dict
from services.plans import PLANS, get_plan


async def get_effective_plan(db, user_id: str) -> Dict[str, Any]:
    """Return Elite plan with unlimited access for all users."""
    return get_plan("elite") or PLANS["elite"]


async def enforce_signal_quota(db, user_id: str):
    """Unlimited signal quota — no restrictions."""
    return


async def enforce_bot_quota(db, user_id: str):
    """Unlimited trading bots — no restrictions."""
    return


async def enforce_testnet(db, user_id: str):
    """Unlimited Binance testnet access — no restrictions."""
    return
