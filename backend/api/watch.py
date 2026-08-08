"""Watchlists + Alerts endpoints."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services import market_data as md
from services.auth import current_user

router = APIRouter(prefix="/watch", tags=["watchlists"])


def _db():
    from server import db as _database
    return _database


class WatchlistCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    symbols: List[str] = Field(default_factory=list)


class WatchlistUpdate(BaseModel):
    name: Optional[str] = None
    symbols: Optional[List[str]] = None


class AlertCreate(BaseModel):
    symbol: str
    condition: str = Field(..., description="above | below")
    threshold: float


# ── Watchlists ─────────────────────────────────────────────────────────────

@router.get("/lists")
async def list_watchlists(user: Dict[str, Any] = Depends(current_user)):
    cursor = _db().watchlists.find({"user_id": user["id"]}, {"_id": 0})
    docs = await cursor.to_list(200)
    # Enrich with live prices
    all_syms = list({s for w in docs for s in (w.get("symbols") or [])})
    prices: Dict[str, float] = {}
    if all_syms:
        try:
            tickers, _src = await md.ticker_24hr(all_syms)
            for t in tickers:
                prices[t["symbol"]] = {
                    "price": float(t["lastPrice"]),
                    "change_pct": float(t["priceChangePercent"]),
                }
        except Exception:
            pass
    for w in docs:
        w["live"] = {s: prices.get(s) for s in (w.get("symbols") or [])}
    return {"watchlists": docs}


@router.post("/lists")
async def create_watchlist(req: WatchlistCreate, user: Dict[str, Any] = Depends(current_user)):
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": req.name,
        "symbols": list(dict.fromkeys(req.symbols)),  # dedupe
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    await _db().watchlists.insert_one(dict(doc))
    return doc


@router.patch("/lists/{watchlist_id}")
async def update_watchlist(watchlist_id: str, req: WatchlistUpdate, user: Dict[str, Any] = Depends(current_user)):
    update: Dict[str, Any] = {}
    if req.name is not None:
        update["name"] = req.name
    if req.symbols is not None:
        update["symbols"] = list(dict.fromkeys(req.symbols))
    if not update:
        raise HTTPException(status_code=400, detail="No fields to update")
    r = await _db().watchlists.update_one(
        {"id": watchlist_id, "user_id": user["id"]},
        {"$set": update},
    )
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    doc = await _db().watchlists.find_one({"id": watchlist_id}, {"_id": 0})
    return doc


@router.delete("/lists/{watchlist_id}")
async def delete_watchlist(watchlist_id: str, user: Dict[str, Any] = Depends(current_user)):
    r = await _db().watchlists.delete_one({"id": watchlist_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return {"status": "ok"}


# ── Alerts ─────────────────────────────────────────────────────────────────

@router.get("/alerts")
async def list_alerts(user: Dict[str, Any] = Depends(current_user)):
    cursor = _db().alerts.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    docs = await cursor.to_list(200)
    return {"alerts": docs}


@router.post("/alerts")
async def create_alert(req: AlertCreate, user: Dict[str, Any] = Depends(current_user)):
    if req.condition not in {"above", "below"}:
        raise HTTPException(status_code=400, detail="condition must be 'above' or 'below'")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "symbol": req.symbol,
        "condition": req.condition,
        "threshold": float(req.threshold),
        "triggered": False,
        "triggered_at": None,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    await _db().alerts.insert_one(dict(doc))
    return doc


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str, user: Dict[str, Any] = Depends(current_user)):
    r = await _db().alerts.delete_one({"id": alert_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "ok"}


@router.post("/alerts/check")
async def check_alerts(user: Dict[str, Any] = Depends(current_user)):
    """Evaluate all active alerts against current prices; mark triggered as needed."""
    alerts = await _db().alerts.find({"user_id": user["id"], "triggered": False}, {"_id": 0}).to_list(500)
    if not alerts:
        return {"triggered": [], "checked": 0}

    symbols = list({a["symbol"] for a in alerts})
    prices: Dict[str, float] = {}
    try:
        tickers, _src = await md.ticker_24hr(symbols)
        for t in tickers:
            prices[t["symbol"]] = float(t["lastPrice"])
    except Exception:
        for s in symbols:
            try:
                df, _ = await md.get_klines(s, "1m", 3)
                if not df.empty:
                    prices[s] = float(df.iloc[-1]["close"])
            except Exception:
                continue

    triggered: List[Dict[str, Any]] = []
    for a in alerts:
        p = prices.get(a["symbol"])
        if p is None:
            continue
        hit = (a["condition"] == "above" and p >= a["threshold"]) or \
              (a["condition"] == "below" and p <= a["threshold"])
        if hit:
            now = datetime.now(tz=timezone.utc).isoformat()
            await _db().alerts.update_one(
                {"id": a["id"]},
                {"$set": {"triggered": True, "triggered_at": now, "triggered_price": p}},
            )
            triggered.append({**a, "triggered": True, "triggered_at": now, "triggered_price": p})
    return {"triggered": triggered, "checked": len(alerts)}
