"""Strategy backtesting engine — SMA crossover, RSI, MACD strategies."""
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from services.indicators import ema, macd, rsi, sma


def _base_state(initial_cash: float, fee_rate: float):
    return {
        "cash": initial_cash,
        "position": 0.0,   # base asset qty
        "avg_price": 0.0,
        "trades": [],      # dicts of trades
        "equity_curve": [],
        "fee_rate": fee_rate,
    }


def _mark_to_market(state: Dict[str, Any], t, price: float):
    equity = state["cash"] + state["position"] * price
    state["equity_curve"].append({"time": int(t.timestamp()), "equity": round(equity, 2), "price": round(price, 4)})


def _buy(state: Dict[str, Any], t, price: float, size_pct: float = 1.0):
    if state["position"] > 0 or state["cash"] <= 0:
        return
    cash_to_use = state["cash"] * size_pct
    fee = cash_to_use * state["fee_rate"]
    qty = (cash_to_use - fee) / price
    state["position"] = qty
    state["avg_price"] = price
    state["cash"] -= cash_to_use
    state["trades"].append({
        "side": "BUY", "time": int(t.timestamp()), "price": round(price, 4),
        "qty": round(qty, 8), "fee": round(fee, 4), "pnl": None,
    })


def _sell(state: Dict[str, Any], t, price: float):
    if state["position"] <= 0:
        return
    proceeds = state["position"] * price
    fee = proceeds * state["fee_rate"]
    pnl = proceeds - fee - (state["position"] * state["avg_price"])
    state["cash"] += (proceeds - fee)
    state["trades"].append({
        "side": "SELL", "time": int(t.timestamp()), "price": round(price, 4),
        "qty": round(state["position"], 8), "fee": round(fee, 4), "pnl": round(pnl, 4),
    })
    state["position"] = 0.0
    state["avg_price"] = 0.0


def _metrics(state: Dict[str, Any], initial_cash: float, last_price: float) -> Dict[str, Any]:
    ending = state["cash"] + state["position"] * last_price
    ret_pct = (ending - initial_cash) / initial_cash * 100
    closed = [t for t in state["trades"] if t["pnl"] is not None]
    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]
    win_rate = (len(wins) / len(closed) * 100) if closed else 0.0
    total_pnl = sum(t["pnl"] for t in closed) if closed else 0.0
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0.0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0.0

    # Max drawdown
    equity_series = [row["equity"] for row in state["equity_curve"]]
    peak = -float("inf")
    max_dd = 0.0
    for e in equity_series:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return {
        "initial_cash": round(initial_cash, 2),
        "ending_equity": round(ending, 2),
        "return_pct": round(ret_pct, 3),
        "total_pnl": round(total_pnl, 2),
        "num_trades": len(closed),
        "win_rate_pct": round(win_rate, 2),
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "max_drawdown_pct": round(max_dd, 3),
    }


def run_sma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50, initial_cash: float = 10000.0, fee_rate: float = 0.001) -> Dict[str, Any]:
    df = df.copy()
    df["sma_fast"] = sma(df["close"], fast)
    df["sma_slow"] = sma(df["close"], slow)
    df.dropna(inplace=True)
    state = _base_state(initial_cash, fee_rate)

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        cur = df.iloc[i]
        t = cur["open_time"]
        price = float(cur["close"])
        # Golden cross → BUY
        if prev["sma_fast"] <= prev["sma_slow"] and cur["sma_fast"] > cur["sma_slow"]:
            _buy(state, t, price)
        # Death cross → SELL
        elif prev["sma_fast"] >= prev["sma_slow"] and cur["sma_fast"] < cur["sma_slow"]:
            _sell(state, t, price)
        _mark_to_market(state, t, price)

    last_price = float(df.iloc[-1]["close"]) if len(df) else 0
    metrics = _metrics(state, initial_cash, last_price)
    return {
        "strategy": "SMA Crossover",
        "params": {"fast": fast, "slow": slow},
        "metrics": metrics,
        "equity_curve": state["equity_curve"],
        "trades": state["trades"],
    }


def run_rsi_strategy(df: pd.DataFrame, period: int = 14, oversold: float = 30.0, overbought: float = 70.0,
                    initial_cash: float = 10000.0, fee_rate: float = 0.001) -> Dict[str, Any]:
    df = df.copy()
    df["rsi"] = rsi(df["close"], period)
    df.dropna(inplace=True)
    state = _base_state(initial_cash, fee_rate)

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        cur = df.iloc[i]
        t = cur["open_time"]
        price = float(cur["close"])
        # RSI crosses UP through oversold → BUY
        if prev["rsi"] < oversold and cur["rsi"] >= oversold:
            _buy(state, t, price)
        # RSI crosses DOWN through overbought → SELL
        elif prev["rsi"] > overbought and cur["rsi"] <= overbought:
            _sell(state, t, price)
        _mark_to_market(state, t, price)

    last_price = float(df.iloc[-1]["close"]) if len(df) else 0
    metrics = _metrics(state, initial_cash, last_price)
    return {
        "strategy": "RSI Mean Reversion",
        "params": {"period": period, "oversold": oversold, "overbought": overbought},
        "metrics": metrics,
        "equity_curve": state["equity_curve"],
        "trades": state["trades"],
    }


def run_macd_strategy(df: pd.DataFrame, initial_cash: float = 10000.0, fee_rate: float = 0.001) -> Dict[str, Any]:
    df = df.copy()
    macd_line, signal_line, hist = macd(df["close"])
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df.dropna(inplace=True)
    state = _base_state(initial_cash, fee_rate)

    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        cur = df.iloc[i]
        t = cur["open_time"]
        price = float(cur["close"])
        if prev["macd"] <= prev["macd_signal"] and cur["macd"] > cur["macd_signal"]:
            _buy(state, t, price)
        elif prev["macd"] >= prev["macd_signal"] and cur["macd"] < cur["macd_signal"]:
            _sell(state, t, price)
        _mark_to_market(state, t, price)

    last_price = float(df.iloc[-1]["close"]) if len(df) else 0
    metrics = _metrics(state, initial_cash, last_price)
    return {
        "strategy": "MACD Crossover",
        "params": {"fast": 12, "slow": 26, "signal": 9},
        "metrics": metrics,
        "equity_curve": state["equity_curve"],
        "trades": state["trades"],
    }


STRATEGIES = {
    "sma_crossover": run_sma_crossover,
    "rsi": run_rsi_strategy,
    "macd": run_macd_strategy,
}
