from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

_redis_client: redis.Redis | None = None


async def reset_redis() -> None:
    """Drop the cached client so the next call reconnects."""
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:  # noqa: BLE001
            pass
        _redis_client = None


async def ping_redis() -> bool:
    try:
        client = await get_redis()
        await client.ping()
        return True
    except Exception:  # noqa: BLE001
        await reset_redis()
        return False


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


async def publish_json(channel: str, payload: dict[str, Any]) -> int:
    """Serialize and publish one JSON payload to a Redis channel."""
    return await publish(channel, json.dumps(payload))


async def iter_pattern_messages(
    pattern: str,
) -> AsyncIterator[dict[str, Any]]:
    """Yield Redis pattern-subscription messages until the consumer stops.

    Only ``pmessage`` events are yielded. Callers own cancellation by
    breaking out of the async for-loop or cancelling the consumer task.
    """
    client = await get_redis()
    pubsub = client.pubsub()
    try:
        await pubsub.psubscribe(pattern)
        async for message in pubsub.listen():
            if message.get("type") != "pmessage":
                continue
            yield {
                "type": "pmessage",
                "pattern": message.get("pattern"),
                "channel": message.get("channel"),
                "data": message.get("data"),
            }
    except asyncio.CancelledError:
        raise
    except Exception:
        await reset_redis()
        raise
    finally:
        try:
            await pubsub.punsubscribe(pattern)
        except Exception:  # noqa: BLE001
            pass
        try:
            await pubsub.aclose()
        except Exception:  # noqa: BLE001
            pass


async def cache_set(key: str, value: str, ttl_seconds: int = 60) -> None:
    client = await get_redis()
    await client.set(key, value, ex=ttl_seconds)


async def cache_get(key: str) -> str | None:
    client = await get_redis()
    return await client.get(key)


async def cache_json_set(
    key: str, payload: dict[str, Any], ttl_seconds: int = 60
) -> None:
    await cache_set(key, json.dumps(payload), ttl_seconds)


async def cache_json_get(key: str) -> dict[str, Any] | None:
    raw = await cache_get(key)
    if raw is None:
        return None
    return json.loads(raw)
