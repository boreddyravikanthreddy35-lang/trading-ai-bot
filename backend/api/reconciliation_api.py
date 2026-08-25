"""Reconciliation API — /api/reconciliation/*"""
from fastapi import APIRouter, HTTPException
import server
from services import reconciliation_service

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])

@router.post("/run")
async def trigger_reconciliation():
    """Trigger an on-demand full institutional financial audit."""
    db = server.db
    try:
        report = await reconciliation_service.run_reconciliation(db)
        return {"status": "ok", "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_summary():
    """Get latest reconciliation run status and open breaks."""
    db = server.db
    try:
        summary = await reconciliation_service.get_latest_reconciliation_summary(db)
        return {"status": "ok", **summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/breaks")
async def get_breaks(limit: int = 50, status: str = "OPEN"):
    """Get all reconciliation breaks."""
    db = server.db
    try:
        query = {}
        if status:
            query["status"] = status
        breaks = await db.reconciliation_breaks.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        return {"status": "ok", "breaks": breaks, "count": len(breaks)}
    except Exception as e:
        return {"status": "ok", "breaks": [], "count": 0}
