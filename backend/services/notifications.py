"""In-app notification service."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def make_notification(
    user_id: str,
    kind: str,
    title: str,
    body: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "kind": kind,  # alert | bot_trade | system
        "title": title,
        "body": body,
        "payload": payload or {},
        "read": False,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
