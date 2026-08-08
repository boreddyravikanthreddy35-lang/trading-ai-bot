"""
Market Data Service — Cascading exchange fallback (Binance → Bybit → Kraken → KuCoin)
plus CoinGecko for market overview & metadata.
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
import pandas as pd

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BINANCE_BASE = "https://api.binance.com/api/v3"
BYBIT_BASE = "https://api.bybit.com/v5"
KRAKEN_BASE = "https://api.kraken.com/0/public"
KUCOIN_BASE = "https://api.kucoin.com/api/v1"

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (crypto-ai/1.0)",
    "Accept": "application/json",
}

# Popular symbols we support out of the box. UI can add more.
DEFAULT_SYMBOLS: Dict[str, str] = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "binancecoin": "BNBUSDT",
    "ripple": "XRPUSDT",
    "cardano": "ADAUSDT",
    "dogecoin": "DOGEUSDT",
    "avalanche-2": "AVAXUSDT",
    "polkadot": "DOTUSDT",
    "chainlink": "LINKUSDT",
    "polygon-ecosystem-token": "MATICUSDT",
    "litecoin": "LTCUSDT",
}

SYMBOL_TO_COINGECKO = {v: k for k, v in DEFAULT_SYMBOLS.items()}

# Interval maps
BYBIT_INTERVAL = {
    "1m": "1", "5m": "5", "15m": "15", "30m": "30",
    "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720",
    "1d": "D", "1w": "W",
}
KRAKEN_INTERVAL = {
    "1m": 1, "5m": 5, "15m": 15, "30m": 30,
    "1h": 60, "4h": 240, "1d": 1440, "1w": 10080,
}
KUCOIN_INTERVAL = {
    "1m": "1min", "5m": "5min", "15m": "15min", "30m": "30min",
    "1h": "1hour", "2h": "2hour", "4h": "4hour", "6h": "6hour", "12h": "12hour",
    "1d": "1day", "1w": "1week",
}

_FAILED_SOURCES: set = set()


def to_kraken_pair(unified: str) -> str:
    if unified.startswith("BTC"):
        return "XBT" + unified[3:]
    return unified


def to_kucoin_pair(unified: str) -> str:
    if unified.endswith("USDT"):
        return unified[:-4] + "-USDT"
    return unified


# ─── HTTP with retries + 429 backoff ───────────────────────────────────────

async def _get_json(url: str, params: Dict[str, Any], attempts: int = 3, timeout: float = 20.0) -> Any:
    async with httpx.AsyncClient(timeout=timeout, headers=HTTP_HEADERS) as client:
        last_exc: Optional[Exception] = None
        for i in range(attempts):
            try:
                r = await client.get(url, params=params)
                if r.status_code == 429:
                    retry_after = float(r.headers.get("Retry-After", 2 ** (i + 1)))
                    await asyncio.sleep(min(retry_after, 12))
                    continue
                r.raise_for_status()
                return r.json()
            except Exception as e:
                last_exc = e
                await asyncio.sleep(1.0 * (i + 1))
        raise last_exc if last_exc else RuntimeError(f"GET {url} failed")


# ─── TTL Cache ─────────────────────────────────────────────────────────────

class TTLCache:
    def __init__(self):
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str):
        entry = self._store.get(key)
        if not entry:
            return None
        exp, val = entry
        if exp < time.time():
            self._store.pop(key, None)
            return None
        return val

    def set(self, key: str, value: Any, ttl: float):
        self._store[key] = (time.time() + ttl, value)

_CACHE = TTLCache()


# ─── CoinGecko ─────────────────────────────────────────────────────────────

async def coingecko_markets(vs_currency: str = "usd", per_page: int = 25) -> List[Dict[str, Any]]:
    key = f"cg-markets:{vs_currency}:{per_page}"
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    url = f"{COINGECKO_BASE}/coins/markets"
    params = {
        "vs_currency": vs_currency,
        "order": "market_cap_desc",
        "per_page": per_page,
        "page": 1,
        "sparkline": "true",
        "price_change_percentage": "1h,24h,7d",
    }
    data = await _get_json(url, params, attempts=3)
    _CACHE.set(key, data, ttl=45)
    return data


async def coingecko_coin(coin_id: str) -> Dict[str, Any]:
    key = f"cg-coin:{coin_id}"
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    url = f"{COINGECKO_BASE}/coins/{coin_id}"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    }
    data = await _get_json(url, params, attempts=2)
    _CACHE.set(key, data, ttl=120)
    return data


# ─── Tickers (24h stats) ───────────────────────────────────────────────────

async def binance_ticker_24hr(symbols: List[str]) -> List[Dict[str, Any]]:
    url = f"{BINANCE_BASE}/ticker/24hr"
    params = {"symbols": json.dumps(symbols)}
    data = await _get_json(url, params, attempts=2)
    if isinstance(data, dict):
        return [data]
    return data


async def bybit_ticker_24hr(symbols: List[str]) -> List[Dict[str, Any]]:
    url = f"{BYBIT_BASE}/market/tickers"
    data = await _get_json(url, {"category": "spot"}, attempts=2)
    rows = data.get("result", {}).get("list", []) if isinstance(data, dict) else []
    filt = [r for r in rows if r.get("symbol") in set(symbols)]
    return [{
        "symbol": r["symbol"],
        "lastPrice": r.get("lastPrice", "0"),
        "priceChangePercent": float(r.get("price24hPcnt", 0)) * 100,
        "quoteVolume": r.get("turnover24h", "0"),
        "highPrice": r.get("highPrice24h", "0"),
        "lowPrice": r.get("lowPrice24h", "0"),
    } for r in filt]


async def kraken_ticker_24hr(symbols: List[str]) -> List[Dict[str, Any]]:
    pairs = [to_kraken_pair(s) for s in symbols]
    url = f"{KRAKEN_BASE}/Ticker"
    data = await _get_json(url, {"pair": ",".join(pairs)}, attempts=2)
    result = data.get("result", {}) if isinstance(data, dict) else {}
    norm: List[Dict[str, Any]] = []
    for k, s in result.items():
        last = float(s["c"][0])
        open24 = float(s.get("o", last))
        pct = ((last - open24) / open24 * 100) if open24 else 0.0
        unified = k.replace("XBT", "BTC")
        norm.append({
            "symbol": unified,
            "lastPrice": last,
            "priceChangePercent": pct,
            "quoteVolume": float(s["v"][1]) * last,
            "highPrice": float(s["h"][1]),
            "lowPrice": float(s["l"][1]),
        })
    return norm


async def kucoin_ticker_24hr(symbols: List[str]) -> List[Dict[str, Any]]:
    norm: List[Dict[str, Any]] = []
    for s in symbols:
        try:
            data = await _get_json(f"{KUCOIN_BASE}/market/stats", {"symbol": to_kucoin_pair(s)}, attempts=2)
            d = data.get("data", {}) if isinstance(data, dict) else {}
            if not d or not d.get("last"):
                continue
            norm.append({
                "symbol": s,
                "lastPrice": d.get("last", "0"),
                "priceChangePercent": float(d.get("changeRate", 0)) * 100,
                "quoteVolume": d.get("volValue", "0"),
                "highPrice": d.get("high", "0"),
                "lowPrice": d.get("low", "0"),
            })
        except Exception:
            continue
    return norm


async def ticker_24hr(symbols: List[str]) -> Tuple[List[Dict[str, Any]], str]:
    cache_key = f"ticker:{','.join(sorted(symbols))}"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    sources = [
        ("binance", binance_ticker_24hr),
        ("bybit", bybit_ticker_24hr),
        ("kraken", kraken_ticker_24hr),
        ("kucoin", kucoin_ticker_24hr),
    ]
    last_exc = None
    for name, fn in sources:
        if name in _FAILED_SOURCES:
            continue
        try:
            data = await fn(symbols)
            if data:
                _CACHE.set(cache_key, (data, name), ttl=20)
                return data, name
        except Exception as e:
            last_exc = e
            msg = str(e)
            if any(code in msg for code in ["451", "403"]):
                _FAILED_SOURCES.add(name)
    raise last_exc if last_exc else RuntimeError("All ticker sources failed")


# ─── Klines (OHLCV) ────────────────────────────────────────────────────────

async def binance_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    url = f"{BINANCE_BASE}/klines"
    data = await _get_json(url, {"symbol": symbol, "interval": interval, "limit": limit}, attempts=2)
    cols = ["open_time", "open", "high", "low", "close", "volume", "close_time",
            "qav", "num_trades", "taker_base", "taker_quote", "ignore"]
    df = pd.DataFrame(data, columns=cols)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


async def bybit_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    bi = BYBIT_INTERVAL.get(interval, "60")
    data = await _get_json(f"{BYBIT_BASE}/market/kline",
                           {"category": "spot", "symbol": symbol, "interval": bi, "limit": min(limit, 1000)}, attempts=2)
    rows = list(reversed(data.get("result", {}).get("list", []) if isinstance(data, dict) else []))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume", "turnover"])
    df["open_time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="ms")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["close_time"] = df["open_time"]
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


async def kraken_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    ki = KRAKEN_INTERVAL.get(interval, 60)
    data = await _get_json(f"{KRAKEN_BASE}/OHLC", {"pair": to_kraken_pair(symbol), "interval": ki}, attempts=2)
    if data.get("error"):
        raise RuntimeError(f"Kraken: {data['error']}")
    result = data.get("result", {})
    rows: List[Any] = []
    for k, v in result.items():
        if k == "last":
            continue
        rows = v
        break
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "vwap", "volume", "count"])
    df["open_time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="s")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["close_time"] = df["open_time"]
    df = df.tail(limit).reset_index(drop=True)
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


async def kucoin_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    ki = KUCOIN_INTERVAL.get(interval, "1hour")
    data = await _get_json(f"{KUCOIN_BASE}/market/candles", {"symbol": to_kucoin_pair(symbol), "type": ki}, attempts=2)
    rows = data.get("data", []) if isinstance(data, dict) else []
    if not rows:
        return pd.DataFrame()
    rows = list(reversed(rows))
    df = pd.DataFrame(rows, columns=["open_time", "open", "close", "high", "low", "volume", "turnover"])
    df["open_time"] = pd.to_datetime(df["open_time"].astype(np.int64), unit="s")
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    df["close_time"] = df["open_time"]
    df = df.tail(limit).reset_index(drop=True)
    return df[["open_time", "open", "high", "low", "close", "volume", "close_time"]]


async def get_klines(symbol: str, interval: str = "1h", limit: int = 200) -> Tuple[pd.DataFrame, str]:
    """Cascading fallback for OHLCV: Binance → Bybit → Kraken → KuCoin."""
    cache_key = f"kl:{symbol}:{interval}:{limit}"
    cached = _CACHE.get(cache_key)
    if cached is not None:
        df, src = cached
        return df, src
    sources = [
        ("binance", binance_klines),
        ("bybit", bybit_klines),
        ("kraken", kraken_klines),
        ("kucoin", kucoin_klines),
    ]
    last_exc = None
    for name, fn in sources:
        if name in _FAILED_SOURCES:
            continue
        try:
            df = await fn(symbol, interval, limit)
            if df is not None and len(df) > 0:
                # cache short-lived so charts stay fresh
                _CACHE.set(cache_key, (df, name), ttl=15)
                return df, name
        except Exception as e:
            last_exc = e
            msg = str(e)
            if any(code in msg for code in ["451", "403"]):
                _FAILED_SOURCES.add(name)
    raise last_exc if last_exc else RuntimeError("All kline sources failed")


def klines_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    out = []
    for _, row in df.iterrows():
        out.append({
            "time": int(row["open_time"].timestamp()),  # seconds — lightweight-charts convention
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        })
    return out
