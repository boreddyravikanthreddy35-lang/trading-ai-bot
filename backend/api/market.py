"""Market data endpoints: overview, coin detail, klines."""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from services import market_data as md
from services.indicators import compute_indicators, compute_indicator_series

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/overview")
async def overview(per_page: int = 25):
    """Top N coins by market cap with sparklines and 24h stats."""
    try:
        data = await md.coingecko_markets(per_page=per_page)
        return {"source": "coingecko", "coins": data}
    except Exception:
        # Fallback: synth from ticker cascade
        try:
            symbols = list(md.DEFAULT_SYMBOLS.values())[:per_page]
            tickers, src = await md.ticker_24hr(symbols)
            bn_to_cg = {v: k for k, v in md.DEFAULT_SYMBOLS.items()}
            coins = []
            for t in tickers:
                cg_id = bn_to_cg.get(t["symbol"], t["symbol"].lower())
                coins.append({
                    "id": cg_id,
                    "symbol": t["symbol"].replace("USDT", "").lower(),
                    "name": cg_id.title().replace("-", " "),
                    "image": None,
                    "current_price": float(t["lastPrice"]),
                    "market_cap": None,
                    "market_cap_rank": None,
                    "total_volume": float(t["quoteVolume"]),
                    "price_change_percentage_24h": float(t["priceChangePercent"]),
                    "price_change_percentage_1h_in_currency": None,
                    "price_change_percentage_7d_in_currency": None,
                    "sparkline_in_7d": {"price": []},
                })
            return {"source": src, "coins": coins}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Market data unavailable: {e}")


@router.get("/coin/{coin_id}")
async def coin_detail(coin_id: str):
    """Detailed metadata for a coin from CoinGecko."""
    try:
        data = await md.coingecko_coin(coin_id)
        # Trim payload
        md_ = data.get("market_data", {}) or {}
        return {
            "id": data.get("id"),
            "symbol": data.get("symbol"),
            "name": data.get("name"),
            "image": (data.get("image") or {}).get("large"),
            "description": (data.get("description") or {}).get("en", "")[:600],
            "market_cap_rank": data.get("market_cap_rank"),
            "current_price": (md_.get("current_price") or {}).get("usd"),
            "market_cap": (md_.get("market_cap") or {}).get("usd"),
            "total_volume": (md_.get("total_volume") or {}).get("usd"),
            "price_change_percentage_24h": md_.get("price_change_percentage_24h"),
            "price_change_percentage_7d": md_.get("price_change_percentage_7d"),
            "price_change_percentage_30d": md_.get("price_change_percentage_30d"),
            "high_24h": (md_.get("high_24h") or {}).get("usd"),
            "low_24h": (md_.get("low_24h") or {}).get("usd"),
            "ath": (md_.get("ath") or {}).get("usd"),
            "atl": (md_.get("atl") or {}).get("usd"),
            "homepage": (data.get("links") or {}).get("homepage", [None])[0],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Coin detail unavailable: {e}")


@router.get("/klines")
async def klines(
    symbol: str = Query(..., description="e.g. BTCUSDT"),
    interval: str = "1h",
    limit: int = 300,
    with_indicators: bool = False,
):
    try:
        df, source = await md.get_klines(symbol, interval, limit)
        candles = md.klines_to_records(df)
        payload = {
            "source": source,
            "symbol": symbol,
            "interval": interval,
            "candles": candles,
        }
        if with_indicators and len(df) >= 30:
            payload["indicators"] = compute_indicators(df)
            payload["indicator_series"] = compute_indicator_series(df)
        return payload
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Klines unavailable: {e}")


@router.get("/symbols")
async def supported_symbols():
    """List of supported trading pairs."""
    return {
        "symbols": [
            {"symbol": v, "coingecko_id": k, "base": v.replace("USDT", ""), "quote": "USDT"}
            for k, v in md.DEFAULT_SYMBOLS.items()
        ]
    }


@router.get("/movers")
async def movers(direction: str = "gainers", limit: int = 5):
    """Top gainers / losers from CoinGecko overview."""
    try:
        data = await md.coingecko_markets(per_page=100)
    except Exception:
        raise HTTPException(status_code=502, detail="Market data unavailable")
    sorted_data = sorted(
        [d for d in data if d.get("price_change_percentage_24h") is not None],
        key=lambda x: x["price_change_percentage_24h"],
        reverse=(direction == "gainers"),
    )
    return {"direction": direction, "coins": sorted_data[:limit]}
