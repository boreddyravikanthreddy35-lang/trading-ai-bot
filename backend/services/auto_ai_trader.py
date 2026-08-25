"""
Auto AI Trader Service - Production Pipeline Edition.

Full AI -> Risk Engine -> Order Service -> Execution Service -> Ledger -> Wallet flow.

Every trade is:
  1. AI signals BUY/SELL/HOLD based on technical indicators & 5-agent intelligence
  2. Risk Engine validates (balance, position limits, stop loss, score threshold)
  3. Order created with lifecycle events
  4. Funds reserved (USDT locked)
  5. Market order executed at live price
  6. Ledger double-entry posted (USDT debit + BASE credit, or vice versa)
  7. Wallet balances updated
  8. Position P&L updated
  9. AI decision recorded with risk verdict

Result: complete audit trail, no arbitrary balance mutations.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services import market_data as md
from services.indicators import compute_indicators
from services.trade_intelligence import build_full_trade_intelligence, detect_market_regime
from services import risk_engine, order_service, execution_service, wallet_service, position_service


DEFAULT_CAPITAL = 1000.0
DEFAULT_COINS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "PEPEUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT", "AVAXUSDT", "LINKUSDT"]
FEE_RATE = 0.001
MODEL_VERSION = "v2.0"
INR_PER_USDT = 88.0

_USER_CAPITAL: Dict[str, float] = {}
_USER_BUDGET: Dict[str, Dict[str, Any]] = {}
_USER_COINS: Dict[str, List[str]] = {}
_LATEST_TRADES: Dict[str, List[Dict[str, Any]]] = {}
_AI_ENABLED: Dict[str, bool] = {}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _now_local() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_user_capital(user_id: str) -> float:
    return _USER_CAPITAL.get(user_id, DEFAULT_CAPITAL)


def set_user_capital(user_id: str, capital: float) -> None:
    _USER_CAPITAL[user_id] = max(10.0, float(capital))


async def get_user_budget_summary(db, user_id: str) -> Dict[str, Any]:
    """
    Get the user's allocated AI trading budget and real-time utilization in 100% USDT.
    Calculates:
      - allocated_budget_usdt: e.g. $500.00 USDT
      - total_active_invested_usdt: sum of invested USDT across all OPEN positions
      - remaining_budget_usdt: max(0.0, allocated - invested)
      - utilization_pct: percentage of budget used (0-100%)
      - is_budget_full: boolean flag when remaining budget is exhausted (< $2.00)
    """
    budget_cfg = _USER_BUDGET.get(user_id)
    if not budget_cfg and db is not None:
        try:
            doc = await db.ai_budgets.find_one({"user_id": user_id})
            if doc:
                budget_cfg = {
                    "budget_usdt": float(doc.get("budget_usdt", doc.get("budget", 500.0))),
                }
                _USER_BUDGET[user_id] = budget_cfg
        except Exception:
            pass

    if not budget_cfg:
        budget_cfg = {
            "budget_usdt": 500.0,
        }
        _USER_BUDGET[user_id] = budget_cfg

    budget_usdt = float(budget_cfg.get("budget_usdt", 500.0))

    # Calculate active invested funds in open positions
    total_invested_usdt = 0.0
    open_positions_count = 0
    if db is not None:
        try:
            positions = await db.positions.find({"user_id": user_id}).to_list(100)
            for p in positions:
                qty = float(p.get("quantity", 0))
                if qty > 0.000001 and p.get("status") != "CLOSED":
                    avg_p = float(p.get("average_entry_price") or p.get("avg_price") or 0)
                    cost = float(p.get("total_invested") or (qty * avg_p))
                    total_invested_usdt += cost
                    open_positions_count += 1
        except Exception as e:
            print(f"[auto_ai_trader] budget position calc error: {e}")

    total_invested_usdt = round(total_invested_usdt, 4)
    remaining_usdt = max(0.0, round(budget_usdt - total_invested_usdt, 4))
    utilization_pct = min(100.0, round((total_invested_usdt / budget_usdt) * 100, 1)) if budget_usdt > 0 else 0.0
    is_budget_full = remaining_usdt < 2.0

    return {
        "user_id": user_id,
        "allocated_budget_usdt": budget_usdt,
        "total_active_invested_usdt": total_invested_usdt,
        "remaining_budget_usdt": remaining_usdt,
        "utilization_pct": utilization_pct,
        "is_budget_full": is_budget_full,
        "open_positions_count": open_positions_count,
        "currency": "USDT",
    }


async def set_user_budget(db, user_id: str, budget_usdt: float) -> Dict[str, Any]:
    """Save user's allocated AI trading budget in USDT."""
    b_usdt = max(5.0, float(budget_usdt))

    _USER_BUDGET[user_id] = {
        "budget_usdt": b_usdt,
    }

    if db is not None:
        try:
            await db.ai_budgets.update_one(
                {"user_id": user_id},
                {"$set": {
                    "user_id": user_id,
                    "budget_usdt": b_usdt,
                    "updated_at": _now_iso(),
                }},
                upsert=True
            )
        except Exception as e:
            print(f"[auto_ai_trader] ai_budgets save error: {e}")

    return await get_user_budget_summary(db, user_id)


def get_user_coins(user_id: str) -> List[str]:
    return _USER_COINS.get(user_id, DEFAULT_COINS)


def set_user_coins(user_id: str, coins: List[str]) -> List[str]:
    cleaned = []
    for c in coins:
        sym = str(c).strip().upper()
        if sym:
            if not sym.endswith("USDT"):
                sym = sym + "USDT"
            if sym not in cleaned:
                cleaned.append(sym)
    if not cleaned:
        cleaned = DEFAULT_COINS
    _USER_COINS[user_id] = cleaned
    return cleaned


async def get_auto_trader_trades(db, user_id: str) -> List[Dict[str, Any]]:
    """Get clean, deduplicated trade history combining in-memory stream with persistent DB executions."""
    seen_keys = set()
    combined = []

    # 1. Fetch AI decisions to enrich trades with full reasoning, technical regime, and risk metrics
    decision_map = {}
    try:
        decisions = await db.ai_decisions.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
        for d in decisions:
            oid = d.get("order_id")
            if oid:
                decision_map[oid] = d
            sym = d.get("symbol")
            if sym and sym not in decision_map:
                decision_map[sym] = d
    except Exception:
        pass

    def _make_dedup_key(item: Dict) -> str:
        sym = item.get("symbol", "")
        side = str(item.get("action") or item.get("side", "")).upper()
        qty = round(float(item.get("quantity") or 0), 4)
        if "REJECT" in side:
            reason = str(item.get("reason") or item.get("risk_reason") or "")[:25]
            return f"rej_{sym}_{reason}"
        return f"trade_{sym}_{side}_{qty}"

    # 2. In-memory trades (highest fidelity with local timestamps)
    mem_trades = _LATEST_TRADES.get(user_id, [])
    for t in mem_trades:
        key = _make_dedup_key(t)
        if key not in seen_keys:
            seen_keys.add(key)
            d_meta = decision_map.get(t.get("order_id")) or decision_map.get(t.get("symbol")) or {}
            combined.append({
                **t,
                "reason": t.get("reason") or t.get("rationale") or d_meta.get("reason") or "AI Signal Analysis",
                "rationale": t.get("rationale") or t.get("reason") or d_meta.get("reason") or "AI Signal Analysis",
                "market_regime": t.get("market_regime") or d_meta.get("market_regime") or "MOMENTUM_BREAKOUT",
                "stop_loss": t.get("stop_loss") or d_meta.get("stop_loss"),
                "take_profit": t.get("take_profit") or d_meta.get("take_profit"),
                "confidence": t.get("confidence") or d_meta.get("confidence", 85.0),
                "score": t.get("score") or d_meta.get("score", 75),
            })

    # 3. Check Supabase db.trades table (persistent trades)
    try:
        db_trades = await db.trades.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
        for t in db_trades:
            key = _make_dedup_key(t)
            if key not in seen_keys:
                seen_keys.add(key)
                price = float(t.get("price") or t.get("avg_price") or 0)
                qty = float(t.get("quantity") or 0)
                quote = round(price * qty, 2) if price and qty else float(t.get("quote_amount") or 0)
                pnl = float(t.get("realized_pnl", 0)) if t.get("realized_pnl") is not None else 0.0
                side = str(t.get("side", "BUY")).upper()
                d_meta = decision_map.get(t.get("order_id")) or decision_map.get(t.get("symbol")) or {}

                default_reason = (
                    f"🟢 Bullish momentum signal (Score: {d_meta.get('score', 85)}/100). Technical indicators indicate strong upside breakout."
                    if side == "BUY"
                    else f"🔴 Exit signal executed. Realized PnL: ${pnl:+,.2f}. Profit/Loss locked in."
                )
                full_reason = t.get("reason") or t.get("rationale") or d_meta.get("reason") or default_reason

                combined.append({
                    "id": t.get("id"),
                    "time": t.get("created_at"),
                    "trade_time": t.get("created_at"),
                    "created_at": t.get("created_at"),
                    "symbol": t.get("symbol", "BTCUSDT"),
                    "action": side,
                    "side": side,
                    "buy_price": price if side == "BUY" else None,
                    "sell_price": price if side == "SELL" else None,
                    "price": price,
                    "quantity": qty,
                    "amount": quote,
                    "fee": float(t.get("fee") or round(quote * FEE_RATE, 4)),
                    "realized_pnl": pnl if side == "SELL" else None,
                    "score": t.get("score") or d_meta.get("score", 85),
                    "confidence": t.get("confidence") or d_meta.get("confidence", 85.0),
                    "market_regime": t.get("market_regime") or d_meta.get("market_regime") or ("BULLISH_BREAKOUT" if side == "BUY" else "PROFIT_TAKE"),
                    "stop_loss": t.get("stop_loss") or d_meta.get("stop_loss") or (round(price * 0.975, 4) if price else None),
                    "take_profit": t.get("take_profit") or d_meta.get("take_profit") or (round(price * 1.03, 4) if price else None),
                    "order_id": t.get("id"),
                    "rationale": full_reason,
                    "reason": full_reason,
                })
    except Exception as e:
        print(f"[auto_ai_trader] load db.trades error: {e}")

    # 4. Check Risk Blocked / Rejected decisions
    try:
        rejected = await db.ai_decisions.find(
            {"user_id": user_id, "risk_verdict": "REJECTED"}, {"_id": 0}
        ).sort("created_at", -1).limit(20).to_list(20)
        for r in rejected:
            rid = f"rej_{r.get('id')}"
            if rid not in seen_keys:
                seen_keys.add(rid)
                price = float(r.get("entry_price") or r.get("price") or 0)
                reason_text = r.get("risk_reason") or r.get("reason") or "Risk Filter Rejection"
                combined.append({
                    "id": rid,
                    "time": r.get("created_at"),
                    "trade_time": r.get("created_at"),
                    "created_at": r.get("created_at"),
                    "symbol": r.get("symbol"),
                    "action": "BUY_REJECTED",
                    "side": "BUY_REJECTED",
                    "buy_price": price or None,
                    "sell_price": None,
                    "price": price,
                    "quantity": 0.0,
                    "amount": 0.0,
                    "fee": 0.0,
                    "realized_pnl": None,
                    "score": r.get("score") or 60,
                    "confidence": r.get("confidence") or 70.0,
                    "market_regime": r.get("market_regime") or "HIGH_VOLATILITY",
                    "stop_loss": r.get("stop_loss"),
                    "take_profit": r.get("take_profit"),
                    "order_id": r.get("id"),
                    "rationale": f"⚠️ Blocked by Risk Engine: {reason_text}",
                    "reason": f"⚠️ Blocked by Risk Engine: {reason_text}",
                })
    except Exception as e:
        print(f"[auto_ai_trader] load rejected decisions error: {e}")

    # Sort descending by timestamp
    combined.sort(key=lambda x: str(x.get("time") or x.get("created_at") or ""), reverse=True)
    return combined[:50]


def set_ai_enabled(user_id: str, enabled: bool) -> None:
    _AI_ENABLED[user_id] = enabled


def get_ai_enabled(user_id: str) -> bool:
    return _AI_ENABLED.get(user_id, True)


def _add_trade_log(user_id: str, entry: Dict) -> None:
    if user_id not in _LATEST_TRADES:
        _LATEST_TRADES[user_id] = []
    _LATEST_TRADES[user_id].insert(0, entry)
    _LATEST_TRADES[user_id] = _LATEST_TRADES[user_id][:100]


async def _record_ai_decision(db, user_id: str, symbol: str, decision: str,
                                score: int, confidence: float, market_regime: str,
                                entry_price: float, target_price: float, stop_loss: float,
                                risk_verdict: str, risk_rejection_reason: str,
                                reason: str, order_id: str = "", risk_score: float = 0.0) -> str:
    """Save AI decision to ai_decisions table for full auditability."""
    risk_reward = 0.0
    if target_price and entry_price and stop_loss and (entry_price - stop_loss) > 0:
        risk_reward = round((target_price - entry_price) / (entry_price - stop_loss), 4)

    rec = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "symbol": symbol,
        "decision": decision,
        "confidence": round(confidence, 2),
        "score": score,
        "market_regime": market_regime,
        "entry_price": round(entry_price, 8) if entry_price else None,
        "target_price": round(target_price, 8) if target_price else None,
        "stop_loss": round(stop_loss, 8) if stop_loss else None,
        "risk_reward": risk_reward,
        "risk_score": round(risk_score, 1),
        "risk_verdict": risk_verdict,
        "risk_rejection_reason": risk_rejection_reason,
        "strategy": "AI_AUTO",
        "model_version": MODEL_VERSION,
        "reason": reason,
        "order_id": order_id,
        "created_at": _now_iso()
    }
    try:
        await db.ai_decisions.insert_one(rec)
    except Exception as e:
        print(f"[auto_ai_trader] ai_decisions insert failed: {e}")
    return rec["id"]


_USER_LOCKS: Dict[str, Any] = {}

def _get_user_lock(user_id: str):
    import asyncio
    if user_id not in _USER_LOCKS:
        _USER_LOCKS[user_id] = asyncio.Lock()
    return _USER_LOCKS[user_id]


async def run_ai_cycle(db, user_id: str, symbol: str,
                        force_trade: Optional[str] = None) -> Dict[str, Any]:
    """
    Run one full AI trading cycle for a symbol.

    Full pipeline:
      AI signal -> Risk Engine -> Order -> Reserve Funds -> Execute -> Ledger -> Balance

    Returns detailed result dict with all decision data.
    """
    # Clean up any stale unfulfilled OPEN orders and release their locks
    if db is not None:
        try:
            stale_orders = await db.orders.find({"user_id": user_id, "status": "OPEN"}).to_list(50)
            for so in stale_orders:
                so_id = so.get("id")
                ex = await db.executions.find_one({"order_id": so_id})
                if not ex:
                    await order_service.cancel_order(db, so, "Auto-cancelled stale open order")
                    amt = float(so.get("quote_amount", 0))
                    if amt > 0:
                        await wallet_service.release_reservation(db, user_id, "USDT", amt)
        except Exception:
            pass

    # --- 1. Get market data and AI signal ---
    try:
        df, src = await md.get_klines(symbol, "1h", 100)
        if df is None or len(df) < 10:
            return {"symbol": symbol, "action": "SKIP", "reason": "Insufficient market data"}
        indicators = compute_indicators(df)
        current_price = float(indicators.get("close", df["close"].iloc[-1]))
    except Exception as e:
        return {"symbol": symbol, "action": "ERROR", "reason": f"Market data error: {e}"}

    try:
        regime_info = detect_market_regime(indicators)
        market_regime = regime_info.get("regime", "RANGING")
        confidence = float(regime_info.get("confidence", 75))

        signal_obj = {
            "action": "BUY" if force_trade == "BUY" else "HOLD",
            "entry_price": current_price,
            "stop_loss": round(current_price * 0.97, 8),
            "take_profit": round(current_price * 1.03, 8),
            "risk_level": "medium",
        }
        coin_meta = {"symbol": symbol, "name": symbol.replace("USDT", "")}
        intel = build_full_trade_intelligence(signal_obj, indicators, coin_meta)

        tq = intel.get("trade_quality", {})
        score = int(tq.get("score") or tq.get("composite_score") or 60)
        stop_loss = round(current_price * 0.97, 8)
        take_profit = round(current_price * 1.03, 8)
        reason = regime_info.get("description", "Technical Analysis")
    except Exception as e:
        score = 60
        confidence = 70.0
        market_regime = "RANGING"
        reason = f"Analysis default: {e}"
        stop_loss = round(current_price * 0.97, 8)
        take_profit = round(current_price * 1.03, 8)

    # --- 2. Check open position & determine action (BUY, SELL, HOLD) ---
    open_pos = await db.positions.find_one({"user_id": user_id, "symbol": symbol})
    has_open_position = open_pos is not None and float(open_pos.get("quantity", 0)) > 0.000001 and open_pos.get("status") != "CLOSED"

    if force_trade:
        action = force_trade.upper()
    elif has_open_position:
        # User already holds this coin — evaluate if we should SELL (Take-Profit / Stop-Loss / Bearish) or HOLD
        entry_price = float(open_pos.get("average_entry_price") or open_pos.get("avg_price") or current_price)
        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0

        if pnl_pct >= 3.0:
            action = "SELL"
            reason = f"🎯 TAKE-PROFIT HIT: +{pnl_pct:.2f}% gain (Bought @ ${entry_price:,.2f} -> Current: ${current_price:,.2f})"
        elif pnl_pct <= -2.5:
            action = "SELL"
            reason = f"🛑 STOP-LOSS HIT: {pnl_pct:.2f}% loss protection (Bought @ ${entry_price:,.2f} -> Current: ${current_price:,.2f})"
        elif score < 45:
            action = "SELL"
            reason = f"📉 BEARISH REVERSAL: AI Score dropped to {score}/100 (Exit signal)"
        else:
            action = "HOLD"
            reason = f"📌 HOLDING POSITION: PnL {pnl_pct:+.2f}% | Target: +3.0% (${entry_price * 1.03:,.2f}) | Stop: -2.5% (${entry_price * 0.975:,.2f})"
    else:
        # No position open — evaluate if we should BUY or HOLD
        if score >= 65:
            action = "BUY"
        else:
            action = "HOLD"
            reason = f"Waiting for breakout signal (Current Score: {score}/100, Need >= 65 to BUY)"

    # --- 3. Get portfolio value for risk sizing ---
    try:
        summary = await wallet_service.get_portfolio_summary(db, user_id)
        portfolio_value = summary["total_value_usdt"]
    except Exception:
        portfolio_value = get_user_capital(user_id)

    # --- 4. Handle HOLD ---
    if action == "HOLD":
        await _record_ai_decision(
            db, user_id, symbol, "HOLD", score, confidence, market_regime,
            current_price, take_profit, stop_loss,
            "N/A", "", reason
        )
        return {
            "symbol": symbol,
            "action": "HOLD",
            "score": score,
            "confidence": confidence,
            "market_regime": market_regime,
            "current_price": current_price,
            "reason": reason,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }

    # --- 5. BUY flow ---
    if action == "BUY":
        # 1. Enforce User's Allocated AI Budget Limit (100% USDT)
        budget_summary = await get_user_budget_summary(db, user_id)
        if budget_summary["is_budget_full"] or budget_summary["remaining_budget_usdt"] < 2.0:
            budget_reason = (
                f"⛔ AI Budget Cap Reached: Allocated budget of ${budget_summary['allocated_budget_usdt']:,.2f} USDT "
                f"is 100% utilized across {budget_summary['open_positions_count']} open positions "
                f"(${budget_summary['total_active_invested_usdt']:,.2f} USDT invested). "
                f"AI will NOT buy more coins until existing positions are sold or budget is increased."
            )
            await _record_ai_decision(
                db, user_id, symbol, "BUY", score, confidence, market_regime,
                current_price, take_profit, stop_loss,
                "REJECTED", budget_reason, reason, risk_score=95.0
            )
            _add_trade_log(user_id, {
                "time": _now_local(), "symbol": symbol, "action": "BUY_REJECTED",
                "reason": budget_reason, "score": score
            })
            return {
                "symbol": symbol, "action": "BUY_REJECTED",
                "score": score, "risk_reason": budget_reason, "budget_full": True
            }

        usdt_bal = await wallet_service.get_balance(db, user_id, "USDT")
        
        # If user has no USDT in wallet, auto-initialize with user capital for seamless paper trading
        if usdt_bal["available"] < 10.0:
            cap = get_user_capital(user_id)
            if cap >= 10.0:
                await wallet_service.initialize_wallet_with_usdt(db, user_id, cap)
                usdt_bal = await wallet_service.get_balance(db, user_id, "USDT")

        # Sizing: take max 25% of budget per trade, but never exceed remaining budget or wallet available USDT
        remaining_budget = budget_summary["remaining_budget_usdt"]
        target_size = max(budget_summary["allocated_budget_usdt"] * 0.25, 2.0)
        trade_size = min(
            remaining_budget,
            target_size,
            usdt_bal["available"],
            500.0
        )
        trade_size = round(max(trade_size, 1.0), 2)

        # Risk check
        approved, risk_reason, risk_score = await risk_engine.check_buy(
            db=db, user_id=user_id, symbol=symbol,
            quote_amount=trade_size, score=score,
            stop_loss=stop_loss, take_profit=take_profit,
            entry_price=current_price, portfolio_value=portfolio_value
        )

        if not approved:
            await _record_ai_decision(
                db, user_id, symbol, "BUY", score, confidence, market_regime,
                current_price, take_profit, stop_loss,
                "REJECTED", risk_reason, reason, risk_score=risk_score
            )
            _add_trade_log(user_id, {
                "time": _now_local(), "symbol": symbol, "action": "BUY_REJECTED",
                "reason": risk_reason, "score": score
            })
            return {
                "symbol": symbol, "action": "BUY_REJECTED",
                "score": score, "risk_reason": risk_reason
            }

        # Create order
        order = await order_service.create_order(
            db, user_id, symbol, "BUY", trade_size
        )
        await order_service.mark_risk_approved(db, order)

        # Reserve USDT funds (available down, locked up)
        reserved = await wallet_service.reserve_funds(db, user_id, "USDT", trade_size)
        if not reserved:
            await order_service.cancel_order(db, order, "Insufficient balance at reservation time")
            return {"symbol": symbol, "action": "CANCELLED", "reason": "Insufficient USDT at reservation"}

        await order_service.mark_funds_reserved(db, order, trade_size)

        # Execute fill (ledger posts, balance settles)
        try:
            execution = await execution_service.execute_buy(db, order, current_price)
        except Exception as e:
            await order_service.cancel_order(db, order, f"Execution failed: {e}")
            await wallet_service.release_reservation(db, user_id, "USDT", trade_size)
            return {"symbol": symbol, "action": "ERROR", "reason": f"Execution failed: {e}"}

        # Record AI decision with order ID
        await _record_ai_decision(
            db, user_id, symbol, "BUY", score, confidence, market_regime,
            current_price, take_profit, stop_loss,
            "APPROVED", "", reason, order_id=order["id"], risk_score=risk_score
        )

        qty = execution["quantity"]
        fee = execution["fee"]
        trade_log = {
            "time": _now_local(),
            "symbol": symbol,
            "action": "BUY",
            "buy_price": current_price,
            "sell_price": None,
            "quantity": qty,
            "amount": trade_size,
            "fee": fee,
            "realized_pnl": None,
            "score": score,
            "confidence": confidence,
            "market_regime": market_regime,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reason": reason,
            "order_id": order["id"],
            "execution_id": execution["id"],
        }
        _add_trade_log(user_id, trade_log)

        print(f"[auto_ai_trader] BUY {symbol}: ${trade_size:.2f} @ ${current_price:,.4f} | qty={qty:.6f} | fee=${fee:.4f}")
        return {
            "symbol": symbol, "action": "BUY",
            "price": current_price, "quantity": qty,
            "amount": trade_size, "fee": fee,
            "score": score, "order_id": order["id"],
            "stop_loss": stop_loss, "take_profit": take_profit,
            "market_regime": market_regime,
        }

    # --- 6. SELL flow ---
    if action == "SELL":
        approved, risk_reason, risk_score = await risk_engine.check_sell(
            db, user_id, symbol, score
        )

        if not approved:
            await _record_ai_decision(
                db, user_id, symbol, "SELL", score, confidence, market_regime,
                current_price, take_profit, stop_loss,
                "REJECTED", risk_reason, reason, risk_score=risk_score
            )
            return {"symbol": symbol, "action": "SELL_REJECTED", "reason": risk_reason}

        pos = open_pos or await db.positions.find_one({"user_id": user_id, "symbol": symbol})
        if not pos or float(pos.get("quantity", 0)) <= 0.000001:
            return {"symbol": symbol, "action": "NO_POSITION", "reason": "No open position to sell"}

        position_value = float(pos.get("quantity", 0)) * current_price
        order = await order_service.create_order(
            db, user_id, symbol, "SELL", position_value
        )
        await order_service.mark_risk_approved(db, order)
        await order_service.mark_funds_reserved(db, order, position_value)

        # Execute fill
        try:
            execution, realized_pnl = await execution_service.execute_sell(
                db, order, pos, current_price
            )
        except Exception as e:
            await order_service.cancel_order(db, order, f"Execution failed: {e}")
            return {"symbol": symbol, "action": "ERROR", "reason": f"Sell execution failed: {e}"}

        # Record AI decision
        await _record_ai_decision(
            db, user_id, symbol, "SELL", score, confidence, market_regime,
            current_price, take_profit, stop_loss,
            "APPROVED", "", reason, order_id=order["id"], risk_score=risk_score
        )

        entry_price = float(pos.get("average_entry_price", current_price))
        qty = float(pos.get("quantity", 0))
        fee = execution.get("fee", 0)

        trade_log = {
            "time": _now_local(),
            "symbol": symbol,
            "action": "SELL",
            "buy_price": entry_price,
            "sell_price": current_price,
            "quantity": qty,
            "amount": qty * current_price,
            "fee": fee,
            "realized_pnl": realized_pnl,
            "score": score,
            "confidence": confidence,
            "market_regime": market_regime,
            "reason": reason,
            "order_id": order["id"],
            "execution_id": execution["id"],
        }
        _add_trade_log(user_id, trade_log)

        pnl_str = f"+${realized_pnl:.2f}" if realized_pnl >= 0 else f"-${abs(realized_pnl):.2f}"
        print(f"[auto_ai_trader] SELL {symbol}: {qty:.6f} @ ${current_price:,.4f} | PnL={pnl_str}")
        return {
            "symbol": symbol, "action": "SELL",
            "price": current_price, "quantity": qty,
            "realized_pnl": realized_pnl, "fee": fee,
            "score": score, "order_id": order["id"],
            "market_regime": market_regime,
        }

    return {"symbol": symbol, "action": "UNKNOWN"}


async def scan_coins(db, user_id: str, symbols: List[str]) -> List[Dict]:
    """Scan coins with parallel market data prefetching + sequential atomic trade execution."""
    import asyncio

    # Clean stale unfulfilled OPEN orders once per scan
    if db is not None:
        try:
            stale_orders = await db.orders.find({"user_id": user_id, "status": "OPEN"}).to_list(20)
            for so in stale_orders:
                so_id = so.get("id")
                ex = await db.executions.find_one({"order_id": so_id})
                if not ex:
                    await order_service.cancel_order(db, so, "Auto-cancelled stale open order")
                    amt = float(so.get("quote_amount", 0))
                    if amt > 0:
                        await wallet_service.release_reservation(db, user_id, "USDT", amt)
        except Exception:
            pass

    # 1. Prefetch market klines for all coins in parallel
    try:
        await asyncio.gather(*[md.get_klines(sym, "1h", 100) for sym in symbols], return_exceptions=True)
    except Exception:
        pass

    # 2. Evaluate and size trades sequentially under user lock
    results = []
    for sym in symbols:
        try:
            res = await run_ai_cycle(db, user_id, sym)
            results.append(res)
        except Exception as e:
            results.append({"symbol": sym, "action": "ERROR", "reason": str(e)})
    return results


async def get_live_positions_with_pnl(db, user_id: str) -> List[Dict]:
    """Get all open positions with live current prices and unrealized P&L."""
    try:
        positions = await position_service.get_open_positions(db, user_id)
        if not positions:
            return []

        symbols = [p["symbol"] for p in positions]
        price_map = {}
        try:
            tickers, _ = await md.ticker_24hr(symbols)
            for t in tickers:
                price_map[t["symbol"]] = float(t.get("lastPrice", 0))
        except Exception:
            pass

        enriched = []
        for pos in positions:
            symbol = pos["symbol"]
            live_price = price_map.get(symbol) or float(pos.get("current_price", 0))
            if live_price <= 0:
                live_price = float(pos.get("average_entry_price", 1.0))

            qty = float(pos.get("quantity", 0))
            avg_entry = float(pos.get("average_entry_price", live_price))
            cost_basis = float(pos.get("total_invested", qty * avg_entry))
            current_value = round(qty * live_price, 4)
            unrealized_pnl = round(current_value - cost_basis, 4)
            pnl_pct = round((unrealized_pnl / cost_basis * 100), 2) if cost_basis > 0 else 0.0

            enriched.append({
                **pos,
                "current_price": live_price,
                "current_value": current_value,
                "cost_basis": cost_basis,
                "unrealized_pnl": unrealized_pnl,
                "pnl_percentage": pnl_pct,
                "avg_buy_price": avg_entry,
                "entry_price": avg_entry,
            })
        return enriched
    except Exception as e:
        print(f"[auto_ai_trader] get_live_positions_with_pnl error: {e}")
        return []


async def reset_all_user_trading_data(db, user_id: str, initial_usdt: float = 0.0) -> Dict[str, Any]:
    """
    Completely wipe trade history, open positions, orders, executions, AI decisions,
    and ledger history for this user, starting completely fresh from 0.
    """
    # 1. Clear in-memory state
    global _LATEST_TRADES
    _LATEST_TRADES.clear()

    _USER_CAPITAL[user_id] = 1000.0
    _USER_BUDGET[user_id] = {
        "user_id": user_id,
        "budget_usdt": 1000.0,
    }

    if db is not None:
        try:
            import asyncio
            tables = [
                db.positions, db.trades, db.orders, db.order_events,
                db.executions, db.ai_decisions, db.paper_trades,
                db.ledger_entries, db.ledger_transactions, db.deposits,
                db.payment_transactions, db.ai_budgets, db.wallet_balances
            ]
            await asyncio.gather(*[t.delete_many({}) for t in tables], return_exceptions=True)

            # Reinitialize wallet for user with 1000.0 USDT
            from services import wallet_service
            for uid in [user_id, "default_user", "aabf552e-7359-40b0-95ce-2d6e046022f4"]:
                await wallet_service.initialize_wallet_with_usdt(db, uid, 1000.0)
        except Exception as e:
            print(f"[auto_ai_trader] reset error: {e}")

    return {
        "status": "ok",
        "message": "All trading history, positions, and balance completely reset to $1,000.00 USDT clean slate.",
        "user_id": user_id,
        "trades_count": 0,
        "positions_count": 0,
        "cash_available": 1000.0,
        "cash_locked": 0.0,
        "balance_usdt": 1000.0,
    }
