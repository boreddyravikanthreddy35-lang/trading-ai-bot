"""
Supabase (PostgreSQL) compatibility adapter for SignalForge.
Mimics the Motor/MongoDB async API used throughout the backend.
All blocking supabase-py calls are wrapped in asyncio.to_thread()
so the FastAPI event loop is never blocked.
Includes seamless in-memory fallback if any table has not yet been migrated in Supabase.
"""
import asyncio
import copy
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)

_BACKUP_FILE = os.path.join(os.path.dirname(__file__), "..", "db_local_backup.json")
_MEMORY_STORE: Dict[str, List[Dict[str, Any]]] = {}

def _load_memory_store():
    global _MEMORY_STORE
    try:
        if os.path.exists(_BACKUP_FILE):
            with open(_BACKUP_FILE, "r", encoding="utf-8") as f:
                _MEMORY_STORE = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load backup store: {e}")

def _save_memory_store():
    try:
        with open(_BACKUP_FILE, "w", encoding="utf-8") as f:
            json.dump(_MEMORY_STORE, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Failed to save backup store: {e}")

_load_memory_store()

def _get_mem_table(table: str) -> List[Dict[str, Any]]:
    if table not in _MEMORY_STORE:
        _MEMORY_STORE[table] = []
    return _MEMORY_STORE[table]

def _doc_matches(doc: Dict, filter_dict: Dict) -> bool:
    if not filter_dict:
        return True
    for k, v in filter_dict.items():
        if k == "_id":
            continue
        doc_val = doc.get(k)
        if isinstance(v, dict):
            for op, op_val in v.items():
                if op == "$eq" and doc_val != op_val:
                    return False
                elif op == "$ne" and doc_val == op_val:
                    return False
                elif op == "$gt" and (doc_val is None or doc_val <= op_val):
                    return False
                elif op == "$gte" and (doc_val is None or doc_val < op_val):
                    return False
                elif op == "$lt" and (doc_val is None or doc_val >= op_val):
                    return False
                elif op == "$lte" and (doc_val is None or doc_val > op_val):
                    return False
                elif op == "$in" and doc_val not in op_val:
                    return False
                elif op == "$regex":
                    pat = str(op_val).lstrip("^")
                    if not re.search(pat, str(doc_val or "")):
                        return False
        else:
            if doc_val != v:
                return False
    return True

class _WriteResult:
    def __init__(self, matched=0, modified=0, deleted=0, inserted=0, upserted=False):
        self.matched_count  = matched
        self.modified_count = modified
        self.deleted_count  = deleted
        self.inserted_count = inserted
        self.upserted_id    = "upserted" if upserted else None

def _apply_filters(query, filters: Dict):
    for key, value in (filters or {}).items():
        if key == "_id":
            continue
        if isinstance(value, dict):
            for op, operand in value.items():
                if op == "$eq":
                    query = query.eq(key, operand)
                elif op == "$ne":
                    query = query.neq(key, operand)
                elif op == "$gt":
                    query = query.gt(key, operand)
                elif op == "$gte":
                    query = query.gte(key, operand)
                elif op == "$lt":
                    query = query.lt(key, operand)
                elif op == "$lte":
                    query = query.lte(key, operand)
                elif op == "$in":
                    query = query.in_(key, operand)
                elif op == "$regex":
                    pat = operand.lstrip("^")
                    if not operand.endswith("$"):
                        pat += "%"
                    query = query.like(key, pat)
        else:
            if value is None:
                query = query.is_(key, "null")
            elif isinstance(value, bool):
                query = query.eq(key, value)
            else:
                query = query.eq(key, value)
    return query

def _clean_doc(doc: Dict) -> Dict:
    return {k: v for k, v in doc.items() if k != "_id"}

class SupabaseCursor:
    def __init__(self, client: Client, table: str, filters: Dict):
        self._client   = client
        self._table    = table
        self._filters  = filters or {}
        self._sort_col: Optional[str] = None
        self._sort_desc = True
        self._limit_val: Optional[int] = None

    def sort(self, key, direction=-1):
        self._sort_col  = key
        self._sort_desc = (direction == -1)
        return self

    def limit(self, n: int):
        self._limit_val = n
        return self

    def _build_and_run(self, cap: Optional[int] = None):
        rows = []
        try:
            query = self._client.table(self._table).select("*")
            query = _apply_filters(query, self._filters)
            if self._sort_col:
                query = query.order(self._sort_col, desc=self._sort_desc)
            lim = self._limit_val or cap
            if lim:
                query = query.limit(lim)
            result = query.execute()
            rows = result.data or []
        except Exception:
            pass

        # If remote returned empty, check in-memory store
        if not rows and self._table in _MEMORY_STORE:
            rows = [doc for doc in _get_mem_table(self._table) if _doc_matches(doc, self._filters)]
            if self._sort_col:
                rows.sort(key=lambda x: x.get(self._sort_col) or "", reverse=self._sort_desc)

        lim = self._limit_val or cap
        return rows[:lim] if lim else rows

    async def to_list(self, length: Optional[int] = None) -> List[Dict]:
        cap = self._limit_val or length
        return await asyncio.to_thread(self._build_and_run, cap)

    def __await__(self):
        return self.to_list().__await__()

class SupabaseCollection:
    def __init__(self, client: Client, table: str):
        self._client = client
        self._table  = table

    async def find_one(self, filter_dict: Dict, projection=None) -> Optional[Dict]:
        def _sync():
            try:
                query = self._client.table(self._table).select("*")
                query = _apply_filters(query, filter_dict)
                result = query.limit(1).execute()
                if result.data:
                    return result.data[0]
            except Exception:
                pass
            for doc in _get_mem_table(self._table):
                if _doc_matches(doc, filter_dict):
                    return copy.deepcopy(doc)
            return None
        return await asyncio.to_thread(_sync)

    def find(self, filter_dict: Dict = None, projection=None) -> SupabaseCursor:
        return SupabaseCursor(self._client, self._table, filter_dict or {})

    async def count_documents(self, filter_dict: Dict) -> int:
        def _sync():
            try:
                query = self._client.table(self._table).select("*", count="exact")
                query = _apply_filters(query, filter_dict)
                result = query.execute()
                if result.count is not None and result.count > 0:
                    return result.count
            except Exception:
                pass
            return sum(1 for doc in _get_mem_table(self._table) if _doc_matches(doc, filter_dict))
        return await asyncio.to_thread(_sync)

    async def insert_one(self, document: Dict) -> _WriteResult:
        doc = _clean_doc(document)
        def _sync():
            try:
                self._client.table(self._table).insert(doc).execute()
            except Exception:
                pass
            _get_mem_table(self._table).append(copy.deepcopy(doc))
            _save_memory_store()
            return _WriteResult(inserted=1)
        return await asyncio.to_thread(_sync)

    async def update_one(
        self,
        filter_dict: Dict,
        update_dict: Dict,
        upsert: bool = False,
    ) -> _WriteResult:
        if "$set" in update_dict:
            set_data = _clean_doc(update_dict["$set"])
        else:
            set_data = _clean_doc(update_dict)

        def _sync():
            matched = 0
            try:
                query = self._client.table(self._table).update(set_data)
                query = _apply_filters(query, filter_dict)
                result = query.execute()
                matched = len(result.data) if result.data else 0
            except Exception:
                pass

            tbl = _get_mem_table(self._table)
            mem_matched = False
            for doc in tbl:
                if _doc_matches(doc, filter_dict):
                    doc.update(copy.deepcopy(set_data))
                    mem_matched = True

            if mem_matched or matched > 0:
                _save_memory_store()
                return _WriteResult(matched=max(matched, 1), modified=max(matched, 1))

            if upsert:
                combined = {}
                for k, v in filter_dict.items():
                    if k != "_id" and not isinstance(v, dict):
                        combined[k] = v
                combined.update(copy.deepcopy(set_data))
                try:
                    self._client.table(self._table).insert(combined).execute()
                except Exception:
                    pass
                tbl.append(combined)
                _save_memory_store()
                return _WriteResult(matched=0, modified=0, inserted=1, upserted=True)
            return _WriteResult(matched=0, modified=0)

        return await asyncio.to_thread(_sync)

    async def update_many(self, filter_dict: Dict, update_dict: Dict) -> _WriteResult:
        if "$set" in update_dict:
            set_data = _clean_doc(update_dict["$set"])
        else:
            set_data = _clean_doc(update_dict)

        def _sync():
            try:
                query = self._client.table(self._table).update(set_data)
                query = _apply_filters(query, filter_dict)
                result = query.execute()
                count = len(result.data) if result.data else 0
                if count > 0:
                    return _WriteResult(matched=count, modified=count)
            except Exception:
                pass

            tbl = _get_mem_table(self._table)
            count = 0
            for doc in tbl:
                if _doc_matches(doc, filter_dict):
                    doc.update(copy.deepcopy(set_data))
                    count += 1
            if count > 0:
                _save_memory_store()
            return _WriteResult(matched=count, modified=count)

        return await asyncio.to_thread(_sync)

    async def delete_one(self, filter_dict: Dict) -> _WriteResult:
        def _sync():
            count = 0
            try:
                query = self._client.table(self._table).delete()
                query = _apply_filters(query, filter_dict)
                result = query.execute()
                count = len(result.data) if result.data else 0
            except Exception:
                pass

            tbl = _get_mem_table(self._table)
            for i, doc in enumerate(tbl):
                if _doc_matches(doc, filter_dict):
                    tbl.pop(i)
                    _save_memory_store()
                    return _WriteResult(deleted=1)
            return _WriteResult(deleted=count)
        return await asyncio.to_thread(_sync)

    async def delete_many(self, filter_dict: Dict) -> _WriteResult:
        def _sync():
            count = 0
            try:
                query = self._client.table(self._table).delete()
                if filter_dict:
                    query = _apply_filters(query, filter_dict)
                else:
                    query = query.neq("id", "00000000-0000-0000-0000-000000000000")
                result = query.execute()
                count = len(result.data) if result.data else 0
            except Exception:
                pass

            tbl = _get_mem_table(self._table)
            before = len(tbl)
            _MEMORY_STORE[self._table] = [d for d in tbl if not _doc_matches(d, filter_dict)]
            _save_memory_store()
            deleted = max(count, before - len(_MEMORY_STORE[self._table]))
            return _WriteResult(deleted=deleted)
        return await asyncio.to_thread(_sync)

class SupabaseDB:
    def __init__(self, client: Client):
        self._client = client

    def __getattr__(self, name: str) -> SupabaseCollection:
        return SupabaseCollection(self._client, name)

def create_db(url: str = None, key: str = None) -> SupabaseDB:
    url = url or os.environ.get("SUPABASE_URL", "")
    key = key or os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in backend/.env")
    client: Client = create_client(url, key)
    return SupabaseDB(client)
