"""
Subscription plans catalog + entitlements.
All amounts defined SERVER-SIDE only. Client sends only a plan_id.
"""
from typing import Any, Dict, List, Optional


PLANS: Dict[str, Dict[str, Any]] = {
    "free": {
        "id": "free",
        "name": "Free",
        "description": "Get started with core signals",
        "price_monthly": 0.0,
        "currency": "usd",
        "features": [
            "5 AI signals / day",
            "Claude OR Gemini per signal",
            "$10,000 paper trading account",
            "Watchlists & alerts",
            "Basic backtesting",
        ],
        "limits": {
            "signals_per_day": 5,
            "max_bots": 0,
            "testnet": False,
        },
    },
    "pro": {
        "id": "pro",
        "name": "Pro",
        "description": "For active traders who want AI at scale",
        "price_monthly": 19.0,
        "currency": "usd",
        "features": [
            "100 AI signals / day",
            "Both Claude & Gemini side-by-side",
            "3 AI trading bots",
            "Chat with AI Analyst (unlimited)",
            "Backtesting + saved strategy presets",
        ],
        "limits": {
            "signals_per_day": 100,
            "max_bots": 3,
            "testnet": False,
        },
    },
    "elite": {
        "id": "elite",
        "name": "Elite",
        "description": "For power users — unlimited AI + testnet execution",
        "price_monthly": 49.0,
        "currency": "usd",
        "features": [
            "Unlimited AI signals",
            "Unlimited AI trading bots",
            "Binance testnet execution",
            "Priority chat with AI Analyst",
            "All future features included",
        ],
        "limits": {
            "signals_per_day": -1,  # -1 = unlimited
            "max_bots": -1,
            "testnet": True,
        },
    },
}

# Only paid plans are checkout-able
PAID_PLAN_IDS = [pid for pid, p in PLANS.items() if p["price_monthly"] > 0]


def get_plan(plan_id: str) -> Optional[Dict[str, Any]]:
    return PLANS.get(plan_id)


def default_plan_id() -> str:
    return "free"


def public_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": plan["id"],
        "name": plan["name"],
        "description": plan["description"],
        "price_monthly": plan["price_monthly"],
        "currency": plan["currency"],
        "features": plan["features"],
        "limits": plan["limits"],
    }


def public_all() -> List[Dict[str, Any]]:
    order = ["free", "pro", "elite"]
    return [public_plan(PLANS[k]) for k in order if k in PLANS]
