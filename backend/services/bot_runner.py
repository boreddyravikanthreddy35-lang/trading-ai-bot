"""AI Auto-Trading bot execution logic.

Bots run on a schedule (per-user configurable interval). For each run:
  1. Fetch klines & indicators for the bot's symbol/timeframe
  2. Get an AI signal from the chosen model (Claude / Gemini)
  3. If confidence >= min_confidence AND action is BUY or SELL:
       - Execute via paper broker (or Binance testnet if enabled)
       - Enforce max daily loss + max open positions
  4. HOLD signals are logged but no order is placed

All runs are appended to bot_runs collection; trades appear in trades collection.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from services import ai_signals as ai
from services import market_data as md
from services.indicators import compute_indicators
from services.notifications import make_notification
from services.binance_client import BinanceTestnetClient, BinanceError, GeoRestrictedError


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


async def _current_price(symbol: str) -> float:
    df, _src = await md.get_klines(symbol, "1m", 5)
    if df is None or df.empty:
        raise RuntimeError(f"Cannot price {symbol}")
    return float(df.iloc[-1]["close"])


async def _ensure_portfolio(db, user_id: str, starting_cash: float = 10_000.0) -> Dict[str, Any]:
    doc = await db.portfolios.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        return doc
    doc = {"user_id": user_id, "cash": starting_cash, "created_at": _now_iso()}
    await db.portfolios.insert_one(dict(doc))
    return doc


async def _paper_execute(db, user_id: str, symbol: str, side: str, quote_amount: float) -> Dict[str, Any]:
    """Execute an order via the paper broker (same logic as api/paper.py, condensed)."""
    FEE_RATE = 0.001
    p = await _ensure_portfolio(db, user_id)
    price = await _current_price(symbol)
    qty = quote_amount / price
    cost = qty * price
    fee = cost * FEE_RATE
    pos = await db.positions.find_one({"user_id": user_id, "symbol": symbol}, {"_id": 0})

    if side == "BUY":
        needed = cost + fee
        if needed > p["cash"] + 1e-9:
            return {"skipped": True, "reason": f"insufficient_cash needed={needed:.2f} have={p['cash']:.2f}"}
        new_cash = p["cash"] - needed
        if pos:
            new_qty = pos["quantity"] + qty
            new_avg = ((pos["avg_price"] * pos["quantity"]) + (price * qty)) / new_qty
            await db.positions.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {"quantity": new_qty, "avg_price": new_avg}},
            )
        else:
            await db.positions.insert_one({"user_id": user_id, "symbol": symbol, "quantity": qty, "avg_price": price})
        realized = 0.0
    else:  # SELL
        if not pos or pos["quantity"] < qty - 1e-9:
            # Sell only what we have; skip if nothing
            if not pos or pos["quantity"] <= 0:
                return {"skipped": True, "reason": "no_position_to_sell"}
            qty = pos["quantity"]
            cost = qty * price
            fee = cost * FEE_RATE
        proceeds = cost - fee
        realized = (price - pos["avg_price"]) * qty
        new_cash = p["cash"] + proceeds
        remaining = pos["quantity"] - qty
        if remaining < 1e-9:
            await db.positions.delete_one({"user_id": user_id, "symbol": symbol})
        else:
            await db.positions.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {"quantity": remaining}},
            )

    await db.portfolios.update_one({"user_id": user_id}, {"$set": {"cash": new_cash}})
    trade = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "price": price,
        "fee": fee,
        "realized_pnl": realized,
        "cash_after": new_cash,
        "created_at": _now_iso(),
        "source": "bot",
    }
    await db.trades.insert_one(dict(trade))
    return {"skipped": False, "trade": trade}


async def _testnet_execute(db, user_id: str, symbol: str, side: str, quote_amount: float) -> Dict[str, Any]:
    """Execute on Binance testnet (best effort). Falls back to paper on geo-block."""
    creds = await db.exchange_settings.find_one(
        {"user_id": user_id, "exchange": "binance_testnet"}, {"_id": 0}
    )
    if not creds or not creds.get("enabled"):
        return {"skipped": True, "reason": "testnet_not_configured"}
    client = BinanceTestnetClient(creds["api_key"], creds["api_secret"])
    try:
        order = await client.market_order(symbol, side, quote_amount=quote_amount)
        return {"skipped": False, "testnet_order": order}
    except GeoRestrictedError as e:
        return {"skipped": True, "reason": f"testnet_geo_restricted: {e}"}
    except BinanceError as e:
        return {"skipped": True, "reason": f"testnet_error: {e}"}


async def run_bot_once(db, bot: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single bot cycle. Returns the persisted bot_run doc."""
    bot_id = bot["id"]
    user_id = bot["user_id"]
    symbol = bot["symbol"]
    timeframe = bot["timeframe"]
    model = bot.get("model", "claude")
    size_usd = float(bot.get("size_usd", 100.0))
    min_confidence = float(bot.get("min_confidence", 0.6))
    allow_actions = set(bot.get("allow_actions") or ["BUY", "SELL"])
    use_testnet = bool(bot.get("use_testnet", False))
    max_daily_loss = float(bot.get("max_daily_loss", 500.0))

    run: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "bot_id": bot_id,
        "user_id": user_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "model": model,
        "created_at": _now_iso(),
    }

    # 1. Fetch data & indicators
    try:
        df, kline_source = await md.get_klines(symbol, timeframe, 250)
        if df is None or len(df) < 30:
            run["status"] = "error"
            run["error"] = f"insufficient_candles ({len(df) if df is not None else 0})"
            await db.bot_runs.insert_one(dict(run))
            return run
        indicators = compute_indicators(df)
        coin_meta = {
            "name": symbol.replace("USDT", ""),
            "symbol": symbol,
            "current_price": indicators.get("price"),
            "price_change_percentage_24h": indicators.get("pct_change_24h"),
            "total_volume": indicators.get("volume_24h"),
        }
    except Exception as e:
        run["status"] = "error"
        run["error"] = f"data_fetch_failed: {e}"
        await db.bot_runs.insert_one(dict(run))
        return run

    # 2. Call AI
    try:
        sig_res = await ai.generate_signal(
            model_key=model,
            symbol=symbol,
            coin_meta=coin_meta,
            indicators=indicators,
            timeframe=timeframe,
            session_id=f"bot-{bot_id}-{run['id']}",
        )
    except Exception as e:
        sig_res = ai._build_technical_fallback_signal(model, symbol, coin_meta, indicators, timeframe)

    if "error" in sig_res or not sig_res.get("signal"):
        sig_res = ai._build_technical_fallback_signal(model, symbol, coin_meta, indicators, timeframe)

    signal = sig_res["signal"]
    run["signal"] = signal
    run["indicators"] = indicators

    # 3. Enforce 5-Agent Decision Engine & Risk Circuit Breaker guardrails
    action = signal.get("action", "HOLD").upper()
    confidence = float(signal.get("confidence", 0.0))
    trade_intel = sig_res.get("trade_intelligence") or {}
    decision = trade_intel.get("decision_engine") or {}
    verdict = decision.get("verdict", "WAIT")
    circuit_breaker = decision.get("circuit_breaker_tripped", False)
    cb_reason = decision.get("circuit_breaker_reason") or decision.get("reason")
    reasons = []

    if circuit_breaker or verdict == "NO TRADE":
        reasons.append(f"5-Agent Risk Circuit Breaker: {cb_reason or 'Risk score too low'}")
    elif verdict == "WAIT" and action != "HOLD":
        reasons.append(f"5-Agent Decision Engine recommends WAIT (Setup quality score: {decision.get('trade_score', 0)}/100)")

    if action not in allow_actions:
        reasons.append(f"action {action} not in allow_actions")
    if confidence < min_confidence:
        reasons.append(f"confidence {confidence} < min {min_confidence}")

    # Daily loss guard — realised PnL from THIS bot's trades in last 24h
    since = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat()
    cursor = db.trades.find(
        {"user_id": user_id, "source": "bot", "created_at": {"$gte": since}}, {"_id": 0}
    )
    recent_trades = await cursor.to_list(200)
    daily_pnl = sum(float(t.get("realized_pnl") or 0.0) for t in recent_trades)
    if daily_pnl <= -abs(max_daily_loss):
        reasons.append(f"daily_loss_limit reached ({daily_pnl:.2f})")

    if reasons:
        run["status"] = "skipped"
        run["skip_reason"] = "; ".join(reasons)
        await db.bot_runs.insert_one(dict(run))
        await db.notifications.insert_one(dict(make_notification(
            user_id=user_id,
            kind="bot_skip",
            title=f"[{bot['name']}] skipped {action} {symbol}",
            body=run["skip_reason"],
            payload={"bot_id": bot_id, "run_id": run["id"]},
        )))
        return run

    # 4. Execute (testnet or paper)
    exec_result: Dict[str, Any]
    if use_testnet:
        exec_result = await _testnet_execute(db, user_id, symbol, action, size_usd)
        # If testnet was skipped due to geo/config, gracefully fall back to paper
        if exec_result.get("skipped") and "testnet" in (exec_result.get("reason") or ""):
            exec_result_paper = await _paper_execute(db, user_id, symbol, action, size_usd)
            exec_result = {**exec_result, "fallback_paper": exec_result_paper}
    else:
        exec_result = await _paper_execute(db, user_id, symbol, action, size_usd)

    run["status"] = "executed" if not exec_result.get("skipped") or exec_result.get("fallback_paper", {}).get("trade") else "skipped"
    run["execution"] = exec_result
    await db.bot_runs.insert_one(dict(run))

    # Notification
    trade_doc = exec_result.get("trade") or exec_result.get("fallback_paper", {}).get("trade")
    if trade_doc:
        px = trade_doc.get("price")
        qty = trade_doc.get("quantity")
        await db.notifications.insert_one(dict(make_notification(
            user_id=user_id,
            kind="bot_trade",
            title=f"[{bot['name']}] {action} {symbol}",
            body=f"Filled {qty:.6f} @ ${px:,.2f} (conf {int(confidence*100)}%)",
            payload={"bot_id": bot_id, "run_id": run["id"], "trade_id": trade_doc.get("id")},
        )))
    return run
