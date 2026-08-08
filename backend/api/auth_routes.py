"""Auth API — email/password signup, login, me, Google OAuth (session-based)."""
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from services.auth import (
    create_access_token,
    current_user,
    hash_password,
    new_user_id,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _db():
    from server import db as _database
    return _database


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=200)
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleOAuthRequest(BaseModel):
    session_id: str = Field(..., description="Emergent OAuth session_id from URL fragment")


def _serialize_user(u: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": u["id"],
        "email": u["email"],
        "name": u.get("name"),
        "provider": u.get("provider", "email"),
        "picture": u.get("picture"),
        "created_at": u.get("created_at"),
    }


@router.post("/signup")
async def signup(req: SignupRequest):
    email = req.email.lower().strip()
    existing = await _db().users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "id": new_user_id(),
        "email": email,
        "name": req.name or email.split("@")[0],
        "password_hash": hash_password(req.password),
        "provider": "email",
        "picture": None,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    await _db().users.insert_one(dict(user))
    token = create_access_token(user["id"], user["email"])
    return {"user": _serialize_user(user), "token": token}


@router.post("/login")
async def login(req: LoginRequest):
    email = req.email.lower().strip()
    user = await _db().users.find_one({"email": email}, {"_id": 0})
    if not user or user.get("provider") != "email" or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(user["id"], user["email"])
    return {"user": _serialize_user(user), "token": token}


@router.post("/google")
async def google_oauth(req: GoogleOAuthRequest):
    """
    Emergent Managed Google OAuth:
    Frontend redirects the user to https://auth.emergentagent.com/?redirect=<preview_url>
    After successful login, user comes back with #session_id=<id> in the URL fragment.
    Frontend extracts that and POSTs it here to complete sign-in.
    """
    if not req.session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": req.session_id},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Failed to validate session: {e}")

    email = (data.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Google session missing email")

    user = await _db().users.find_one({"email": email}, {"_id": 0})
    if not user:
        user = {
            "id": new_user_id(),
            "email": email,
            "name": data.get("name") or email.split("@")[0],
            "password_hash": None,
            "provider": "google",
            "picture": data.get("picture"),
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        await _db().users.insert_one(dict(user))
    else:
        # Update picture/name if missing
        updates: Dict[str, Any] = {}
        if not user.get("picture") and data.get("picture"):
            updates["picture"] = data["picture"]
        if not user.get("name") and data.get("name"):
            updates["name"] = data["name"]
        if updates:
            await _db().users.update_one({"id": user["id"]}, {"$set": updates})
            user.update(updates)

    token = create_access_token(user["id"], user["email"])
    return {"user": _serialize_user(user), "token": token}


@router.get("/me")
async def me(user: Dict[str, Any] = Depends(current_user)):
    doc = await _db().users.find_one({"id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(doc)
