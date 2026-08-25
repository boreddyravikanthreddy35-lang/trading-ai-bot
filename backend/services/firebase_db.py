"""Firebase Firestore database adapter for local and hosted deployments.

This module provides a minimal Firestore-backed replacement for the MongoDB
collection API used throughout the backend. It is designed to be used when
Firebase credentials are available via environment variables.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except Exception:  # pragma: no cover - optional dependency in local dev
    firebase_admin = None
    credentials = None
    firestore = None


class FirestoreCursor:
    def __init__(self, collection, filter: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        self._collection = collection
        self._filter = filter or {}
        self._projection = projection or {}
        self._limit: Optional[int] = None
        self._sort_key: Optional[str] = None
        self._sort_desc = False

    def sort(self, key: str, direction: int = 1):
        self._sort_key = key
        self._sort_desc = direction != 1
        return self

    def limit(self, value: int):
        self._limit = value
        return self

    async def to_list(self, length: Optional[int] = None) -> List[Dict[str, Any]]:
        docs = await self._collection._find_matching(self._filter, projection=self._projection)
        if self._sort_key:
            docs = sorted(
                docs,
                key=lambda item: item.get(self._sort_key, "") or "",
                reverse=self._sort_desc,
            )
        if self._limit is not None:
            docs = docs[: self._limit]
        if length is not None:
            docs = docs[:length]
        return docs


class FirestoreCollection:
    def __init__(self, db: "FirestoreDB", name: str):
        self._db = db
        self._name = name
        self._collection = db._client.collection(name)

    def find(self, filter: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        return FirestoreCursor(self, filter=filter, projection=projection)

    async def find_one(self, filter: Optional[Dict[str, Any]] = None, projection: Optional[Dict[str, Any]] = None):
        docs = await self._find_matching(filter or {}, projection=projection)
        return docs[0] if docs else None

    async def insert_one(self, document: Dict[str, Any]):
        payload = dict(document)
        payload.pop("_id", None)
        doc_id = str(payload.pop("id", "") or "")
        if not doc_id:
            ref = self._collection.document()
            doc_id = ref.id
            payload["id"] = doc_id
            await asyncio.to_thread(ref.set, payload)
            return type("InsertOneResult", (), {"inserted_id": doc_id})()

        ref = self._collection.document(doc_id)
        await asyncio.to_thread(ref.set, payload)
        return type("InsertOneResult", (), {"inserted_id": doc_id})()

    async def update_one(self, filter: Dict[str, Any], update: Dict[str, Any]):
        doc = await self.find_one(filter)
        if not doc:
            return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0})()

        payload = dict(doc)
        payload.pop("id", None)
        set_data = update.get("$set", {}) if isinstance(update, dict) else {}
        for key, value in set_data.items():
            payload[key] = value
        payload["id"] = doc["id"]
        ref = self._collection.document(doc["id"])
        await asyncio.to_thread(ref.set, payload)
        return type("UpdateResult", (), {"matched_count": 1, "modified_count": 1})()

    async def count_documents(self, filter: Optional[Dict[str, Any]] = None):
        docs = await self._find_matching(filter or {})
        return len(docs)

    async def _find_matching(self, filter: Dict[str, Any], projection: Optional[Dict[str, Any]] = None):
        docs = await asyncio.to_thread(self._read_all_documents)
        if not filter:
            filtered = docs
        else:
            filtered = []
            for item in docs:
                if self._matches(item, filter):
                    filtered.append(item)
        if projection:
            filtered = [self._project(item, projection) for item in filtered]
        return filtered

    def _read_all_documents(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for doc in self._collection.stream():
            data = doc.to_dict() or {}
            data["id"] = doc.id
            result.append(data)
        return result

    def _project(self, item: Dict[str, Any], projection: Dict[str, Any]) -> Dict[str, Any]:
        projected: Dict[str, Any] = {}
        for key, include in projection.items():
            if key == "_id":
                continue
            if include:
                projected[key] = item.get(key)
        return projected

    def _matches(self, item: Dict[str, Any], filter: Dict[str, Any]) -> bool:
        for key, expected in filter.items():
            if isinstance(expected, dict):
                if "$ne" in expected and item.get(key) == expected["$ne"]:
                    return False
                if "$exists" in expected and (key in item) != expected["$exists"]:
                    return False
                continue
            if item.get(key) != expected:
                return False
        return True


class FirestoreDB:
    def __init__(self, client):
        self._client = client

    def __getattr__(self, name: str) -> FirestoreCollection:
        return FirestoreCollection(self, name)


def _load_credentials():
    if firebase_admin is None or credentials is None or firestore is None:
        raise RuntimeError("firebase-admin is not installed")

    credentials_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if credentials_json:
        payload = json.loads(credentials_json)
        return credentials.Certificate(payload)

    credentials_path = os.environ.get("FIREBASE_CREDENTIALS_FILE")
    if credentials_path:
        return credentials.Certificate(credentials_path)

    project_id = os.environ.get("FIREBASE_PROJECT_ID")
    if project_id:
        return credentials.ApplicationDefault()

    raise RuntimeError("No Firebase credentials configured")


def create_db():
    if firebase_admin is None:
        raise RuntimeError("firebase-admin is not installed")

    if not firebase_admin._apps:
        cred = _load_credentials()
        firebase_admin.initialize_app(cred)

    # Support named Firestore databases (non-default)
    database_id = os.environ.get("FIREBASE_DATABASE_ID")
    if database_id:
        client = firestore.client(database_id=database_id)
    else:
        client = firestore.client()
    return FirestoreDB(client)
