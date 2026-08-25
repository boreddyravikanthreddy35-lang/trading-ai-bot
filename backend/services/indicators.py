"""Technical indicators computed with pandas/numpy (no ta-lib dependency)."""
import numpy as np
import pandas as pd
from typing import Any, Dict


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.ewm(alpha=1 / period, adjust=False).mean()
    ma_down = down.ewm(alpha=1 / period, adjust=False).mean()
    rs = ma_up / ma_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _round(v, n=4):
    try:
        f = float(v)
        if np.isnan(f):
            return None
        return round(f, n)
    except Exception:
        return None


def compute_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    close = df["close"]
    df = df.copy()
    df["sma_20"] = sma(close, 20)
    df["sma_50"] = sma(close, 50)
    df["ema_12"] = ema(close, 12)
    df["ema_26"] = ema(close, 26)
    df["rsi_14"] = rsi(close, 14)
    macd_line, signal_line, hist = macd(close)
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = hist

    last = df.iloc[-1]

    volatility = _round(df["close"].pct_change().std() * (24**0.5), 4)

    result = {
        "price": _round(last["close"], 4),
        "close": _round(last["close"], 4),
        "sma_20": _round(last["sma_20"], 4),
        "sma20": _round(last["sma_20"], 4),
        "sma_50": _round(last["sma_50"], 4),
        "sma50": _round(last["sma_50"], 4),
        "ema_12": _round(last["ema_12"], 4),
        "ema12": _round(last["ema_12"], 4),
        "ema_26": _round(last["ema_26"], 4),
        "ema26": _round(last["ema_26"], 4),
        "rsi_14": _round(last["rsi_14"], 2),
        "rsi": _round(last["rsi_14"], 2),
        "RSI": _round(last["rsi_14"], 2),
        "macd": _round(last["macd"], 4),
        "macd_signal": _round(last["macd_signal"], 4),
        "macd_hist": _round(last["macd_hist"], 4),
        "volatility": volatility,
        "high_24h": _round(df["high"].tail(24).max(), 4),
        "low_24h": _round(df["low"].tail(24).min(), 4),
        "volume_24h": _round(df["volume"].tail(24).sum(), 2),
    }
    if len(df) > 25:
        result["pct_change_24h"] = _round(((last["close"] - df["close"].iloc[-25]) / df["close"].iloc[-25]) * 100, 3)
    return result


def compute_indicator_series(df: pd.DataFrame) -> Dict[str, Any]:
    """Return time-series arrays for chart overlays (SMA, EMA, RSI, MACD)."""
    df = df.copy()
    close = df["close"]
    df["sma_20"] = sma(close, 20)
    df["sma_50"] = sma(close, 50)
    df["ema_12"] = ema(close, 12)
    df["ema_26"] = ema(close, 26)
    df["rsi_14"] = rsi(close, 14)
    macd_line, signal_line, hist = macd(close)

    def pts(col):
        out = []
        for i, row in df.iterrows():
            v = row[col] if col in df.columns else None
            if pd.notna(v):
                out.append({"time": int(row["open_time"].timestamp()), "value": float(v)})
        return out

    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    return {
        "sma_20": pts("sma_20"),
        "sma_50": pts("sma_50"),
        "ema_12": pts("ema_12"),
        "ema_26": pts("ema_26"),
        "rsi_14": pts("rsi_14"),
        "macd": pts("macd"),
        "macd_signal": pts("macd_signal"),
    }
