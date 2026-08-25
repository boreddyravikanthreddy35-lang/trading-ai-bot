"""
Payments + subscription plan service.
Uses emergentintegrations.payments.stripe.checkout (Flow B — shared Emergent sandbox).

Key design:
- Plan mapping is SERVER-SIDE (see services.plans). Client only sends plan_id + origin_url.
- `payment_transactions` row is inserted BEFORE checkout redirect (status=initiated, payment_status=pending).
- On successful payment, the user's `plan` field is upgraded; expiry set to 30 days out.
- All routes under /api prefix.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from emergentintegrations.payments.stripe.checkout import (
        StripeCheckout, CheckoutSessionRequest,
    )
except Exception:  # pragma: no cover - optional dependency for local runs
    class CheckoutSessionRequest:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class StripeCheckout:
        def __init__(self, *args, **kwargs):
            self.api_key = kwargs.get("api_key")
            self.webhook_url = kwargs.get("webhook_url")

        async def create_checkout_session(self, req):
            raise RuntimeError("Stripe integration unavailable")

        async def get_checkout_status(self, session_id):
            raise RuntimeError("Stripe integration unavailable")

        async def handle_webhook(self, payload, sig):
            raise RuntimeError("Stripe integration unavailable")

from services.auth import current_user, optional_user
from services.plans import PLANS, PAID_PLAN_IDS, public_all, public_plan, get_plan

router = APIRouter(prefix="/payments", tags=["payments"])

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_emergent")


def _db():
    from server import db as _database
    return _database


def _now():
    return datetime.now(tz=timezone.utc)


def _stripe(host_url: str) -> StripeCheckout:
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)


class CheckoutRequest(BaseModel):
    plan_id: str = Field(..., description="pro | elite")
    origin_url: str = Field(..., description="e.g. window.location.origin")


# ---- Public endpoints -----------------------------------------------------

@router.get("/plans")
async def list_plans():
    return {"plans": public_all()}


@router.get("/subscription")
async def my_subscription(user: Optional[Dict[str, Any]] = Depends(optional_user)):
    """Return Unlimited Elite plan for all users (No subscription restrictions)."""
    user_id = user["id"] if user else "demo-user"
    plan = get_plan("elite")
    
    # Count today's signals for display
    today_key = _now().strftime("%Y-%m-%d")
    try:
        signals_today = await _db().signal_runs.count_documents({
            "user_id": user_id,
            "created_at": {"$regex": f"^{today_key}"},
        })
        active_bots = await _db().bots.count_documents({"user_id": user_id, "active": True})
    except Exception:
        signals_today = 0
        active_bots = 0

    return {
        "plan": public_plan(plan),
        "plan_id": "elite",
        "expires_at": None,
        "status": "unlimited",
        "usage": {
            "signals_today": signals_today,
            "signals_limit": -1,
            "active_bots": active_bots,
            "max_bots": -1,
            "testnet": True,
        },
    }


@router.post("/checkout")
async def create_checkout(req: CheckoutRequest, request: Request, user: Dict[str, Any] = Depends(current_user)):
    if req.plan_id not in PAID_PLAN_IDS:
        raise HTTPException(status_code=400, detail=f"plan_id must be one of {PAID_PLAN_IDS}")
    plan = PLANS[req.plan_id]

    origin = req.origin_url.rstrip("/")
    success_url = f"{origin}/billing/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/billing/cancel"

    host_url = str(request.base_url).rstrip("/")
    stripe_checkout = _stripe(host_url)

    # SERVER-SIDE price. Amount as float. currency lowercase.
    checkout_req = CheckoutSessionRequest(
        amount=float(plan["price_monthly"]),
        currency=plan["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": str(user["id"]),
            "user_email": str(user.get("email", "")),
            "plan_id": plan["id"],
            "plan_name": plan["name"],
        },
    )

    try:
        session = await stripe_checkout.create_checkout_session(checkout_req)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}")

    # Persist BEFORE the redirect
    now = _now().isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "plan_id": plan["id"],
        "amount": float(plan["price_monthly"]),
        "currency": plan["currency"],
        "status": "initiated",
        "payment_status": "pending",
        "metadata": {"user_id": str(user["id"]), "plan_id": plan["id"]},
        "created_at": now,
        "updated_at": now,
    }
    await _db().payment_transactions.insert_one(dict(doc))

    return {
        "checkout_url": session.url,
        "session_id": session.session_id,
        "plan_id": plan["id"],
        "amount": plan["price_monthly"],
    }


async def _apply_paid_upgrade(user_id: str, plan_id: str, session_id: str):
    """Idempotently upgrade the user's subscription based on a paid session."""
    tx = await _db().payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        return
    if tx.get("applied_to_subscription"):
        return
    expires = _now() + timedelta(days=30)
    await _db().subscriptions.update_one(
        {"user_id": user_id},
        {"$set": {
            "user_id": user_id,
            "plan_id": plan_id,
            "activated_at": _now().isoformat(),
            "expires_at": expires.isoformat(),
            "latest_session_id": session_id,
            "updated_at": _now().isoformat(),
        }},
        upsert=True,
    )
    await _db().payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"applied_to_subscription": True, "applied_at": _now().isoformat()}},
    )
    await _db().notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "kind": "billing",
        "title": f"Welcome to {plan_id.title()}!",
        "body": f"Your {plan_id.title()} plan is active. Renews {expires.strftime('%b %d, %Y')}.",
        "payload": {"plan_id": plan_id, "session_id": session_id},
        "read": False,
        "created_at": _now().isoformat(),
    })


@router.get("/status/{session_id}")
async def get_status(session_id: str, request: Request):
    """Polling endpoint. Unauthenticated per playbook rules — only returns limited fields."""
    tx = await _db().payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # If not paid yet, ask Stripe directly (webhook fallback)
    if tx.get("payment_status") != "paid":
        try:
            host_url = str(request.base_url).rstrip("/")
            stripe_checkout = _stripe(host_url)
            status = await stripe_checkout.get_checkout_status(session_id)
            if status.payment_status == "paid" or status.status == "complete":
                await _db().payment_transactions.update_one(
                    {"session_id": session_id, "payment_status": {"$ne": "paid"}},
                    {"$set": {
                        "status": "completed",
                        "payment_status": "paid",
                        "amount_total": (status.amount_total or 0) / 100.0 if status.amount_total else tx["amount"],
                        "updated_at": _now().isoformat(),
                    }},
                )
                tx = await _db().payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
                # Apply upgrade using metadata (idempotent)
                await _apply_paid_upgrade(user_id=tx["user_id"], plan_id=tx["plan_id"], session_id=session_id)
        except Exception:
            pass  # transient, fall through to DB state

    return {
        "session_id": tx["session_id"],
        "status": tx["status"],
        "payment_status": tx["payment_status"],
        "plan_id": tx.get("plan_id"),
    }


@router.get("/history")
async def payment_history(user: Dict[str, Any] = Depends(current_user), limit: int = 30):
    cur = _db().payment_transactions.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return {"transactions": await cur.to_list(limit)}


# ---- Webhook (Flow B path: /api/webhook/stripe) ---------------------------

webhook_router = APIRouter(tags=["payments"])  # NOT prefixed with /payments


@webhook_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    host_url = str(request.base_url).rstrip("/")
    stripe_checkout = _stripe(host_url)
    try:
        response = await stripe_checkout.handle_webhook(payload, sig)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {e}")

    session_id = response.session_id
    payment_status = response.payment_status
    metadata = response.metadata or {}

    if not session_id:
        return {"status": "ignored"}

    tx = await _db().payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        return {"status": "unknown_session"}

    # Idempotent update
    if tx.get("payment_status") != "paid":
        await _db().payment_transactions.update_one(
            {"session_id": session_id, "payment_status": {"$ne": "paid"}},
            {"$set": {
                "payment_status": payment_status,
                "status": "completed" if payment_status == "paid" else tx.get("status", "initiated"),
                "webhook_event": response.event_type,
                "updated_at": _now().isoformat(),
            }},
        )

    if payment_status == "paid":
        user_id = metadata.get("user_id") or tx.get("user_id")
        plan_id = metadata.get("plan_id") or tx.get("plan_id")
        if user_id and plan_id:
            await _apply_paid_upgrade(user_id=user_id, plan_id=plan_id, session_id=session_id)

    return {"status": "ok"}
