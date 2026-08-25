import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apscheduler.triggers.interval import IntervalTrigger

from services import market_data as md
from services import scheduler as sched
from services.indicators import compute_indicators
from services.trade_intelligence import build_full_trade_intelligence

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"]
DEFAULT_CAPITAL = 1000.0
MAX_POSITION_PCT = 0.30
FEE_RATE = 0.001
STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.05

_USER_STATES: Dict[str, Dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _log_activity(user_id: str, message: str, activity_type: str):
    state = _USER_STATES.get(user_id)
    if not state:
        return
    log_entry = {
        "timestamp": _now_iso(),
        "message": message,
        "type": activity_type,
    }
    state.setdefault("activity_log", [])
    state["activity_log"].insert(0, log_entry)
    state["activity_log"] = state["activity_log"][:100]


def get_trader_status(user_id: str) -> Dict[str, Any]:
    state = _USER_STATES.get(user_id)
    if not state:
        return {
            "status": "STOPPED",
            "allocated_capital": DEFAULT_CAPITAL,
            "symbols": DEFAULT_SYMBOLS,
            "interval_minutes": 5,
            "buy_threshold": 80,
            "sell_threshold": 40,
            "stop_loss_pct": STOP_LOSS_PCT,
            "take_profit_pct": TAKE_PROFIT_PCT,
            "last_cycle_time": None,
        }
    return {
        "status": state.get("status", "STOPPED"),
        "allocated_capital": state.get("allocated_capital", DEFAULT_CAPITAL),
        "symbols": state.get("symbols", DEFAULT_SYMBOLS),
        "interval_minutes": state.get("interval_minutes", 5),
        "buy_threshold": state.get("buy_threshold", 80),
        "sell_threshold": state.get("sell_threshold", 40),
        "stop_loss_pct": state.get("stop_loss_pct", STOP_LOSS_PCT),
        "take_profit_pct": state.get("take_profit_pct", TAKE_PROFIT_PCT),
        "last_cycle_time": state.get("last_cycle_time"),
    }


async def start_continuous_trading(
    db,
    user_id: str,
    capital: Optional[float] = None,
    symbols: Optional[List[str]] = None,
    interval_minutes: Optional[int] = None,
    stop_loss_pct: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
    buy_threshold: Optional[int] = None,
    sell_threshold: Optional[int] = None,
) -> Dict[str, Any]:
    cap = float(capital) if capital and capital > 0 else DEFAULT_CAPITAL
    syms = symbols if symbols and len(symbols) > 0 else list(DEFAULT_SYMBOLS)
    interval = int(interval_minutes) if interval_minutes and interval_minutes > 0 else 5
    sl = float(stop_loss_pct) if stop_loss_pct is not None else STOP_LOSS_PCT
    tp = float(take_profit_pct) if take_profit_pct is not None else TAKE_PROFIT_PCT
    buy_t = int(buy_threshold) if buy_threshold is not None else 80
    sell_t = int(sell_threshold) if sell_threshold is not None else 40

    job_id = f"continuous_trader_{user_id}"

    # Initialize or update state
    _USER_STATES[user_id] = {
        "status": "ACTIVE",
        "allocated_capital": cap,
        "symbols": syms,
        "interval_minutes": interval,
        "stop_loss_pct": sl,
        "take_profit_pct": tp,
        "buy_threshold": buy_t,
        "sell_threshold": sell_t,
        "activity_log": _USER_STATES.get(user_id, {}).get("activity_log", []),
        "latest_analyses": _USER_STATES.get(user_id, {}).get("latest_analyses", {}),
        "job_id": job_id,
        "last_cycle_time": _now_iso(),
    }

    _log_activity(
        user_id,
        f"Started 24/7 autonomous trading engine (Capital: ${cap:,.2f}, {len(syms)} assets, interval: {interval}m, SL: {sl*100:.1f}%, TP: {tp*100:.1f}%).",
        "system",
    )

    if sched._scheduler is not None:
        trigger = IntervalTrigger(minutes=max(1, interval))
        try:
            sched._scheduler.add_job(
                _run_trading_cycle,
                trigger,
                id=job_id,
                args=[db, user_id],
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                next_run_time=datetime.now(tz=timezone.utc),
            )
        except Exception as e:
            logger.error(f"Error adding scheduler job {job_id}: {e}")

    return get_trader_status(user_id)


def pause_continuous_trading(user_id: str):
    if user_id in _USER_STATES:
        state = _USER_STATES[user_id]
        state["status"] = "PAUSED"
        _log_activity(user_id, "24/7 AI Autonomous Trader paused by user.", "system")


def resume_continuous_trading(user_id: str):
    if user_id in _USER_STATES:
        state = _USER_STATES[user_id]
        state["status"] = "ACTIVE"
        _log_activity(user_id, "24/7 AI Autonomous Trader resumed.", "system")


async def stop_continuous_trading(db, user_id: str, sell_all: bool = False):
    if user_id in _USER_STATES:
        state = _USER_STATES[user_id]
        job_id = state.get("job_id")

        if sched._scheduler is not None and job_id:
            try:
                sched._scheduler.remove_job(job_id)
            except Exception:
                pass

        if sell_all:
            await sell_all_positions(db, user_id)

        state["status"] = "STOPPED"
        _log_activity(user_id, "24/7 AI Autonomous Trader stopped.", "system")


async def sell_position_now(db, user_id: str, symbol: str) -> Dict[str, Any]:
    pos = await db.positions.find_one({"user_id": user_id, "symbol": symbol}, {"_id": 0})
    if not pos:
        return {"status": "error", "message": f"No open position found for {symbol}"}

    qty = float(pos.get("quantity", 0))
    if qty <= 0:
        return {"status": "error", "message": f"Zero quantity in position for {symbol}"}

    try:
        df, _ = await md.get_klines(symbol, "1m", 5)
        current_price = float(df.iloc[-1]["close"]) if df is not None and len(df) > 0 else float(pos.get("avg_price", 0))
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
        current_price = float(pos.get("avg_price", 0))

    portfolio_doc = await db.portfolios.find_one({"user_id": user_id}, {"_id": 0})
    cash = float(portfolio_doc.get("cash", 0)) if portfolio_doc else 0.0

    cost = qty * current_price
    fee = cost * FEE_RATE
    proceeds = cost - fee
    avg_price = float(pos.get("avg_price", current_price))
    realized = (current_price - avg_price) * qty
    new_cash = cash + proceeds

    await db.positions.delete_one({"user_id": user_id, "symbol": symbol})
    await db.portfolios.update_one({"user_id": user_id}, {"$set": {"cash": new_cash}}, upsert=True)

    trade_doc = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "symbol": symbol,
        "side": "SELL",
        "quantity": qty,
        "price": current_price,
        "fee": fee,
        "realized_pnl": realized,
        "cash_after": new_cash,
        "created_at": _now_iso(),
        "source": "continuous_ai",
        "score": 0,
        "rationale": "Manual immediate sell execution requested by user.",
    }
    try:
        await db.trades.insert_one(dict(trade_doc))
    except Exception:
        pass

    _log_activity(
        user_id,
        f"Sold {qty:.6f} {symbol} @ ${current_price:,.4f} (Realized PnL: ${realized:+,.2f})",
        "manual_sell",
    )
    return {
        "symbol": symbol,
        "quantity": qty,
        "price": current_price,
        "realized_pnl": realized,
        "cash_after": new_cash,
    }


async def sell_all_positions(db, user_id: str) -> List[Dict[str, Any]]:
    positions = await db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(100)
    results = []
    for pos in positions:
        res = await sell_position_now(db, user_id, pos["symbol"])
        results.append(res)
    return results


async def _run_trading_cycle(db, user_id: str):
    state = _USER_STATES.get(user_id)
    if not state or state.get("status") != "ACTIVE":
        return

    state["last_cycle_time"] = _now_iso()
    symbols = state.get("symbols", DEFAULT_SYMBOLS)
    stop_loss_pct = state.get("stop_loss_pct", STOP_LOSS_PCT)
    take_profit_pct = state.get("take_profit_pct", TAKE_PROFIT_PCT)
    buy_threshold = state.get("buy_threshold", 80)
    sell_threshold = state.get("sell_threshold", 40)
    allocated_capital = state.get("allocated_capital", DEFAULT_CAPITAL)

    for symbol in symbols:
        try:
            df, _ = await md.get_klines(symbol, "1h", 200)
            if df is None or len(df) < 30:
                continue

            indicators = compute_indicators(df)
            current_price = float(indicators.get("price") or df.iloc[-1]["close"])

            # 1. Stop-loss / Take-profit Guard
            pos = await db.positions.find_one({"user_id": user_id, "symbol": symbol}, {"_id": 0})
            has_position = pos is not None and float(pos.get("quantity", 0)) > 0

            if has_position:
                entry_price = float(pos.get("avg_price", current_price))
                if entry_price > 0:
                    pct_change = (current_price - entry_price) / entry_price
                    if pct_change <= -stop_loss_pct:
                        _log_activity(
                            user_id,
                            f"🛑 STOP-LOSS HIT for {symbol}: Entry ${entry_price:,.2f} -> Current ${current_price:,.2f} ({pct_change*100:.2f}%)",
                            "stop_loss",
                        )
                        await sell_position_now(db, user_id, symbol)
                        continue
                    elif pct_change >= take_profit_pct:
                        _log_activity(
                            user_id,
                            f"🎯 TAKE-PROFIT HIT for {symbol}: Entry ${entry_price:,.2f} -> Current ${current_price:,.2f} ({pct_change*100:.2f}%)",
                            "take_profit",
                        )
                        await sell_position_now(db, user_id, symbol)
                        continue

            # 2. Build Trade Intelligence
            pct_24h = float(indicators.get("pct_change_24h") or 0.0)
            coin_meta = {
                "name": symbol.replace("USDT", ""),
                "symbol": symbol,
                "current_price": current_price,
                "price_change_percentage_24h": pct_24h,
                "total_volume": indicators.get("volume_24h", 0),
            }

            rsi_val_signal = float(indicators.get("rsi") or indicators.get("rsi_14") or 50.0)
            volatility_val = float(indicators.get("volatility") or 0.03)
            if rsi_val_signal > 75 or rsi_val_signal < 25 or volatility_val > 0.06:
                signal_risk = "high"
            elif rsi_val_signal > 65 or rsi_val_signal < 35 or volatility_val > 0.04:
                signal_risk = "medium"
            else:
                signal_risk = "low"

            sma20_val = float(indicators.get("sma20") or indicators.get("sma_20") or 0)
            simulated_signal = {
                "action": "BUY" if current_price > sma20_val else "HOLD",
                "risk_level": signal_risk,
                "entry_price": current_price,
                "stop_loss": current_price * (1 - stop_loss_pct),
                "take_profit": current_price * (1 + take_profit_pct),
            }

            intel = build_full_trade_intelligence(simulated_signal, indicators, coin_meta)
            decision_info = intel.get("decision_engine") or {}
            score = int(decision_info.get("trade_score") or 50)
            circuit_breaker = bool(decision_info.get("circuit_breaker_tripped"))

            # Store latest analysis
            state.setdefault("latest_analyses", {})
            state["latest_analyses"][symbol] = {
                "timestamp": _now_iso(),
                "score": score,
                "price": current_price,
                "indicators": {
                    "rsi": indicators.get("rsi"),
                    "sma20": indicators.get("sma20"),
                    "volatility": indicators.get("volatility"),
                    "pct_change_24h": pct_24h,
                },
                "circuit_breaker": circuit_breaker,
                "five_agents": intel.get("five_agents", {}),
            }

            # 3. Decision mapping
            if circuit_breaker:
                action = "SELL" if has_position else "HOLD"
            elif score >= buy_threshold:
                action = "BUY"
            elif score < sell_threshold:
                action = "SELL"
            else:
                action = "HOLD"

            # 4. Sizing and Execution
            portfolio_doc = await db.portfolios.find_one({"user_id": user_id}, {"_id": 0})
            cash = float(portfolio_doc.get("cash", allocated_capital)) if portfolio_doc else allocated_capital
            max_trade_usd = allocated_capital * MAX_POSITION_PCT

            if action == "BUY" and not has_position:
                buy_usd = min(max_trade_usd, cash)
                if buy_usd >= 10.0:
                    qty = buy_usd / current_price
                    cost = qty * current_price
                    fee = cost * FEE_RATE
                    needed = cost + fee

                    if needed <= cash:
                        new_cash = cash - needed
                        await db.positions.insert_one({
                            "user_id": user_id,
                            "symbol": symbol,
                            "quantity": qty,
                            "avg_price": current_price,
                        })
                        await db.portfolios.update_one({"user_id": user_id}, {"$set": {"cash": new_cash}}, upsert=True)

                        trade_doc = {
                            "id": str(uuid.uuid4()),
                            "user_id": user_id,
                            "symbol": symbol,
                            "side": "BUY",
                            "quantity": qty,
                            "price": current_price,
                            "fee": fee,
                            "realized_pnl": 0.0,
                            "cash_after": new_cash,
                            "created_at": _now_iso(),
                            "source": "continuous_ai",
                            "score": score,
                            "rationale": f"24/7 AI Engine: Score {score}/100 >= {buy_threshold} triggered BUY allocation.",
                        }
                        try:
                            await db.trades.insert_one(dict(trade_doc))
                        except Exception:
                            pass

                        _log_activity(
                            user_id,
                            f"🟢 AI BUY: {qty:.6f} {symbol} @ ${current_price:,.2f} (${buy_usd:,.2f}) — Score: {score}/100",
                            "buy",
                        )

            elif action == "SELL" and has_position:
                _log_activity(
                    user_id,
                    f"🔴 AI SELL: Score {score}/100 < {sell_threshold} triggered auto exit on {symbol}",
                    "sell",
                )
                await sell_position_now(db, user_id, symbol)

        except Exception as e:
            logger.error(f"Error in continuous trading cycle for {symbol}: {e}")


async def get_dashboard_data(db, user_id: str) -> Dict[str, Any]:
    state = _USER_STATES.get(user_id, {
        "status": "STOPPED",
        "allocated_capital": DEFAULT_CAPITAL,
        "symbols": DEFAULT_SYMBOLS,
        "interval_minutes": 5,
        "buy_threshold": 80,
        "sell_threshold": 40,
        "stop_loss_pct": STOP_LOSS_PCT,
        "take_profit_pct": TAKE_PROFIT_PCT,
        "activity_log": [],
        "latest_analyses": {},
    })

    portfolio_doc = await db.portfolios.find_one({"user_id": user_id}, {"_id": 0})
    cash = float(portfolio_doc.get("cash", state.get("allocated_capital", DEFAULT_CAPITAL))) if portfolio_doc else state.get("allocated_capital", DEFAULT_CAPITAL)

    positions = await db.positions.find({"user_id": user_id}, {"_id": 0}).to_list(100)

    invested = 0.0
    total_value = cash
    pos_data = []

    for pos in positions:
        sym = pos["symbol"]
        qty = float(pos.get("quantity", 0))
        avg = float(pos.get("avg_price", 0))

        current_price = avg
        latest_analysis = state.get("latest_analyses", {}).get(sym)
        if latest_analysis and latest_analysis.get("price"):
            current_price = float(latest_analysis["price"])
        else:
            # Fallback ticker check
            ticker = md.get_cached_ticker(sym)
            if ticker and ticker.get("price"):
                current_price = float(ticker["price"])

        val = qty * current_price
        invested += (qty * avg)
        total_value += val
        pnl = val - (qty * avg)
        pnl_pct = ((current_price - avg) / avg * 100.0) if avg > 0 else 0.0

        pos_data.append({
            "symbol": sym,
            "quantity": qty,
            "avg_price": avg,
            "current_price": current_price,
            "value": val,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })

    alloc_cap = float(state.get("allocated_capital", DEFAULT_CAPITAL))
    total_pnl = total_value - alloc_cap
    total_pnl_pct = (total_pnl / alloc_cap * 100.0) if alloc_cap > 0 else 0.0

    return {
        "ai_status": state.get("status", "STOPPED"),
        "portfolio": {
            "cash": cash,
            "total_value": total_value,
            "invested": invested,
            "pnl": total_pnl,
            "pnl_pct": total_pnl_pct,
            "allocated_capital": alloc_cap,
        },
        "positions": pos_data,
        "latest_analyses": state.get("latest_analyses", {}),
        "activity_log": state.get("activity_log", []),
        "config": {
            "interval_minutes": state.get("interval_minutes", 5),
            "symbols": state.get("symbols", DEFAULT_SYMBOLS),
            "buy_threshold": state.get("buy_threshold", 80),
            "sell_threshold": state.get("sell_threshold", 40),
            "stop_loss_pct": state.get("stop_loss_pct", STOP_LOSS_PCT),
            "take_profit_pct": state.get("take_profit_pct", TAKE_PROFIT_PCT),
        },
    }
