"""
Razorpay & INR Payment API - /api/payment/*
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

import server
from services import payment_gateway

router = APIRouter(prefix="/payment", tags=["payment-gateway"])


class CreateRazorpayOrderRequest(BaseModel):
    user_id: str = "default_user"
    amount_inr: float = Field(..., gt=0, description="Amount in INR (e.g. 500, 1000, 5000)")
    receipt_prefix: Optional[str] = "dep"
    notes: Optional[Dict[str, Any]] = None


class VerifyRazorpayPaymentRequest(BaseModel):
    user_id: str = "default_user"
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    amount_inr: float


class PayoutRequest(BaseModel):
    user_id: str = "default_user"
    amount_inr: float = Field(..., gt=0, description="Amount in INR to withdraw")
    payout_mode: str = Field("UPI", description="UPI or BANK")
    payout_address: str = Field(..., description="e.g. user@upi or IFSC:Account")
    account_holder_name: Optional[str] = ""


@router.get("/config")
async def get_payment_config():
    """Returns public payment gateway key and exchange rate."""
    return {
        "gateway": "RAZORPAY",
        "key_id": payment_gateway.RAZORPAY_KEY_ID,
        "currency": "INR",
        "inr_per_usdt": payment_gateway.INR_PER_USDT,
        "supported_methods": ["UPI", "GPay", "PhonePe", "Paytm", "Cards", "NetBanking"],
    }


@router.post("/razorpay/create-order")
async def create_order(req: CreateRazorpayOrderRequest):
    """
    Create a Razorpay INR Order.
    Returns order_id, amount in paise, key_id, and currency for Frontend Checkout SDK.
    """
    db = server.db
    try:
        order_res = await payment_gateway.create_razorpay_order(
            db=db,
            user_id=req.user_id,
            amount_inr=req.amount_inr,
            receipt_prefix=req.receipt_prefix or "dep",
            notes=req.notes
        )
        return {"status": "ok", **order_res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay order: {str(e)}")


@router.post("/razorpay/verify-payment")
async def verify_payment(req: VerifyRazorpayPaymentRequest):
    """
    Verify payment signature and credit wallet through Double-Entry Ledger.
    """
    db = server.db
    try:
        result = await payment_gateway.process_successful_payment(
            db=db,
            user_id=req.user_id,
            order_id=req.razorpay_order_id,
            payment_id=req.razorpay_payment_id,
            signature=req.razorpay_signature,
            amount_inr=req.amount_inr
        )
        return {"status": "ok", **result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment processing error: {str(e)}")


@router.post("/payout/request")
async def request_payout(req: PayoutRequest):
    """
    Request an INR withdrawal/payout to Bank Account or UPI.
    Debits USDT wallet via Double-Entry Ledger.
    """
    db = server.db
    try:
        result = await payment_gateway.request_payout_withdrawal(
            db=db,
            user_id=req.user_id,
            amount_inr=req.amount_inr,
            payout_mode=req.payout_mode,
            payout_address=req.payout_address,
            account_holder_name=req.account_holder_name or ""
        )
        return {"status": "ok", **result}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payout error: {str(e)}")


@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request):
    """
    Razorpay Webhook receiver for background async payment confirmations.
    """
    db = server.db
    try:
        body = await request.json()
        event = body.get("event")
        payload = body.get("payload", {})
        payment_entity = payload.get("payment", {}).get("entity", {})

        if event in ("payment.captured", "order.paid"):
            order_id = payment_entity.get("order_id")
            payment_id = payment_entity.get("id")
            amount_paise = payment_entity.get("amount", 0)
            amount_inr = amount_paise / 100.0
            notes = payment_entity.get("notes", {})
            user_id = notes.get("user_id", "default_user")

            if order_id and payment_id:
                # Check if already processed
                existing = await db.payment_transactions.find_one({"gateway_order_id": order_id})
                if existing and existing.get("status") == "SUCCESS":
                    return {"status": "already_processed"}

                await payment_gateway.process_successful_payment(
                    db=db,
                    user_id=user_id,
                    order_id=order_id,
                    payment_id=payment_id,
                    signature="simulated_webhook_verified",
                    amount_inr=amount_inr
                )

        return {"status": "ok", "event": event}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
