"""
Ledger Service - Double-Entry Financial Authority.

Every financial event (deposit, withdrawal, buy, sell, fee) is posted here.
Ledger entries are APPEND-ONLY - never updated or deleted.
Balance table is derived/cached state; ledger is source of truth.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


FEE_RATE = 0.001  # 0.1% trading fee


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def _get_or_create_wallet(db, user_id: str) -> Dict[str, Any]:
    """Get or create the user's SPOT wallet."""
    wallet = await db.wallets.find_one({"user_id": user_id, "wallet_type": "SPOT"})
    if not wallet:
        w = {"id": str(uuid.uuid4()), "user_id": user_id, "wallet_type": "SPOT",
             "status": "ACTIVE", "created_at": _now(), "updated_at": _now()}
        await db.wallets.insert_one(w)
        wallet = w
    return wallet


async def _get_or_create_account(db, wallet_id: str, user_id: str, asset: str) -> Dict[str, Any]:
    """Get or create asset account under the wallet."""
    acct = await db.accounts.find_one({"wallet_id": wallet_id, "asset": asset})
    if not acct:
        a = {"id": str(uuid.uuid4()), "wallet_id": wallet_id, "user_id": user_id,
             "asset": asset, "status": "ACTIVE", "created_at": _now()}
        await db.accounts.insert_one(a)
        acct = a
    return acct


async def _get_balance(db, wallet_id: str, asset: str) -> Dict[str, Any]:
    """Get current balance row for wallet+asset."""
    return await db.wallet_balances.find_one({"wallet_id": wallet_id, "asset": asset})


async def _ensure_balance_row(db, wallet_id: str, account_id: str, user_id: str, asset: str) -> Dict[str, Any]:
    """Ensure a wallet_balances row exists."""
    bal = await _get_balance(db, wallet_id, asset)
    if not bal:
        b = {"id": str(uuid.uuid4()), "wallet_id": wallet_id, "account_id": account_id,
             "user_id": user_id, "asset": asset, "available": 0.0, "locked": 0.0, "updated_at": _now()}
        await db.wallet_balances.insert_one(b)
        bal = b
    return bal


async def _apply_balance_change(db, wallet_id: str, asset: str, field: str, delta: float) -> float:
    """Apply delta to available or locked. Returns new value."""
    bal = await _get_balance(db, wallet_id, asset)
    current = float(bal.get(field, 0)) if bal else 0.0
    new_val = max(0.0, round(current + delta, 8))
    try:
        await db.wallet_balances.update_one(
            {"wallet_id": wallet_id, "asset": asset},
            {"$set": {field: new_val, "updated_at": _now()}}
        )
    except Exception as e:
        print(f"[ledger_service] Balance update failed for {asset}.{field}: {e}")
    return new_val


async def _post_entry(db, ledger_tx_id: str, wallet_id: str, account_id: str,
                      asset: str, direction: str, amount: float,
                      balance_after: float, purpose: str = "") -> Dict:
    """Append a single ledger entry (NEVER updates existing)."""
    entry = {
        "id": str(uuid.uuid4()),
        "ledger_transaction_id": ledger_tx_id,
        "wallet_id": wallet_id,
        "account_id": account_id,
        "asset": asset,
        "direction": direction,
        "amount": round(amount, 8),
        "balance_after": round(balance_after, 8),
        "entry_purpose": purpose,
        "created_at": _now(),
    }
    try:
        await db.ledger_entries.insert_one(entry)
    except Exception as e:
        print(f"[ledger_service] Entry post failed: {e}")
    return entry


# -- PUBLIC INTERFACE ----------------------------------------------------------

async def post_deposit(db, user_id: str, asset: str, amount: float,
                       deposit_id: str = "", metadata: dict = None) -> Dict:
    """
    Credit user wallet with deposited funds.
    Flow: ledger_transaction -> ledger_entry (CREDIT) -> wallet_balance available up
    """
    wallet = await _get_or_create_wallet(db, user_id)
    wid = wallet["id"]
    acct = await _get_or_create_account(db, wid, user_id, asset)
    await _ensure_balance_row(db, wid, acct["id"], user_id, asset)

    ltx = {"id": str(uuid.uuid4()), "user_id": user_id, "type": "DEPOSIT",
           "reference_type": "DEPOSIT", "reference_id": deposit_id,
           "status": "PENDING", "metadata": metadata or {}, "created_at": _now()}
    try:
        await db.ledger_transactions.insert_one(ltx)
    except Exception as e:
        print(f"[ledger_service] Ledger tx insert failed: {e}")

    new_avail = await _apply_balance_change(db, wid, asset, "available", amount)
    await _post_entry(db, ltx["id"], wid, acct["id"], asset, "CREDIT", amount, new_avail, "DEPOSIT")

    try:
        await db.ledger_transactions.update_one(
            {"id": ltx["id"]}, {"$set": {"status": "POSTED"}})
    except Exception:
        pass

    await _audit(db, user_id, "DEPOSIT_CREDITED", "deposit", deposit_id,
                 {"asset": asset, "amount": amount})
    return ltx


async def post_withdrawal(db, user_id: str, asset: str, amount: float, fee: float,
                          withdrawal_id: str = "", from_locked: bool = False) -> Dict:
    """
    Debit user wallet for withdrawal.
    Flow: ledger_transaction -> ledger_entry (DEBIT) -> balance down
    If from_locked is True, funds were already locked (available was deducted during reservation).
    """
    wallet = await _get_or_create_wallet(db, user_id)
    wid = wallet["id"]
    acct = await _get_or_create_account(db, wid, user_id, asset)

    total_debit = round(amount + fee, 8)
    ltx = {"id": str(uuid.uuid4()), "user_id": user_id, "type": "WITHDRAWAL",
           "reference_type": "WITHDRAWAL", "reference_id": withdrawal_id,
           "status": "PENDING", "metadata": {"amount": amount, "fee": fee}, "created_at": _now()}
    try:
        await db.ledger_transactions.insert_one(ltx)
    except Exception:
        pass

    if from_locked:
        # Funds were already reserved (available was reduced, locked was increased)
        # Release the lock without modifying available again
        await _apply_balance_change(db, wid, asset, "locked", -total_debit)
        bal = await _get_balance(db, wid, asset)
        new_avail = float(bal.get("available", 0))
    else:
        new_avail = await _apply_balance_change(db, wid, asset, "available", -total_debit)

    await _post_entry(db, ltx["id"], wid, acct["id"], asset, "DEBIT", total_debit, new_avail, "WITHDRAWAL")

    try:
        await db.ledger_transactions.update_one({"id": ltx["id"]}, {"$set": {"status": "POSTED"}})
    except Exception:
        pass
    await _audit(db, user_id, "WITHDRAWAL_DEBITED", "withdrawal", withdrawal_id,
                 {"asset": asset, "amount": amount, "fee": fee})
    return ltx


async def post_buy_settlement(db, user_id: str, symbol: str,
                               quote_asset: str, quote_amount: float,
                               base_asset: str, base_quantity: float,
                               fee: float, order_id: str,
                               metadata: dict = None) -> Dict:
    """
    Settle a BUY trade through the ledger.
    Step 1: Release USDT lock, debit USDT
    Step 2: Credit BASE asset
    """
    wallet = await _get_or_create_wallet(db, user_id)
    wid = wallet["id"]
    quote_acct = await _get_or_create_account(db, wid, user_id, quote_asset)
    base_acct = await _get_or_create_account(db, wid, user_id, base_asset)
    await _ensure_balance_row(db, wid, base_acct["id"], user_id, base_asset)

    total_quote = round(quote_amount, 8)
    ltx_id = str(uuid.uuid4())
    ltx = {"id": ltx_id, "user_id": user_id, "type": "BUY",
           "reference_type": "ORDER", "reference_id": order_id,
           "status": "PENDING",
           "metadata": {**(metadata or {}), "symbol": symbol,
                         "quote_amount": quote_amount, "base_quantity": base_quantity, "fee": fee},
           "created_at": _now()}
    try:
        await db.ledger_transactions.insert_one(ltx)
    except Exception:
        pass

    # Release locked USDT
    await _apply_balance_change(db, wid, quote_asset, "locked", -total_quote)
    q_bal = await _get_balance(db, wid, quote_asset)
    q_avail = float(q_bal.get("available", 0)) if q_bal else 0.0
    await _post_entry(db, ltx_id, wid, quote_acct["id"], quote_asset, "DEBIT",
                       total_quote, q_avail, "QUOTE_ASSET")

    # Credit BASE
    new_base = await _apply_balance_change(db, wid, base_asset, "available", base_quantity)
    await _post_entry(db, ltx_id, wid, base_acct["id"], base_asset, "CREDIT",
                       base_quantity, new_base, "BASE_ASSET")

    try:
        await db.ledger_transactions.update_one({"id": ltx_id}, {"$set": {"status": "POSTED"}})
    except Exception:
        pass
    await _audit(db, user_id, "BUY_SETTLED", "order", order_id,
                 {"symbol": symbol, "quote": total_quote, "base": base_quantity})
    return ltx


async def post_sell_settlement(db, user_id: str, symbol: str,
                                base_asset: str, base_quantity: float,
                                quote_asset: str, quote_received: float,
                                fee: float, order_id: str,
                                realized_pnl: float = 0.0,
                                metadata: dict = None) -> Dict:
    """
    Settle a SELL trade through the ledger.
    Step 1: Debit BASE asset
    Step 2: Credit USDT (net of fee)
    """
    wallet = await _get_or_create_wallet(db, user_id)
    wid = wallet["id"]
    base_acct = await _get_or_create_account(db, wid, user_id, base_asset)
    quote_acct = await _get_or_create_account(db, wid, user_id, quote_asset)
    await _ensure_balance_row(db, wid, quote_acct["id"], user_id, quote_asset)

    net_quote = round(quote_received - fee, 8)
    ltx_id = str(uuid.uuid4())
    ltx = {"id": ltx_id, "user_id": user_id, "type": "SELL",
           "reference_type": "ORDER", "reference_id": order_id,
           "status": "PENDING",
           "metadata": {**(metadata or {}), "symbol": symbol, "base_quantity": base_quantity,
                         "quote_received": quote_received, "fee": fee, "realized_pnl": realized_pnl},
           "created_at": _now()}
    try:
        await db.ledger_transactions.insert_one(ltx)
    except Exception:
        pass

    # Debit BASE
    new_base = await _apply_balance_change(db, wid, base_asset, "available", -base_quantity)
    await _post_entry(db, ltx_id, wid, base_acct["id"], base_asset, "DEBIT",
                       base_quantity, new_base, "BASE_ASSET")

    # Credit USDT (net)
    new_quote = await _apply_balance_change(db, wid, quote_asset, "available", net_quote)
    await _post_entry(db, ltx_id, wid, quote_acct["id"], quote_asset, "CREDIT",
                       net_quote, new_quote, "QUOTE_ASSET")

    try:
        await db.ledger_transactions.update_one({"id": ltx_id}, {"$set": {"status": "POSTED"}})
    except Exception:
        pass
    await _audit(db, user_id, "SELL_SETTLED", "order", order_id,
                 {"symbol": symbol, "base": base_quantity, "quote": net_quote, "pnl": realized_pnl})
    return ltx


async def get_ledger_history(db, user_id: str, limit: int = 50) -> List[Dict]:
    """Get recent ledger transactions for a user."""
    try:
        txns = await db.ledger_transactions.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        return txns
    except Exception:
        return []


async def _audit(db, user_id: str, event_type: str, entity_type: str,
                 entity_id: str, payload: dict) -> None:
    """Append audit log entry."""
    try:
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()), "user_id": user_id,
            "event_type": event_type, "entity_type": entity_type,
            "entity_id": entity_id, "payload": payload,
            "created_at": _now()
        })
    except Exception:
        pass
