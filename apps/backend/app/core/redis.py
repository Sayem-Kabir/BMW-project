from typing import Any

import redis.asyncio as redis

from app.core.config import settings

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def publish(channel: str, message: str) -> int:
    client = await get_redis()
    return await client.publish(channel, message)


async def cache_set(key: str, value: str, ttl_seconds: int = 60) -> None:
    client = await get_redis()
    await client.set(key, value, ex=ttl_seconds)


async def cache_get(key: str) -> str | None:
    client = await get_redis()
    return await client.get(key)


async def cache_json_set(key: str, payload: dict[str, Any], ttl_seconds: int = 60) -> None:
    import json

    await cache_set(key, json.dumps(payload), ttl_seconds)


async def cache_json_get(key: str) -> dict[str, Any] | None:
    import json

    raw = await cache_get(key)
    if raw is None:
        return None
    return json.loads(raw)
