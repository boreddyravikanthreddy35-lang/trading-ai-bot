"""
Idempotency Service — Protects financial mutations against network retries and duplicate submissions.
Ensures identical requests execute exactly once and subsequent requests receive the cached response.
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()

def hash_payload(payload: Any) -> str:
    """Generate SHA256 deterministic hash of request payload."""
    try:
        serialized = json.dumps(payload, sort_keys=True, default=str)
    except Exception:
        serialized = str(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

async def check_and_lock(db, key: str, user_id: str, endpoint: str, payload: Any = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Check if idempotency key exists.
    Returns (can_proceed: bool, cached_result: Optional[Dict]).
    If can_proceed is True, a lock record is inserted with status 'PROCESSING'.
    If False and cached_result exists, caller should return cached_result.
    If False and status == 'PROCESSING', concurrent request in flight.
    """
    if not key:
        return True, None

    req_hash = hash_payload(payload)
    record = await db.idempotency_keys.find_one({"key": key})

    if record:
        if record.get("status") == "COMPLETED":
            return False, {
                "idempotent": True,
                "status_code": record.get("response_code", 200),
                "data": record.get("response_body", {}),
            }
        elif record.get("status") == "PROCESSING":
            # Another request with this key is already executing
            return False, {
                "idempotent": True,
                "in_flight": True,
                "status_code": 409,
                "data": {"detail": "Concurrent request with this Idempotency-Key is already in flight."},
            }

    # Acquire lock
    lock_doc = {
        "id": str(uuid.uuid4()),
        "key": key,
        "user_id": user_id,
        "endpoint": endpoint,
        "request_hash": req_hash,
        "response_code": None,
        "response_body": None,
        "status": "PROCESSING",
        "created_at": _now(),
    }
    await db.idempotency_keys.insert_one(lock_doc)
    return True, None

async def save_response(db, key: str, status_code: int, response_data: Any) -> None:
    """Commit response body into idempotency key record upon successful execution."""
    if not key:
        return
    try:
        await db.idempotency_keys.update_one(
            {"key": key},
            {"$set": {
                "status": "COMPLETED",
                "response_code": status_code,
                "response_body": response_data,
                "completed_at": _now(),
            }}
        )
    except Exception as e:
        print(f"[idempotency_service] Failed to save response for key {key}: {e}")

async def release_lock_on_failure(db, key: str, error_msg: str = "") -> None:
    """Release or mark failed so user can retry."""
    if not key:
        return
    try:
        await db.idempotency_keys.update_one(
            {"key": key},
            {"$set": {
                "status": "FAILED",
                "error": error_msg,
                "failed_at": _now(),
            }}
        )
    except Exception:
        pass
