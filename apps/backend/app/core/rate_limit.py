"""Login rate limiting — Spec Phase 10C (5 attempts / minute / IP)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

# In-memory fallback (per-process). Redis preferred when available.
_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()

DEFAULT_LIMIT = 5
DEFAULT_WINDOW_SEC = 60.0


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def check_rate_limit(
    key: str,
    *,
    limit: int = DEFAULT_LIMIT,
    window_sec: float = DEFAULT_WINDOW_SEC,
) -> None:
    """Raise 429 if `key` exceeded `limit` hits inside `window_sec`."""
    now = time.monotonic()
    with _lock:
        q = _buckets[key]
        while q and now - q[0] > window_sec:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts — try again in a minute",
                headers={"Retry-After": str(int(window_sec))},
            )
        q.append(now)


async def enforce_login_rate(request: Request) -> None:
    """FastAPI dependency for POST /auth/login."""
    from app.core.config import settings

    if settings.environment.lower() in {"development", "dev", "local", "test"}:
        return

    ip = client_ip(request)
    window_sec = float(getattr(settings, "login_rate_window_sec", DEFAULT_WINDOW_SEC) or DEFAULT_WINDOW_SEC)
    limit = int(getattr(settings, "login_rate_limit", DEFAULT_LIMIT) or DEFAULT_LIMIT)
    # Prefer Redis sliding window when broker is up
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        if redis is not None:
            rkey = f"rate:login:{ip}"
            count = await redis.incr(rkey)
            if count == 1:
                await redis.expire(rkey, int(window_sec))
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts — try again in a minute",
                    headers={"Retry-After": str(int(window_sec))},
                )
            return
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        pass
    check_rate_limit(f"login:{ip}", limit=limit, window_sec=window_sec)


async def enforce_tenant_rate(request: Request, org_id: str | None) -> None:
    """Spec Section 19.6 — per-tenant API rate limit."""
    if not org_id:
        return
    from app.core.config import settings

    limit = int(getattr(settings, "tenant_rate_limit", 120) or 120)
    window = float(getattr(settings, "tenant_rate_window_sec", 60) or 60)
    key = f"tenant:{org_id}:{request.url.path}"
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        if redis is not None:
            rkey = f"rate:{key}"
            count = await redis.incr(rkey)
            if count == 1:
                await redis.expire(rkey, int(window))
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Org rate limit exceeded",
                    headers={"Retry-After": str(int(window))},
                )
            return
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        pass
    check_rate_limit(key, limit=limit, window_sec=window)
