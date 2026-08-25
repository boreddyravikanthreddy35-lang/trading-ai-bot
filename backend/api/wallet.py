"""
Wallet API - /api/wallet/*

Endpoints:
  GET  /api/wallet/balances       - All asset balances
  GET  /api/wallet/summary        - Portfolio summary with prices
  POST /api/wallet/deposit        - Simulated deposit
  POST /api/wallet/withdraw       - Simulated withdrawal
  GET  /api/wallet/transactions   - Ledger transaction history
  POST /api/wallet/initialize     - Initialize wallet with starting USDT
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import server

from services import wallet_service, ledger_service
from services.market_data import ticker_24hr

router = APIRouter(prefix="/wallet", tags=["wallet"])


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


# -- Schemas ------------------------------------------------------------------

class DepositRequest(BaseModel):
    user_id: str = "default_user"
    asset: str = "USDT"
    amount: float

class WithdrawRequest(BaseModel):
    user_id: str = "default_user"
    asset: str = "USDT"
    amount: float

class InitializeRequest(BaseModel):
    user_id: str = "default_user"
    amount: float = 1000.0


# -- Endpoints ----------------------------------------------------------------

@router.get("/balances")
async def get_balances(user_id: str = "default_user"):
    """Get all asset balances (available + locked) for a user."""
    db = server.db
    try:
        balances = await wallet_service.get_balances(db, user_id)
        return {"status": "ok", "user_id": user_id, "balances": balances}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_portfolio_summary(user_id: str = "default_user"):
    """
    Portfolio summary: total value in USDT, per-asset with live prices.
    Auto-initializes with paper trading capital if empty.
    """
    db = server.db
    try:
        balances = await wallet_service.get_balances(db, user_id)

        balances = await wallet_service.get_balances(db, user_id)

        # Get live prices for all held assets
        price_map = {}
        total_value = 0.0
        assets_detail = []

        for b in balances:
            asset = b["asset"]
            total_qty = b["total"]
            if total_qty == 0:
                continue
            if asset == "USDT":
                price = 1.0
                value_usdt = total_qty
            else:
                try:
                    ticker_res, src = await ticker_24hr([f"{asset}USDT"])
                    if ticker_res and len(ticker_res) > 0:
                        price = float(ticker_res[0].get("lastPrice", 0))
                    else:
                        price = 0.0
                except Exception:
                    price = 0.0
                value_usdt = round(total_qty * price, 2)
            price_map[asset] = price
            total_value += value_usdt
            assets_detail.append({
                **b,
                "price_usdt": price,
                "value_usdt": round(value_usdt, 2),
            })

        # Get positions for unrealized and realized P&L
        try:
            positions = await db.positions.find(
                {"user_id": user_id, "status": "OPEN"}, {"_id": 0}
            ).to_list(50)
            total_unrealized = sum(float(p.get("unrealized_pnl", 0)) for p in positions)
            closed_pos = await db.positions.find({"user_id": user_id, "status": "CLOSED"}, {"_id": 0}).to_list(100)
            total_realized = sum(float(p.get("realized_pnl", 0)) for p in closed_pos)
        except Exception:
            total_unrealized = 0.0
            total_realized = 0.0

        return {
            "status": "ok",
            "user_id": user_id,
            "total_value_usdt": round(total_value, 2),
            "total_unrealized_pnl": round(total_unrealized, 4),
            "total_realized_pnl": round(total_realized, 4),
            "assets": assets_detail,
            "updated_at": _now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deposit")
async def deposit(req: DepositRequest):
    """
    Simulated deposit: credit user wallet with specified amount.
    Flow: create deposit record -> post to ledger -> credit balance
    """
    db = server.db
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    try:
        deposit_id = str(uuid.uuid4())
        # Ensure wallet exists
        wallet = await wallet_service.get_or_create_wallet(db, req.user_id)

        # Create deposit record
        deposit_rec = {
            "id": deposit_id,
            "user_id": req.user_id,
            "wallet_id": wallet["id"],
            "asset": req.asset,
            "amount": round(req.amount, 8),
            "fee": 0.0,
            "net_amount": round(req.amount, 8),
            "status": "PENDING",
            "simulated": True,
            "tx_hash": f"SIM_{deposit_id[:8].upper()}",
            "ledger_transaction_id": "",
            "created_at": _now(),
            "confirmed_at": None
        }
        try:
            await db.deposits.insert_one(deposit_rec)
        except Exception:
            pass

        # Post to ledger -> credits balance
        ltx = await ledger_service.post_deposit(
            db, req.user_id, req.asset, req.amount,
            deposit_id=deposit_id,
            metadata={"simulated": True, "wallet_id": wallet["id"]}
        )

        # Mark deposit confirmed
        try:
            await db.deposits.update_one(
                {"id": deposit_id},
                {"$set": {
                    "status": "CREDITED",
                    "ledger_transaction_id": ltx["id"],
                    "confirmed_at": _now()
                }}
            )
        except Exception:
            pass

        # Return updated balance
        bal = await wallet_service.get_balance(db, req.user_id, req.asset)
        return {
            "status": "ok",
            "message": f"Deposited {req.amount} {req.asset} successfully",
            "deposit_id": deposit_id,
            "ledger_tx_id": ltx["id"],
            "new_balance": bal
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/withdraw")
async def withdraw(req: WithdrawRequest):
    """
    Simulated withdrawal: debit user wallet.
    """
    db = server.db
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # Check balance
    bal = await wallet_service.get_balance(db, req.user_id, req.asset)
    withdrawal_fee = round(req.amount * 0.001, 8)  # 0.1% withdrawal fee
    total_needed = req.amount + withdrawal_fee

    if bal["available"] < total_needed:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient {req.asset}. Available: {bal['available']:.4f}, Needed: {total_needed:.4f} (incl fee)"
        )

    try:
        wallet = await wallet_service.get_or_create_wallet(db, req.user_id)
        withdrawal_id = str(uuid.uuid4())

        # Create withdrawal record
        wd_rec = {
            "id": withdrawal_id,
            "user_id": req.user_id,
            "wallet_id": wallet["id"],
            "asset": req.asset,
            "amount": round(req.amount, 8),
            "fee": withdrawal_fee,
            "net_amount": round(req.amount - withdrawal_fee, 8),
            "status": "PENDING",
            "tx_hash": f"SIM_{withdrawal_id[:8].upper()}",
            "ledger_transaction_id": "",
            "created_at": _now(),
            "completed_at": None
        }
        try:
            await db.withdrawals.insert_one(wd_rec)
        except Exception:
            pass

        # Post to ledger -> debits balance
        ltx = await ledger_service.post_withdrawal(
            db, req.user_id, req.asset, req.amount, withdrawal_fee,
            withdrawal_id=withdrawal_id
        )

        # Mark completed
        try:
            await db.withdrawals.update_one(
                {"id": withdrawal_id},
                {"$set": {
                    "status": "COMPLETED",
                    "ledger_transaction_id": ltx["id"],
                    "completed_at": _now()
                }}
            )
        except Exception:
            pass

        new_bal = await wallet_service.get_balance(db, req.user_id, req.asset)
        return {
            "status": "ok",
            "message": f"Withdrew {req.amount} {req.asset} (fee: {withdrawal_fee})",
            "withdrawal_id": withdrawal_id,
            "ledger_tx_id": ltx["id"],
            "new_balance": new_bal
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
async def get_transactions(user_id: str = "default_user", limit: int = 50):
    """
    Get ledger transaction history for a user.
    Returns human-readable financial events (BUY, SELL, DEPOSIT, WITHDRAWAL).
    """
    db = server.db
    try:
        txns = await ledger_service.get_ledger_history(db, user_id, limit)
        return {"status": "ok", "user_id": user_id, "transactions": txns, "count": len(txns)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize")
async def initialize_wallet(req: InitializeRequest):
    """Initialize a new wallet with starting USDT for paper trading."""
    db = server.db
    try:
        result = await wallet_service.initialize_wallet_with_usdt(db, req.user_id, req.amount)
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deposit-history")
async def deposit_history(user_id: str = "default_user", limit: int = 50):
    """Get complete deposit history from deposits table and double-entry ledger."""
    db = server.db
    try:
        deps = await db.deposits.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)

        ltxs = await db.ledger_transactions.find(
            {"user_id": user_id, "type": "DEPOSIT"}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)

        seen_ids = set()
        combined = []
        for d in deps:
            did = d.get("id") or d.get("ledger_transaction_id")
            if did and did not in seen_ids:
                seen_ids.add(did)
                combined.append(d)

        for tx in ltxs:
            ref_id = tx.get("reference_id") or tx.get("id")
            if ref_id not in seen_ids:
                seen_ids.add(ref_id)
                meta = tx.get("metadata") or {}
                combined.append({
                    "id": tx.get("id"),
                    "user_id": tx.get("user_id"),
                    "asset": meta.get("asset", "USDT"),
                    "amount": float(meta.get("amount", 0)),
                    "fee": float(meta.get("fee", 0)),
                    "net_amount": float(meta.get("amount", 0)),
                    "status": "CREDITED",
                    "simulated": meta.get("simulated", True),
                    "tx_hash": f"TX_{tx.get('id')[:8].upper()}",
                    "ledger_transaction_id": tx.get("id"),
                    "created_at": tx.get("created_at"),
                    "confirmed_at": tx.get("created_at"),
                })

        combined.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return {"status": "ok", "user_id": user_id, "deposits": combined[:limit], "count": len(combined)}
    except Exception as e:
        return {"status": "ok", "user_id": user_id, "deposits": [], "count": 0}


@router.get("/withdrawal-history")
async def withdrawal_history(user_id: str = "default_user", limit: int = 50):
    """Get complete withdrawal history from withdrawals table and double-entry ledger."""
    db = server.db
    try:
        wds = await db.withdrawals.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)

        ltxs = await db.ledger_transactions.find(
            {"user_id": user_id, "type": "WITHDRAWAL"}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)

        seen_ids = set()
        combined = []
        for w in wds:
            wid = w.get("id") or w.get("ledger_transaction_id")
            if wid and wid not in seen_ids:
                seen_ids.add(wid)
                combined.append(w)

        for tx in ltxs:
            ref_id = tx.get("reference_id") or tx.get("id")
            if ref_id not in seen_ids:
                seen_ids.add(ref_id)
                meta = tx.get("metadata") or {}
                amt = float(meta.get("amount", 0))
                fee = float(meta.get("fee", 0))
                combined.append({
                    "id": tx.get("id"),
                    "user_id": tx.get("user_id"),
                    "asset": meta.get("asset", "USDT"),
                    "amount": amt,
                    "fee": fee,
                    "net_amount": amt - fee,
                    "status": "COMPLETED",
                    "tx_hash": f"TX_{tx.get('id')[:8].upper()}",
                    "ledger_transaction_id": tx.get("id"),
                    "created_at": tx.get("created_at"),
                    "completed_at": tx.get("created_at"),
                })

        combined.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        return {"status": "ok", "user_id": user_id, "withdrawals": combined[:limit], "count": len(combined)}
    except Exception as e:
        return {"status": "ok", "user_id": user_id, "withdrawals": [], "count": 0}
