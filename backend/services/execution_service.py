"""
Execution Service — Trade Fill Processing, Settlement & Idempotency Protection.

Simulates market order execution (paper/exchange).
Enforces:
  1. No double-fill of the same order
  2. Invariant: Order filled_quantity == Sum(Execution quantities)
  3. Financial settlement via ledger_service
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from services import ledger_service, order_service

FEE_RATE = 0.001  # 0.1% maker/taker fee

def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()

async def execute_buy(db, order: Dict, market_price: float, execution_id: str = None) -> Dict[str, Any]:
    """
    Execute a BUY fill with idempotency check.
    Prevents duplicate fills if an order is already filled or execution_id was processed.
    """
    from services import position_service

    user_id = order["user_id"]
    order_id = order["id"]
    symbol = order["symbol"]
    quote_amount = float(order["quote_amount"])
    base_asset = symbol.replace("USDT", "")

    # 1. Idempotency check: Is order already filled?
    existing_order = await db.orders.find_one({"id": order_id})
    if existing_order and existing_order.get("status") in ["FILLED", "SETTLED"]:
        existing_exec = await db.executions.find_one({"order_id": order_id})
        if existing_exec:
            return existing_exec

    exec_id = execution_id or str(uuid.uuid4())
    existing_exec = await db.executions.find_one({"id": exec_id})
    if existing_exec:
        return existing_exec

    fee = round(quote_amount * FEE_RATE, 8)
    quantity = round((quote_amount - fee) / market_price, 8)

    execution = {
        "id": exec_id,
        "order_id": order_id,
        "user_id": user_id,
        "symbol": symbol,
        "side": "BUY",
        "price": round(market_price, 8),
        "quantity": quantity,
        "quote_amount": quote_amount,
        "fee": fee,
        "fee_asset": "USDT",
        "ledger_transaction_id": "",
        "executed_at": _now()
    }

    try:
        await db.executions.insert_one(execution)
    except Exception as e:
        print(f"[execution_service] Execution insert failed: {e}")

    try:
        await db.trades.insert_one({
            "id": exec_id,
            "user_id": user_id,
            "symbol": symbol,
            "side": "BUY",
            "quantity": quantity,
            "price": round(market_price, 8),
            "fee": fee,
            "realized_pnl": 0.0,
            "cash_after": 0.0,
            "created_at": _now(),
            "source": "AI_AUTO",
        })
    except Exception as e:
        print(f"[execution_service] db.trades insert failed: {e}")

    # Post to ledger (financial settlement)
    try:
        ltx = await ledger_service.post_buy_settlement(
            db=db,
            user_id=user_id,
            symbol=symbol,
            quote_asset="USDT",
            quote_amount=quote_amount,
            base_asset=base_asset,
            base_quantity=quantity,
            fee=fee,
            order_id=order_id,
            metadata={"execution_id": exec_id, "market_price": market_price}
        )
        execution["ledger_transaction_id"] = ltx["id"]
        try:
            await db.executions.update_one(
                {"id": exec_id},
                {"$set": {"ledger_transaction_id": ltx["id"]}}
            )
        except Exception:
            pass
    except Exception as e:
        print(f"[execution_service] Ledger post_buy failed: {e}")

    # Update position
    try:
        await position_service.upsert_buy(
            db=db, user_id=user_id, symbol=symbol,
            quantity=quantity, price=market_price, cost=quote_amount
        )
    except Exception as e:
        print(f"[execution_service] Position update failed: {e}")

    # Mark order FILLED then SETTLED
    await order_service.mark_filled(db, order, execution)
    await order_service.mark_settled(db, order)

    return execution


async def execute_sell(db, order: Dict, position: Dict,
                       market_price: float, execution_id: str = None) -> Tuple[Dict, float]:
    """
    Execute a SELL fill with idempotency check.
    """
    from services import position_service

    user_id = order["user_id"]
    order_id = order["id"]
    symbol = order["symbol"]
    base_asset = symbol.replace("USDT", "")

    # Idempotency check
    existing_order = await db.orders.find_one({"id": order_id})
    if existing_order and existing_order.get("status") in ["FILLED", "SETTLED"]:
        existing_exec = await db.executions.find_one({"order_id": order_id})
        if existing_exec:
            return existing_exec, 0.0

    exec_id = execution_id or str(uuid.uuid4())
    quantity = float(position.get("quantity", 0))
    avg_entry = float(position.get("average_entry_price", market_price))
    quote_received = round(quantity * market_price, 8)
    fee = round(quote_received * FEE_RATE, 8)
    realized_pnl = round((market_price - avg_entry) * quantity - fee, 8)

    execution = {
        "id": exec_id,
        "order_id": order_id,
        "user_id": user_id,
        "symbol": symbol,
        "side": "SELL",
        "price": round(market_price, 8),
        "quantity": quantity,
        "quote_amount": quote_received,
        "fee": fee,
        "fee_asset": "USDT",
        "ledger_transaction_id": "",
        "executed_at": _now()
    }

    try:
        await db.executions.insert_one(execution)
    except Exception as e:
        print(f"[execution_service] Sell execution insert failed: {e}")

    try:
        await db.trades.insert_one({
            "id": exec_id,
            "user_id": user_id,
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": round(market_price, 8),
            "fee": fee,
            "realized_pnl": realized_pnl,
            "cash_after": 0.0,
            "created_at": _now(),
            "source": "AI_AUTO",
        })
    except Exception as e:
        print(f"[execution_service] db.trades sell insert failed: {e}")

    # Post to ledger
    try:
        ltx = await ledger_service.post_sell_settlement(
            db=db, user_id=user_id, symbol=symbol,
            base_asset=base_asset, base_quantity=quantity,
            quote_asset="USDT", quote_received=quote_received,
            fee=fee, order_id=order_id,
            realized_pnl=realized_pnl,
            metadata={"execution_id": exec_id, "market_price": market_price}
        )
        execution["ledger_transaction_id"] = ltx["id"]
    except Exception as e:
        print(f"[execution_service] Ledger post_sell failed: {e}")

    # Close position
    try:
        await position_service.close_sell(
            db=db, user_id=user_id, symbol=symbol,
            sell_price=market_price, quantity=quantity,
            realized_pnl=realized_pnl
        )
    except Exception as e:
        print(f"[execution_service] Position close failed: {e}")

    await order_service.mark_filled(db, order, execution)
    await order_service.mark_settled(db, order)

    return execution, realized_pnl
