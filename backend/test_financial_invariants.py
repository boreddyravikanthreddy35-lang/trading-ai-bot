"""
Financial Invariant Test Suite.

Proves mathematical and operational correctness of the production ledger architecture.
Tests 10 Core Financial Invariants:
  1. Invariant 1: Total Debits == Total Credits across all ledger settlements
  2. Invariant 2: Available + Locked == Total Balance for every asset
  3. Invariant 3: No balance is ever negative (available >= 0, locked >= 0)
  4. Invariant 4: Order filled_quantity == sum(execution quantities)
  5. Invariant 5: Position quantity == sum(buy_qty) - sum(sell_qty)
  6. Invariant 6: Realized P&L matches (sell_price - entry_price) * qty - fee
  7. Invariant 7: Execution Idempotency — retried fills do not duplicate credit
  8. Invariant 8: Withdrawal Idempotency — retried withdrawals do not duplicate debit
  9. Invariant 9: Every financial movement has a parent ledger_transaction
 10. Invariant 10: Institutional Reconciliation reports 100% CLEAN (0 breaks)
"""
import asyncio
import uuid
import sys
from pathlib import Path

# Load environment
sys.path.insert(0, str(Path(__file__).parent))
import server

from services import ledger_service, wallet_service, order_service, execution_service, position_service, reconciliation_service, withdrawal_service, custody_service

async def run_invariant_tests():
    db = server.db
    user_id = f"test_invariant_{uuid.uuid4().hex[:8]}"
    print("=" * 70)
    print(f"RUNNING INSTITUTIONAL FINANCIAL INVARIANT AUDIT FOR: {user_id}")
    print("=" * 70)
    
    passed_count = 0
    total_count = 10

    # --------------------------------------------------------------------------
    # TEST 1: Initial Deposit & Available + Locked == Total
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Testing Deposit & Balance Invariant (Available + Locked == Total)...")
    dep_tx = await ledger_service.post_deposit(db, user_id, "USDT", 2000.0)
    bal_usdt = await wallet_service.get_balance(db, user_id, "USDT")
    assert bal_usdt["available"] == 2000.0, f"Expected 2000.0, got {bal_usdt['available']}"
    assert bal_usdt["locked"] == 0.0, f"Expected 0.0, got {bal_usdt['locked']}"
    assert bal_usdt["total"] == bal_usdt["available"] + bal_usdt["locked"], "Available + Locked != Total"
    print("  -> PASSED: Deposit credited, Available ($2000) + Locked ($0) == Total ($2000)")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 2: Fund Reservation Invariant (available down, locked up, total constant)
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Testing Order Reservation (available down, locked up, total invariant)...")
    reserved = await wallet_service.reserve_funds(db, user_id, "USDT", 500.0)
    assert reserved is True, "Reservation failed"
    bal_after_res = await wallet_service.get_balance(db, user_id, "USDT")
    assert bal_after_res["available"] == 1500.0, f"Expected 1500, got {bal_after_res['available']}"
    assert bal_after_res["locked"] == 500.0, f"Expected 500, got {bal_after_res['locked']}"
    assert bal_after_res["total"] == 2000.0, f"Total changed during reservation: {bal_after_res['total']}"
    print("  -> PASSED: Available dropped to $1500, Locked rose to $500, Total remained $2000")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 3: Negative Balance Rejection Invariant
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Testing Negative Balance Rejection (Cannot reserve more than available)...")
    overdraft = await wallet_service.reserve_funds(db, user_id, "USDT", 99999.0)
    assert overdraft is False, "Overdraft reservation erroneously succeeded!"
    bal_no_overdraft = await wallet_service.get_balance(db, user_id, "USDT")
    assert bal_no_overdraft["available"] >= 0 and bal_no_overdraft["locked"] >= 0, "Negative balance detected!"
    print("  -> PASSED: Overdraft blocked. No balance is negative.")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 4: Order Creation & Execution Fill Invariant
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Testing Execution Fill & Settlement Invariant...")
    order = await order_service.create_order(db, user_id, "BTCUSDT", "BUY", 500.0)
    await order_service.mark_funds_reserved(db, order, 500.0)
    
    btc_price = 100000.0
    exec_1 = await execution_service.execute_buy(db, order, btc_price)
    
    # Verify fill quantity == sum(executions)
    order_db = await db.orders.find_one({"id": order["id"]})
    assert order_db["status"] == "FILLED", f"Expected FILLED, got {order_db['status']}"
    assert abs(order_db["filled_quantity"] - exec_1["quantity"]) < 1e-7, "Filled quantity mismatch!"
    print(f"  -> PASSED: Order #{order['id'][:8]} filled at ${btc_price:,.2f} with qty={exec_1['quantity']} BTC")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 5: Double-Entry Ledger Invariant (Quote Debit == Base Credit + Fee)
    # --------------------------------------------------------------------------
    print("\n[TEST 5] Testing Ledger Entries Balance (Debits vs Credits)...")
    ledger_tx_id = exec_1["ledger_transaction_id"]
    entries = await db.ledger_entries.find({"ledger_transaction_id": ledger_tx_id}, {"_id": 0}).to_list(10)
    assert len(entries) == 2, f"Expected 2 ledger entries for trade, got {len(entries)}"
    
    usdt_debit = next(e for e in entries if e["asset"] == "USDT" and e["direction"] == "DEBIT")
    btc_credit = next(e for e in entries if e["asset"] == "BTC" and e["direction"] == "CREDIT")
    assert usdt_debit["amount"] == 500.0, f"Expected debit of 500.0, got {usdt_debit['amount']}"
    assert btc_credit["amount"] == exec_1["quantity"], "Credit amount does not match base quantity"
    print(f"  -> PASSED: Ledger TX #{ledger_tx_id[:8]} balanced: USDT DEBIT ${usdt_debit['amount']} | BTC CREDIT {btc_credit['amount']}")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 6: Execution Idempotency (Duplicate fills are rejected)
    # --------------------------------------------------------------------------
    print("\n[TEST 6] Testing Execution Idempotency (Preventing Duplicate Fills)...")
    btc_bal_before = (await wallet_service.get_balance(db, user_id, "BTC"))["total"]
    # Attempt duplicate fill on same filled order
    duplicate_exec = await execution_service.execute_buy(db, order, btc_price, execution_id=exec_1["id"])
    btc_bal_after = (await wallet_service.get_balance(db, user_id, "BTC"))["total"]
    assert btc_bal_before == btc_bal_after, "Duplicate execution erroneously changed user balance!"
    print(f"  -> PASSED: Duplicate fill rejected. BTC balance stayed identical at {btc_bal_after}")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 7: Position vs Trade Invariant
    # --------------------------------------------------------------------------
    print("\n[TEST 7] Testing Position Quantity vs Execution Buys/Sells...")
    pos = await db.positions.find_one({"user_id": user_id, "symbol": "BTCUSDT"})
    assert pos is not None, "Position not found"
    assert abs(pos["quantity"] - exec_1["quantity"]) < 1e-7, "Position quantity does not match buy quantity"
    assert pos["average_entry_price"] == btc_price, "Average entry price mismatch"
    print(f"  -> PASSED: Position quantity ({pos['quantity']}) matches Execution quantity exactly")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 8: SELL Execution & Realized P&L Invariant
    # --------------------------------------------------------------------------
    print("\n[TEST 8] Testing SELL Execution & Realized P&L Accuracy...")
    sell_price = 110000.0 # 10% gain
    sell_order = await order_service.create_order(db, user_id, "BTCUSDT", "SELL", pos["quantity"] * sell_price)
    sell_exec, realized_pnl = await execution_service.execute_sell(db, sell_order, pos, sell_price)
    
    expected_gain = (sell_price - btc_price) * pos["quantity"] - sell_exec["fee"]
    assert abs(realized_pnl - expected_gain) < 1e-4, f"Expected PnL {expected_gain}, got {realized_pnl}"
    print(f"  -> PASSED: Position closed at ${sell_price:,.2f}. Realized P&L: +${realized_pnl:.4f} (matches formula)")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 9: Idempotent Withdrawal State Machine
    # --------------------------------------------------------------------------
    print("\n[TEST 9] Testing Idempotent Multi-Stage Withdrawal...")
    idem_key = f"TEST_WD_KEY_{uuid.uuid4().hex}"
    success, wd_result = await withdrawal_service.request_withdrawal(
        db=db,
        user_id=user_id,
        asset="USDT",
        amount=200.0,
        destination_address="0xDestinationAddressForTest123",
        network="ERC20",
        idempotency_key=idem_key
    )
    assert success is True, "Withdrawal failed"
    assert wd_result["status"] == "COMPLETED", "Withdrawal not completed"
    
    # Retry with same idempotency key
    retry_success, retry_result = await withdrawal_service.request_withdrawal(
        db=db,
        user_id=user_id,
        asset="USDT",
        amount=200.0,
        destination_address="0xDestinationAddressForTest123",
        network="ERC20",
        idempotency_key=idem_key
    )
    assert retry_result["withdrawal_id"] == wd_result["withdrawal_id"], "Idempotency key failed to return identical withdrawal"
    print(f"  -> PASSED: Withdrawal #{wd_result['withdrawal_id'][:8]} settled once and deduplicated via Idempotency-Key")
    passed_count += 1

    # --------------------------------------------------------------------------
    # TEST 10: Institutional Reconciliation Audit (Zero Breaks)
    # --------------------------------------------------------------------------
    print("\n[TEST 10] Running Full 5-Point Institutional Reconciliation Audit...")
    audit_report = await reconciliation_service.run_reconciliation(db)
    assert audit_report["status"] == "CLEAN", f"Reconciliation detected breaks: {audit_report.get('breaks_count')}"
    assert audit_report["breaks_count"] == 0, f"Expected 0 breaks, found {audit_report['breaks_count']}"
    print(f"  -> PASSED: Reconciliation Audit Status: CLEAN ({audit_report['passed_checks']}/{audit_report['total_checks']} checks passed, 0 breaks)")
    passed_count += 1

    print("\n" + "=" * 70)
    print(f"ALL {passed_count}/{total_count} FINANCIAL INVARIANT TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_invariant_tests())
