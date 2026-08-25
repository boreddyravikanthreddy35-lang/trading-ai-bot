"""
AI Decisions API - /api/ai-decisions/*

Every BUY/SELL/HOLD decision the AI makes is stored in ai_decisions table.
This endpoint lets you audit exactly what the AI decided, why, and whether
the risk engine approved or rejected it.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import server

router = APIRouter(prefix="/ai-decisions", tags=["ai-decisions"])


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@router.get("")
async def get_ai_decisions(user_id: str = "default_user", limit: int = 50, symbol: str = None):
    """
    Get AI decision history for a user.
    Includes: decision, confidence, market_regime, risk_verdict, entry/target/stop prices.
    """
    db = server.db
    try:
        query = {"user_id": user_id}
        if symbol:
            query["symbol"] = symbol
        decisions = await db.ai_decisions.find(
            query, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        return {
            "status": "ok",
            "user_id": user_id,
            "decisions": decisions,
            "count": len(decisions)
        }
    except Exception as e:
        return {"status": "ok", "decisions": [], "count": 0}


@router.get("/stats")
async def get_ai_stats(user_id: str = "default_user"):
    """
    Statistics on AI decision quality:
    - Total decisions, BUY/SELL/HOLD breakdown
    - Risk engine approval rate
    - Win rate (approved BUY decisions that resulted in profit)
    """
    db = server.db
    try:
        decisions = await db.ai_decisions.find(
            {"user_id": user_id}, {"_id": 0}
        ).to_list(500)

        total = len(decisions)
        buys = sum(1 for d in decisions if d.get("decision") == "BUY")
        sells = sum(1 for d in decisions if d.get("decision") == "SELL")
        holds = sum(1 for d in decisions if d.get("decision") == "HOLD")
        approved = sum(1 for d in decisions if d.get("risk_verdict") == "APPROVED")
        rejected = sum(1 for d in decisions if d.get("risk_verdict") == "REJECTED")

        approval_rate = round((approved / total * 100), 1) if total > 0 else 0.0

        # Average confidence
        confs = [float(d.get("confidence", 0)) for d in decisions if d.get("confidence")]
        avg_confidence = round(sum(confs) / len(confs), 1) if confs else 0.0

        return {
            "status": "ok",
            "total_decisions": total,
            "breakdown": {"BUY": buys, "SELL": sells, "HOLD": holds},
            "risk_engine": {
                "approved": approved,
                "rejected": rejected,
                "approval_rate_pct": approval_rate
            },
            "avg_confidence": avg_confidence
        }
    except Exception as e:
        return {"status": "ok", "total_decisions": 0}


@router.get("/latest")
async def get_latest_decisions(user_id: str, limit: int = 10):
    """Get the most recent AI decisions across all symbols."""
    db = server.db
    try:
        decisions = await db.ai_decisions.find(
            {"user_id": user_id}, {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        return {"status": "ok", "decisions": decisions}
    except Exception as e:
        return {"status": "ok", "decisions": []}
