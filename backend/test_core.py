"""
POC Test Script for AI Crypto Trading Platform
==============================================
Validates the CORE workflow end-to-end:
  1. Fetch real-time market data from CoinGecko (top coins, prices, market cap)
  2. Fetch OHLCV historical candles from Binance public API
  3. Compute technical indicators (RSI, MACD, SMA, EMA) with pandas/numpy
  4. Build market context payload
  5. Call Claude Sonnet 4.5 → get structured BUY/SELL/HOLD signal (strict JSON)
  6. Call Gemini 2.5 Pro → get structured signal (strict JSON)
  7. Compare & validate outputs

Run:  cd /app/backend && python3 test_core.py
"""

import asyncio
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

import httpx
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

# ─── Emergent LLM ──────────────────────────────────────────────────────────
from emergentintegrations.llm.chat import LlmChat, UserMessage

load_dotenv()
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# ─── Constants ─────────────────────────────────────────────────────────────
COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BINANCE_BASE = "https://api.binance.com/api/v3"
BYBIT_BASE = "https://api.bybit.com/v5"
KRAKEN_BASE = "https://api.kraken.com/0/public"
KUCOIN_BASE = "https://api.kucoin.com/api/v1"

# CoinGecko id -> unified symbol map (BTC/USDT style)
SYMBOL_MAP = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
}

# Bybit interval mapping (Binance uses "1h", Bybit uses "60")
BYBIT_INTERVAL_MAP = {
    "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720",
    "1d": "D", "1w": "W", "1M": "M",
}

# Kraken interval in minutes
KRAKEN_INTERVAL_MAP = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "4h": 240, "1d": 1440, "1w": 10080,
}

# KuCoin type strings
KUCOIN_INTERVAL_MAP = {
    "1m": "1min", "3m": "3min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1hour", "2h": "2hour", "4h": "4hour", "6h": "6hour", "8h": "8hour",
    "12h": "12hour", "1d": "1day", "1w": "1week",
}

# Kraken symbol renaming (BTC → XBT, and Kraken uses e.g. XBTUSDT)
def to_kraken_pair(unified: str) -> str:
    # BTCUSDT → XBTUSDT ; ETHUSDT stays ETHUSDT
    if unified.startswith("BTC"):
        return "XBT" + unified[3:]
    return unified


def to_kucoin_pair(unified: str) -> str:
    # BTCUSDT → BTC-USDT
    if unified.endswith("USDT"):
        return unified[:-4] + "-USDT"
    return unified

CLAUDE_MODEL = ("anthropic", "claude-sonnet-4-5-20250929")
GEMINI_MODEL = ("gemini", "gemini-2.5-pro")

# ═══════════════════════════════════════════════════════════════════════════
#   Market Data Fetchers
# ═══════════════════════════════════════════════════════════════════════════

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (crypto-ai-poc/1.0)",
    "Accept": "application/json",
}


async def _get_json_with_retries(url: str, params: Dict[str, Any], attempts: int = 4) -> Any:
    """GET with exponential backoff, handling 429 gracefully."""
    async with httpx.AsyncClient(timeout=25.0, headers=HTTP_HEADERS) as client:
        last_exc = None
        for i in range(attempts):
            try:
                r = await client.get(url, params=params)
                if r.status_code == 429:
                    # respect Retry-After if present, else exp backoff
                    retry_after = float(r.headers.get("Retry-After", 2 ** (i + 1)))
                    await asyncio.sleep(min(retry_after, 15))
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_exc = e
                await asyncio.sleep(1.5 * (i + 1))
        raise last_exc if last_exc else RuntimeError(f"failed GET {url}")


async def fetch_coingecko_markets(vs_currency: str = "usd", per_page: int = 10) -> List[Dict[str, Any]]:
    """Top N coins by market cap with 24h stats (CoinGecko)."""
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }
    return await _get_json_with_retries(url, params, attempts=4)


async def fetch_binance_ticker_24hr(symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """24-hour rolling stats from Binance for all or specific symbols. Very high rate-limit."""
    url = f"{BINANCE_BASE}/ticker/24hr"
    params: Dict[str, Any] = {}
    if symbols:
        params["symbols"] = json.dumps(symbols)
    data = await _get_json_with_retries(url, params, attempts=4)
    if isinstance(data, dict):
        return [data]
    return data


async def fetch_bybit_ticker_24hr(symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """24-hour rolling stats from Bybit (spot). Returns list normalized to Binance-like keys."""
    url = f"{BYBIT_BASE}/market/tickers"
    params = {"category": "spot"}
    data = await _get_json_with_retries(url, params, attempts=4)
    rows = data.get("result", {}).get("list", []) if isinstance(data, dict) else []
    if symbols:
        rows = [r for r in rows if r.get("symbol") in set(symbols)]
    # Normalize to Binance-style keys used later
    norm = []
    for r in rows:
        norm.append({
            "symbol": r.get("symbol"),
            "lastPrice": r.get("lastPrice"),
            "priceChangePercent": (float(r.get("price24hPcnt", 0)) * 100),
            "quoteVolume": r.get("turnover24h", "0"),
            "highPrice": r.get("highPrice24h"),
            "lowPrice": r.get("lowPrice24h"),
        })
    return norm


async def fetch_bybit_klines(symbol: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
    """OHLCV candles from Bybit (spot)."""
    bybit_interval = BYBIT_INTERVAL_MAP.get(interval, "60")
    url = f"{BYBIT_BASE}/market/kline"
    params = {"category": "spot", "symbol": symbol, "interval": bybit_interval, "limit": min(limit, 1000)}
    data = await _get_json_with_retries(url, params, attempts=4)
    rows = data.get("result", {}).get("list", []) if isinstance(data, dict) else []
    # Bybit returns newest-first — reverse to oldest-first
    rows = list(reversed(rows))
    # Row: [start, open, high, low, close, volume, turnover]
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume", "turnover"])
    if df.empty:
        return df
    df["open_time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["close_time"] = df["open_time"]  # bybit doesn't provide close_time explicitly
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


async def fetch_kraken_ticker_24hr(symbols: List[str]) -> List[Dict[str, Any]]:
    """24hr stats from Kraken."""
    pairs = [to_kraken_pair(s) for s in symbols]
    url = f"{KRAKEN_BASE}/Ticker"
    params = {"pair": ",".join(pairs)}
    data = await _get_json_with_retries(url, params, attempts=3)
    result = data.get("result", {}) if isinstance(data, dict) else {}
    norm: List[Dict[str, Any]] = []
    for kraken_pair, stats in result.items():
        # last price c[0], 24h open o, volume in base v[1], high h[1], low l[1]
        last = float(stats["c"][0])
        open24 = float(stats.get("o", last))
        pct = ((last - open24) / open24 * 100) if open24 else 0.0
        # Map back to unified symbol (XBTUSDT -> BTCUSDT)
        unified = kraken_pair.replace("XBT", "BTC")
        norm.append({
            "symbol": unified,
            "lastPrice": last,
            "priceChangePercent": pct,
            "quoteVolume": float(stats["v"][1]) * last,
            "highPrice": float(stats["h"][1]),
            "lowPrice": float(stats["l"][1]),
        })
    return norm


async def fetch_kucoin_ticker_24hr(symbols: List[str]) -> List[Dict[str, Any]]:
    """24hr stats from KuCoin (per symbol)."""
    norm: List[Dict[str, Any]] = []
    for s in symbols:
        k_symbol = to_kucoin_pair(s)
        url = f"{KUCOIN_BASE}/market/stats"
        data = await _get_json_with_retries(url, {"symbol": k_symbol}, attempts=3)
        d = data.get("data", {}) if isinstance(data, dict) else {}
        if not d:
            continue
        last = float(d.get("last", 0))
        pct = float(d.get("changeRate", 0)) * 100
        norm.append({
            "symbol": s,
            "lastPrice": last,
            "priceChangePercent": pct,
            "quoteVolume": float(d.get("volValue", 0)),
            "highPrice": float(d.get("high", 0)),
            "lowPrice": float(d.get("low", 0)),
        })
    return norm


async def fetch_ticker_24hr(symbols: List[str]) -> tuple[List[Dict[str, Any]], str]:
    """
    Ticker with cascading fallback:
      Binance → Bybit → Kraken → KuCoin
    """
    sources = [
        ("binance", fetch_binance_ticker_24hr),
        ("bybit", fetch_bybit_ticker_24hr),
        ("kraken", fetch_kraken_ticker_24hr),
        ("kucoin", fetch_kucoin_ticker_24hr),
    ]
    last_exc = None
    for name, fn in sources:
        if name in _FAILED_SOURCES:
            continue
        try:
            data = await fn(symbols)
            if data:
                return data, name
        except Exception as e:
            last_exc = e
            msg = str(e)
            if any(code in msg for code in ["451", "403"]):
                _FAILED_SOURCES.add(name)
            continue
    raise last_exc if last_exc else RuntimeError("All ticker sources failed")


async def fetch_kraken_klines(symbol: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
    """OHLCV candles from Kraken."""
    k_interval = KRAKEN_INTERVAL_MAP.get(interval, 60)
    k_pair = to_kraken_pair(symbol)
    url = f"{KRAKEN_BASE}/OHLC"
    params = {"pair": k_pair, "interval": k_interval}
    data = await _get_json_with_retries(url, params, attempts=3)
    if not isinstance(data, dict) or data.get("error"):
        raise RuntimeError(f"Kraken error: {data.get('error') if isinstance(data, dict) else data}")
    result = data.get("result", {})
    rows = []
    for key, value in result.items():
        if key == "last":
            continue
        rows = value
        break
    if not rows:
        return pd.DataFrame()
    # row: [time, open, high, low, close, vwap, volume, count]
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "vwap", "volume", "count"])
    df["open_time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="s")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["close_time"] = df["open_time"]
    # Trim to requested limit (Kraken can return up to 720)
    df = df.tail(limit).reset_index(drop=True)
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


async def fetch_kucoin_klines(symbol: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
    """OHLCV candles from KuCoin."""
    k_type = KUCOIN_INTERVAL_MAP.get(interval, "1hour")
    k_symbol = to_kucoin_pair(symbol)
    url = f"{KUCOIN_BASE}/market/candles"
    params = {"symbol": k_symbol, "type": k_type}
    data = await _get_json_with_retries(url, params, attempts=3)
    rows = data.get("data", []) if isinstance(data, dict) else []
    if not rows:
        return pd.DataFrame()
    # KuCoin returns newest-first; row: [time, open, close, high, low, volume, turnover]
    rows = list(reversed(rows))
    df = pd.DataFrame(rows, columns=["open_time", "open", "close", "high", "low", "volume", "turnover"])
    df["open_time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="s")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["close_time"] = df["open_time"]
    df = df.tail(limit).reset_index(drop=True)
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


# Track which sources have failed at runtime so we don't keep retrying them
_FAILED_SOURCES: set = set()


async def fetch_klines(symbol: str, interval: str = "1h", limit: int = 200) -> tuple[pd.DataFrame, str]:
    """
    Fetch OHLCV klines with cascading fallbacks:
      Binance → Bybit → Kraken → KuCoin
    Returns (df, source_name). Remembers permanent failures for the process lifetime.
    """
    sources = [
        ("binance", _fetch_binance_klines_raw),
        ("bybit", fetch_bybit_klines),
        ("kraken", fetch_kraken_klines),
        ("kucoin", fetch_kucoin_klines),
    ]
    last_exc = None
    for name, fn in sources:
        if name in _FAILED_SOURCES:
            continue
        try:
            df = await fn(symbol, interval, limit)
            if df is not None and len(df) > 0:
                return df, name
        except Exception as e:
            last_exc = e
            # Geo-block / permanent failure → don't retry this source
            msg = str(e)
            if any(code in msg for code in ["451", "403"]):
                _FAILED_SOURCES.add(name)
            continue
    raise last_exc if last_exc else RuntimeError("All kline sources failed")


async def _fetch_binance_klines_raw(symbol: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
    url = f"{BINANCE_BASE}/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    data = await _get_json_with_retries(url, params, attempts=2)
    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "taker_base", "taker_quote", "ignore",
    ]
    df = pd.DataFrame(data, columns=cols)
    numeric = ["open", "high", "low", "close", "volume"]
    df[numeric] = df[numeric].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


# Kept for backwards-compat naming; delegates to unified fetch_klines
async def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 200) -> pd.DataFrame:
    df, _src = await fetch_klines(symbol, interval, limit)
    return df


# ═══════════════════════════════════════════════════════════════════════════
#   Technical Indicators (pandas/numpy — no ta-lib)
# ═══════════════════════════════════════════════════════════════════════════

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


def compute_indicators(df: pd.DataFrame) -> Dict[str, float]:
    close = df["close"]
    df["sma_20"] = close.rolling(20).mean()
    df["sma_50"] = close.rolling(50).mean()
    df["ema_12"] = close.ewm(span=12, adjust=False).mean()
    df["ema_26"] = close.ewm(span=26, adjust=False).mean()
    df["rsi_14"] = rsi(close, 14)
    macd_line, signal_line, hist = macd(close)
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_hist"] = hist

    last = df.iloc[-1]
    prev = df.iloc[-2]

    def _round(x, n=4):
        try:
            v = float(x)
            if np.isnan(v):
                return None
            return round(v, n)
        except Exception:
            return None

    return {
        "price": _round(last["close"], 2),
        "prev_close": _round(prev["close"], 2),
        "sma_20": _round(last["sma_20"], 2),
        "sma_50": _round(last["sma_50"], 2),
        "ema_12": _round(last["ema_12"], 2),
        "ema_26": _round(last["ema_26"], 2),
        "rsi_14": _round(last["rsi_14"], 2),
        "macd": _round(last["macd"], 4),
        "macd_signal": _round(last["macd_signal"], 4),
        "macd_hist": _round(last["macd_hist"], 4),
        "high_24h": _round(df["high"].tail(24).max(), 2),
        "low_24h": _round(df["low"].tail(24).min(), 2),
        "volume_24h": _round(df["volume"].tail(24).sum(), 2),
        "pct_change_24h": _round(((last["close"] - df["close"].iloc[-25]) / df["close"].iloc[-25]) * 100, 3) if len(df) > 25 else None,
    }


# ═══════════════════════════════════════════════════════════════════════════
#   LLM Signal Generation
# ═══════════════════════════════════════════════════════════════════════════

class TradingSignal(BaseModel):
    action: str = Field(..., description="BUY | SELL | HOLD")
    confidence: float = Field(..., ge=0.0, le=1.0)
    time_horizon: str = Field(..., description="short|medium|long")
    reasoning: str
    key_factors: List[str]
    indicator_summary: str
    risk_level: str = Field(..., description="low|medium|high")
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


SYSTEM_PROMPT = """You are an expert crypto quantitative analyst.
Given real market data and technical indicators for a cryptocurrency,
produce a concise trading signal.

You MUST respond with a SINGLE valid JSON object matching this exact schema
(no markdown, no code fences, no commentary outside JSON):

{
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0.0-1.0,
  "time_horizon": "short" | "medium" | "long",
  "reasoning": "2-3 sentences explaining the recommendation",
  "key_factors": ["factor 1", "factor 2", "factor 3"],
  "indicator_summary": "1-2 sentences summarizing technicals (RSI, MACD, SMA position)",
  "risk_level": "low" | "medium" | "high",
  "entry_price": <number or null>,
  "stop_loss": <number or null>,
  "take_profit": <number or null>
}

Rules:
- Confidence is 0.0-1.0 (e.g., 0.72).
- If RSI > 70 lean SELL, RSI < 30 lean BUY, otherwise consider MACD/SMA cross.
- Never respond with anything except the JSON object.
- Numbers are plain numbers (no strings, no % signs, no $).
"""


def build_user_prompt(symbol: str, coin_meta: Dict[str, Any], indicators: Dict[str, Any], timeframe: str) -> str:
    return f"""Analyze {symbol} on the {timeframe} timeframe and issue a trading signal.

Coin metadata:
- name: {coin_meta.get('name')}
- symbol: {coin_meta.get('symbol')}
- market_cap_rank: {coin_meta.get('market_cap_rank')}
- current_price_usd: {coin_meta.get('current_price')}
- 24h_change_pct: {coin_meta.get('price_change_percentage_24h')}
- 24h_volume_usd: {coin_meta.get('total_volume')}

Technical indicators (last close):
{json.dumps(indicators, indent=2)}

Return ONLY the JSON signal object per the schema."""


def extract_json_block(text: str) -> Optional[str]:
    """Robustly extract the first JSON object from an LLM response."""
    if not text:
        return None
    text = text.strip()
    # If wrapped in ```json ... ``` — strip fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)
    # Fallback: first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return None


async def call_llm_signal(provider: str, model: str, session_id: str, user_prompt: str) -> Dict[str, Any]:
    """Call an LLM and return validated TradingSignal dict, or {'error':..., 'raw':...}."""
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=SYSTEM_PROMPT,
    ).with_model(provider, model)

    last_err = None
    raw = ""
    for attempt in range(2):
        try:
            raw = await chat.send_message(UserMessage(text=user_prompt))
            block = extract_json_block(raw) or raw
            data = json.loads(block)
            signal = TradingSignal(**data)
            return signal.model_dump()
        except (json.JSONDecodeError, ValidationError) as e:
            last_err = f"{type(e).__name__}: {e}"
            # Re-ask with correction hint
            user_prompt = (
                "Your previous reply was not valid JSON matching the required schema.\n"
                f"Error: {last_err}\n"
                "Return ONLY a single JSON object exactly matching the schema, "
                "no markdown, no fences.\n\n"
                + user_prompt
            )
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            break
    return {"error": last_err, "raw": raw[:800] if raw else ""}


# ═══════════════════════════════════════════════════════════════════════════
#   Orchestrator — End-to-End POC
# ═══════════════════════════════════════════════════════════════════════════

async def run_poc():
    print("=" * 78)
    print(" AI CRYPTO TRADING — CORE WORKFLOW POC ")
    print("=" * 78)

    assert EMERGENT_LLM_KEY, "EMERGENT_LLM_KEY missing from environment"
    print(f"[env] EMERGENT_LLM_KEY loaded (len={len(EMERGENT_LLM_KEY)})\n")

    # ── User Story 1: CoinGecko top markets (with Binance fallback) ────────
    print("── [1] Market overview: CoinGecko primary + Binance fallback ─────")
    t0 = time.time()
    markets = []
    cg_ok = False
    try:
        markets = await fetch_coingecko_markets(per_page=10)
        cg_ok = True
        print(f"   [CoinGecko] fetched {len(markets)} coins in {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"   [CoinGecko] failed ({type(e).__name__}: {str(e)[:120]}) — falling back to Binance ticker")

    if not cg_ok:
        # Cascading ticker fetch: Binance → Bybit → Kraken → KuCoin
        bn_syms = list(SYMBOL_MAP.values())
        tickers, src = await fetch_ticker_24hr(bn_syms)
        bn_to_cg = {v: k for k, v in SYMBOL_MAP.items()}
        markets = []
        for t in tickers:
            cg_id = bn_to_cg.get(t["symbol"], t["symbol"].lower())
            markets.append({
                "id": cg_id,
                "symbol": t["symbol"].replace("USDT", "").lower(),
                "name": cg_id.title(),
                "market_cap_rank": None,
                "current_price": float(t["lastPrice"]),
                "price_change_percentage_24h": float(t["priceChangePercent"]),
                "total_volume": float(t["quoteVolume"]),
            })
        print(f"   [{src}] built {len(markets)} synthetic market rows in {time.time()-t0:.2f}s")

    for m in markets[:5]:
        cp = m.get('current_price') or 0
        pct = m.get('price_change_percentage_24h') or 0
        print(f"   • {m['symbol'].upper():<6} {m['name']:<14} ${cp:<12}  24h: {pct:+.2f}%")
    assert len(markets) >= 3, "Both CoinGecko and Binance ticker failed"

    # ── User Story 2: Klines for 3 symbols (Binance → Bybit fallback) ──────
    print("\n── [2] OHLCV klines (1h, 200 bars) — Binance → Bybit fallback ────")
    klines = {}
    kline_src = "unknown"
    for cg_id, bn_sym in SYMBOL_MAP.items():
        df, kline_src = await fetch_klines(bn_sym, "1h", 200)
        klines[bn_sym] = df
        print(f"   [{kline_src}] {bn_sym}: {len(df)} bars  last_close=${df.iloc[-1]['close']:.2f}")
        assert len(df) >= 100, f"Only {len(df)} bars for {bn_sym} (need ≥100)"

    # ── User Story 3: Indicators ───────────────────────────────────────────
    print("\n── [3] Technical Indicators (RSI/MACD/SMA/EMA) ───────────────────")
    indicators_map = {}
    for sym, df in klines.items():
        ind = compute_indicators(df)
        indicators_map[sym] = ind
        print(f"   {sym}: RSI={ind['rsi_14']}  MACD={ind['macd']}  SMA20={ind['sma_20']}  SMA50={ind['sma_50']}")
        assert ind["rsi_14"] is not None, f"RSI None for {sym}"

    # ── User Stories 4 & 5: LLM signals from BOTH models for each symbol ───
    print("\n── [4/5] LLM Signals — Claude Sonnet 4.5  vs  Gemini 2.5 Pro ─────")
    coin_lookup = {m["id"]: m for m in markets}
    results = []

    for cg_id, bn_sym in SYMBOL_MAP.items():
        coin_meta = coin_lookup.get(cg_id, {"name": cg_id, "symbol": cg_id})
        user_prompt = build_user_prompt(bn_sym, coin_meta, indicators_map[bn_sym], "1h")

        print(f"\n   ── {bn_sym} ────────────────────────────────────────────────")
        session_base = f"poc-{bn_sym}-{int(time.time())}"

        # Claude
        t0 = time.time()
        claude_sig = await call_llm_signal(
            provider=CLAUDE_MODEL[0], model=CLAUDE_MODEL[1],
            session_id=f"{session_base}-claude",
            user_prompt=user_prompt,
        )
        dt_c = time.time() - t0

        # Gemini
        t0 = time.time()
        gemini_sig = await call_llm_signal(
            provider=GEMINI_MODEL[0], model=GEMINI_MODEL[1],
            session_id=f"{session_base}-gemini",
            user_prompt=user_prompt,
        )
        dt_g = time.time() - t0

        # Print comparison
        def _fmt(sig, dt):
            if "error" in sig:
                return f"      ERROR ({dt:.2f}s): {sig['error']}\n      raw: {sig.get('raw','')[:200]}"
            return (
                f"      action={sig['action']:<4} conf={sig['confidence']:.2f}  "
                f"horizon={sig['time_horizon']}  risk={sig['risk_level']}  ({dt:.2f}s)\n"
                f"      key_factors: {sig['key_factors']}\n"
                f"      reasoning: {sig['reasoning'][:180]}"
            )

        print(f"   Claude Sonnet 4.5:")
        print(_fmt(claude_sig, dt_c))
        print(f"   Gemini 2.5 Pro:")
        print(_fmt(gemini_sig, dt_g))

        results.append({
            "symbol": bn_sym,
            "claude": claude_sig,
            "gemini": gemini_sig,
        })

    # ── Final assertions ──────────────────────────────────────────────────
    print("\n" + "=" * 78)
    ok_claude = sum(1 for r in results if "error" not in r["claude"])
    ok_gemini = sum(1 for r in results if "error" not in r["gemini"])
    total = len(results)
    print(f" RESULTS: Claude {ok_claude}/{total}   Gemini {ok_gemini}/{total}")
    print("=" * 78)

    assert ok_claude == total, f"Claude failed on {total - ok_claude} symbol(s)"
    assert ok_gemini == total, f"Gemini failed on {total - ok_gemini} symbol(s)"
    print("\n POC PASSED — Core workflow validated end-to-end. Ready to build the app.\n")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(run_poc())
        sys.exit(0)
    except AssertionError as ae:
        print(f"\n POC FAILED — {ae}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n POC ERROR — {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(2)
