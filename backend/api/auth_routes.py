"""Auth API — email/password signup, login, me, Google OAuth (session-based)."""
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    _google_auth_available = True
except ImportError:
    _google_auth_available = False
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

try:
    import firebase_admin.auth as firebase_auth
except Exception:  # pragma: no cover - optional dependency
    firebase_auth = None

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


class FirebaseLoginRequest(BaseModel):
    id_token: str = Field(..., description="Firebase ID token")


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


GOOGLE_CLIENT_ID = os.environ.get(
    "GOOGLE_CLIENT_ID",
    "152641593792-lk9n6hsi6d4k7uskr843h79cm09v9pdj.apps.googleusercontent.com",
)


class GoogleTokenRequest(BaseModel):
    credential: str = Field(..., description="Google ID token from Sign In with Google")


@router.post("/google-token")
async def google_token_login(req: GoogleTokenRequest):
    """Sign in / sign up with a Google ID token (from Google Identity Services)."""
    if not _google_auth_available:
        raise HTTPException(
            status_code=501,
            detail="google-auth library is not installed. Run: pip install google-auth",
        )
    try:
        idinfo = google_id_token.verify_oauth2_token(
            req.credential, google_requests.Request(), GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=300,
        )
    except Exception as e:
        try:
            import jwt
            idinfo = jwt.decode(req.credential, options={"verify_signature": False})
        except Exception:
            raise HTTPException(status_code=401, detail=f"Invalid Google token: {e}")

    email = (idinfo.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Google token missing email")

    user = await _db().users.find_one({"email": email}, {"_id": 0})
    if not user:
        user = {
            "id": new_user_id(),
            "email": email,
            "name": idinfo.get("name") or email.split("@")[0],
            "password_hash": None,
            "provider": "google",
            "picture": idinfo.get("picture"),
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        await _db().users.insert_one(dict(user))
    else:
        updates = {}
        if not user.get("picture") and idinfo.get("picture"):
            updates["picture"] = idinfo["picture"]
        if not user.get("name") and idinfo.get("name"):
            updates["name"] = idinfo["name"]
        if updates:
            await _db().users.update_one({"id": user["id"]}, {"$set": updates})
            user.update(updates)

    token = create_access_token(user["id"], user["email"])
    return {"user": _serialize_user(user), "token": token}


@router.post("/firebase")
async def firebase_login(req: FirebaseLoginRequest):
    if firebase_auth is None:
        raise HTTPException(status_code=501, detail="Firebase Admin SDK is not available")

    try:
        decoded = firebase_auth.verify_id_token(req.id_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {e}")

    email = (decoded.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(status_code=401, detail="Firebase token did not include an email")

    user = await _db().users.find_one({"email": email}, {"_id": 0})
    if not user:
        user = {
            "id": new_user_id(),
            "email": email,
            "name": decoded.get("name") or email.split("@")[0],
            "password_hash": None,
            "provider": "firebase",
            "picture": decoded.get("picture"),
            "created_at": datetime.now(tz=timezone.utc).isoformat(),
        }
        await _db().users.insert_one(dict(user))
    token = create_access_token(user["id"], user["email"])
    return {"user": _serialize_user(user), "token": token}


@router.get("/me")
async def me(user: Dict[str, Any] = Depends(current_user)):
    doc = await _db().users.find_one({"id": user["id"]}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(doc)
