"""Custody & Deposit Addresses API — /api/custody/*"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import server
from services import custody_service

router = APIRouter(prefix="/custody", tags=["custody"])

class DepositAddressRequest(BaseModel):
    user_id: str
    asset: str = "USDT"
    network: str = "TRC20"

class SimulateBlockchainDepositRequest(BaseModel):
    user_id: str
    asset: str = "USDT"
    network: str = "TRC20"
    amount: float
    tx_hash: Optional[str] = None
    from_address: Optional[str] = None

@router.get("/deposit-address")
async def get_deposit_address(user_id: str = "default_user", asset: str = "USDT", network: str = "TRC20"):
    """Get or generate user's custodial blockchain deposit address."""
    db = server.db
    try:
        addr = await custody_service.get_or_create_deposit_address(db, user_id, asset, network)
        return {"status": "ok", "address_info": addr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deposit/simulate-blockchain")
async def simulate_blockchain_deposit(req: SimulateBlockchainDepositRequest):
    """
    Simulate incoming blockchain deposit with full network confirmation & ledger credit.
    Enforces idempotency on tx_hash.
    """
    db = server.db
    import uuid
    tx_hash = req.tx_hash or f"0xsim_{uuid.uuid4().hex}"
    from_addr = req.from_address or f"0xExternalSender_{req.user_id[:6]}"
    
    # Get user deposit address
    addr_info = await custody_service.get_or_create_deposit_address(db, req.user_id, req.asset, req.network)
    to_addr = addr_info["address"]

    try:
        res = await custody_service.process_blockchain_deposit(
            db=db,
            tx_hash=tx_hash,
            user_id=req.user_id,
            asset=req.asset,
            network=req.network,
            amount=req.amount,
            from_addr=from_addr,
            to_addr=to_addr,
            simulated=True
        )
        return {"status": "ok", "result": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/overview")
async def get_custody_overview():
    """Get institutional multi-vault reserve holdings (Hot/Cold/Exchange)."""
    db = server.db
    try:
        overview = await custody_service.get_custody_overview(db)
        return {"status": "ok", **overview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
