"""Withdrawals API — /api/withdrawals/*"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional
import server
from services import withdrawal_service

router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])

class WithdrawalRequest(BaseModel):
    user_id: str
    asset: str = "USDT"
    amount: float
    destination_address: str
    network: str = "ERC20"
    idempotency_key: Optional[str] = None

@router.post("/request")
async def create_withdrawal(req: WithdrawalRequest, idempotency_key: Optional[str] = Header(None)):
    """
    Request a withdrawal through the 7-stage security, risk, and ledger state machine.
    Supports Idempotency-Key header to prevent duplicate execution.
    """
    db = server.db
    key = req.idempotency_key or idempotency_key or ""
    success, result = await withdrawal_service.request_withdrawal(
        db=db,
        user_id=req.user_id,
        asset=req.asset,
        amount=req.amount,
        destination_address=req.destination_address,
        network=req.network,
        idempotency_key=key
    )
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", "result": result}

@router.get("/{withdrawal_id}")
async def get_withdrawal(withdrawal_id: str):
    """Get withdrawal lifecycle stages and transaction hash."""
    db = server.db
    details = await withdrawal_service.get_withdrawal_details(db, withdrawal_id)
    if not details:
        raise HTTPException(status_code=404, detail="Withdrawal not found")
    return {"status": "ok", "withdrawal": details}
