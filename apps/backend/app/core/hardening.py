"""Pagination + Idempotency-Key helpers — Spec Phase 10D."""

from __future__ import annotations

import hashlib
import json
import time
from threading import Lock
from typing import Any
from uuid import UUID

from fastapi import Header, HTTPException, Query, status
from pydantic import BaseModel, Field

# In-process idempotency cache (prod: Redis). TTL 24h conceptually; memory pruned.
_IDEMPOTENCY: dict[str, tuple[float, dict[str, Any]]] = {}
_IDEMP_LOCK = Lock()
_IDEMP_TTL_SEC = 24 * 3600


class PageParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


def pagination_params(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


def page_meta(*, total: int | None, limit: int, offset: int) -> dict[str, Any]:
    return {
        "limit": limit,
        "offset": offset,
        "total": total,
        "has_more": (total is not None and offset + limit < total),
    }


def _idem_key(user_id: str | UUID | None, key: str, path: str) -> str:
    raw = f"{user_id or 'anon'}:{path}:{key}"
    return hashlib.sha256(raw.encode()).hexdigest()


def idempotency_lookup(
    *,
    key: str | None,
    path: str,
    user_id: str | UUID | None = None,
) -> dict[str, Any] | None:
    if not key:
        return None
    cache_key = _idem_key(user_id, key, path)
    now = time.time()
    with _IDEMP_LOCK:
        hit = _IDEMPOTENCY.get(cache_key)
        if not hit:
            return None
        stored_at, payload = hit
        if now - stored_at > _IDEMP_TTL_SEC:
            _IDEMPOTENCY.pop(cache_key, None)
            return None
        return payload


def idempotency_store(
    *,
    key: str | None,
    path: str,
    payload: dict[str, Any],
    user_id: str | UUID | None = None,
) -> None:
    if not key:
        return
    cache_key = _idem_key(user_id, key, path)
    with _IDEMP_LOCK:
        # Opportunistic prune
        if len(_IDEMPOTENCY) > 5000:
            cutoff = time.time() - _IDEMP_TTL_SEC
            stale = [k for k, (ts, _) in _IDEMPOTENCY.items() if ts < cutoff]
            for k in stale[:1000]:
                _IDEMPOTENCY.pop(k, None)
        _IDEMPOTENCY[cache_key] = (time.time(), json.loads(json.dumps(payload, default=str)))


async def optional_idempotency_key(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> str | None:
    if idempotency_key is None:
        return None
    key = idempotency_key.strip()
    if not key:
        return None
    if len(key) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key too long (max 128)",
        )
    return key
