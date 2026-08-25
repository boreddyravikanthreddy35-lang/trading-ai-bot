"""Autonomous AI Crypto Portfolio Manager Service.

Implements the 5-Brain Autonomous Trading Engine:
1. Market AI: Multi-asset live scanner (BTC, ETH, SOL, BNB, ADA, DOGE, AVAX)
2. Prediction Score Engine: Standardized 0-100 score across 5 sub-agents
3. Decision AI: Mapped thresholds (80-100 BUY, 60-79 HOLD, 40-59 WAIT, 0-39 SELL)
4. Allocation & Risk Engine: Dynamic position sizing (max 30% per setup, cash buffer preserved)
5. Execution Engine: Orders placed, portfolio rebalanced, audit logs generated
"""
import uuid
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services import market_data as md
from services.indicators import compute_indicators
from services.trade_intelligence import build_full_trade_intelligence

ASSET_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"]
DEFAULT_CAPITAL = 1000.0  # $1,000 default allocated trading capital
MAX_POSITION_PCT = 0.30   # Max 30% of capital into a single asset ($300 of $1,000)
FEE_RATE = 0.001          # 0.1% simulated fee

_LATEST_CYCLES: Dict[str, Dict[str, Any]] = {}


def get_latest_cycle(user_id: str) -> Optional[Dict[str, Any]]:
    return _LATEST_CYCLES.get(user_id)



def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def _current_price(symbol: str) -> float:
    df, _ = await md.get_klines(symbol, "1m", 5)
    if df is None or df.empty:
        raise RuntimeError(f"Unable to price {symbol}")
    return float(df.iloc[-1]["close"])


async def _ensure_portfolio(db, user_id: str, default_cash: float = DEFAULT_CAPITAL) -> Dict[str, Any]:
    doc = await db.portfolios.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        return doc
    doc = {
        "user_id": user_id,
        "cash": default_cash,
        "created_at": _now_iso(),
    }
    await db.portfolios.insert_one(dict(doc))
    return doc


def map_score_to_decision(score: int, circuit_breaker: bool = False) -> Dict[str, Any]:
    """3. Decision AI: Maps Prediction Score (0-100) to continuous action state."""
    if circuit_breaker:
        return {
            "action": "SELL",
            "state": "🔴 SELL / EXIT",
            "badge": "🔴 CIRCUIT BREAKER — EXIT",
            "description": "Risk Circuit Breaker Active. Exiting position to preserve capital.",
        }
    if score >= 80:
        return {
            "action": "BUY",
            "state": "🟢 BUY / ADD",
            "badge": "🟢 STRONG BUY (80-100)",
            "description": "High conviction setup score. Allocate capital into asset.",
        }
    elif score >= 60:
        return {
            "action": "HOLD",
            "state": "🟡 HOLD",
            "badge": "🟡 HOLD (60-79)",
            "description": "Moderate bullish score. Maintain existing position size without adding.",
        }
    elif score >= 40:
        return {
            "action": "WAIT",
            "state": "🟡 WAIT / HOLD",
            "badge": "🟡 WAIT (40-59)",
            "description": "Neutral score. Do not risk new capital; preserve cash buffer.",
        }
    else:
        return {
            "action": "SELL",
            "state": "🔴 SELL / EXIT",
            "badge": "🔴 SELL / EXIT (0-39)",
            "description": "Weak setup score. Exit position completely and return funds to cash buffer.",
        }


async def run_autonomous_cycle(
    db,
    user_id: str,
    allocated_capital: float = DEFAULT_CAPITAL,
    symbol_list: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Executes one full scan-score-decide-allocate-execute cycle for the user."""
    symbols = symbol_list or ASSET_UNIVERSE
    cycle_id = str(uuid.uuid4())
    start_time = _now_iso()

    portfolio = await _ensure_portfolio(db, user_id, allocated_capital)
    positions = await db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(200)
    pos_map = {p["symbol"]: p for p in positions if p.get("quantity", 0) > 0}

    asset_evaluations: List[Dict[str, Any]] = []
    actions_taken: List[Dict[str, Any]] = []

    # Max allocation per single trade
    max_trade_usd = allocated_capital * MAX_POSITION_PCT

    for sym in symbols:
        try:
            # 1. Market AI Scanner
            df, kline_src = await md.get_klines(sym, "1h", 200)
            if df is None or len(df) < 30:
                continue
            indicators = compute_indicators(df)
            price = float(df.iloc[-1]["close"])

            coin_meta = {
                "name": sym.replace("USDT", ""),
                "symbol": sym,
                "current_price": price,
                "price_change_percentage_24h": indicators.get("pct_change_24h"),
                "total_volume": indicators.get("volume_24h"),
            }

            # 2. Prediction Score Engine
            rsi_val_p = float(indicators.get("rsi") or indicators.get("rsi_14") or 50.0)
            volatility_p = float(indicators.get("volatility") or 0.03)
            if rsi_val_p > 75 or rsi_val_p < 25 or volatility_p > 0.06:
                risk_lvl = "high"
            elif rsi_val_p > 65 or rsi_val_p < 35 or volatility_p > 0.04:
                risk_lvl = "medium"
            else:
                risk_lvl = "low"

            sma20_p = float(indicators.get("sma20") or indicators.get("sma_20") or 0)
            simulated_signal = {
                "action": "BUY" if price > sma20_p else "HOLD",
                "risk_level": risk_lvl,
                "entry_price": price,
                "stop_loss": price * 0.98,
                "take_profit": price * 1.05,
            }
            intel = build_full_trade_intelligence(simulated_signal, indicators, coin_meta)
            decision_info = intel.get("decision_engine") or {}
            score = int(decision_info.get("trade_score") or 50)
            circuit_breaker = bool(decision_info.get("circuit_breaker_tripped"))

            # 3. Decision AI
            decision = map_score_to_decision(score, circuit_breaker)
            action = decision["action"]

            # 4. Allocation & Risk Engine
            current_pos = pos_map.get(sym)
            has_position = current_pos is not None and current_pos.get("quantity", 0) > 0

            target_allocation_usd = 0.0
            execution_status = "NO_CHANGE"
            execution_details = decision["description"]

            if action == "BUY":
                # If no position, enter up to max_trade_usd
                if not has_position:
                    avail_cash = float(portfolio["cash"])
                    buy_usd = min(max_trade_usd, avail_cash)
                    if buy_usd >= 20.0:  # Min trade size $20
                        # 5. Execution Engine — BUY
                        qty = buy_usd / price
                        cost = qty * price
                        fee = cost * FEE_RATE
                        needed = cost + fee

                        if needed <= portfolio["cash"]:
                            new_cash = portfolio["cash"] - needed
                            await db.positions.insert_one({
                                "user_id": user_id,
                                "symbol": sym,
                                "quantity": qty,
                                "avg_price": price,
                            })
                            await db.portfolios.update_one({"user_id": user_id}, {"$set": {"cash": new_cash}})
                            portfolio["cash"] = new_cash

                            trade_doc = {
                                "id": str(uuid.uuid4()),
                                "user_id": user_id,
                                "symbol": sym,
                                "side": "BUY",
                                "quantity": qty,
                                "price": price,
                                "fee": fee,
                                "realized_pnl": 0.0,
                                "cash_after": new_cash,
                                "created_at": _now_iso(),
                                "source": "autonomous_ai",
                                "cycle_id": cycle_id,
                            }
                            await db.trades.insert_one(trade_doc)

                            execution_status = "EXECUTED_BUY"
                            target_allocation_usd = buy_usd
                            execution_details = f"🟢 Bought {qty:.6f} {sym} @ ${price:,.2f} (${buy_usd:,.2f} allocated)."
                            actions_taken.append({"symbol": sym, "type": "BUY", "usd": buy_usd, "qty": qty, "price": price})

            elif action == "SELL" and has_position:
                # 5. Execution Engine — SELL / EXIT
                qty = float(current_pos["quantity"])
                cost = qty * price
                fee = cost * FEE_RATE
                proceeds = cost - fee
                realized = (price - float(current_pos["avg_price"])) * qty
                new_cash = portfolio["cash"] + proceeds

                await db.positions.delete_one({"user_id": user_id, "symbol": sym})
                await db.portfolios.update_one({"user_id": user_id}, {"$set": {"cash": new_cash}})
                portfolio["cash"] = new_cash

                trade_doc = {
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    "symbol": sym,
                    "side": "SELL",
                    "quantity": qty,
                    "price": price,
                    "fee": fee,
                    "realized_pnl": realized,
                    "cash_after": new_cash,
                    "created_at": _now_iso(),
                    "source": "autonomous_ai",
                    "cycle_id": cycle_id,
                }
                await db.trades.insert_one(trade_doc)

                execution_status = "EXECUTED_SELL"
                execution_details = f"🔴 Liquidated {qty:.6f} {sym} @ ${price:,.2f} (Realized PnL: ${realized:+,.2f})."
                actions_taken.append({"symbol": sym, "type": "SELL", "usd": proceeds, "qty": qty, "pnl": realized})

            elif action in ["HOLD", "WAIT"] and has_position:
                current_val = float(current_pos["quantity"]) * price
                target_allocation_usd = current_val
                execution_details = f"🟡 Holding position ({current_pos['quantity']:.4f} {sym} worth ${current_val:,.2f})."

            asset_evaluations.append({
                "symbol": sym,
                "current_price": price,
                "prediction_score": score,
                "decision": decision,
                "execution_status": execution_status,
                "execution_details": execution_details,
                "target_allocation_usd": target_allocation_usd,
                "trade_intelligence": intel,
            })
        except Exception as e:
            asset_evaluations.append({
                "symbol": sym,
                "error": str(e),
                "prediction_score": 0,
                "decision": {"action": "WAIT", "state": "ERROR", "badge": "🔴 ERROR"},
            })

    # Summary calculation
    total_positions_val = 0.0
    for eval_item in asset_evaluations:
        total_positions_val += eval_item.get("target_allocation_usd", 0.0)

    total_equity = portfolio["cash"] + total_positions_val
    cash_buffer = portfolio["cash"]

    cycle_doc = {
        "id": cycle_id,
        "user_id": user_id,
        "allocated_capital": allocated_capital,
        "total_equity": total_equity,
        "cash_buffer": cash_buffer,
        "invested_usd": total_positions_val,
        "asset_evaluations": asset_evaluations,
        "actions_taken": actions_taken,
        "created_at": start_time,
    }
    _LATEST_CYCLES[user_id] = cycle_doc

    # Persist cycle log — gracefully skip if the table doesn't exist yet
    try:
        await db.autonomous_cycles.insert_one(dict(cycle_doc))
    except Exception:
        pass

    return cycle_doc

