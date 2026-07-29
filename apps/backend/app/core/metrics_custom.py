"""Custom Prometheus metrics — Spec Phase 10B."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

INFERENCE_SECONDS = Histogram(
    "bmw_inference_seconds",
    "Model inference latency in seconds",
    ["pipeline"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

CELERY_QUEUE_DEPTH = Gauge(
    "bmw_celery_queue_depth",
    "Approximate Celery broker queue depth",
    ["queue"],
)

LOGIN_ATTEMPTS = Counter(
    "bmw_login_attempts_total",
    "Login attempts",
    ["result"],
)


def observe_inference(pipeline: str, seconds: float) -> None:
    try:
        INFERENCE_SECONDS.labels(pipeline=pipeline).observe(seconds)
    except Exception:  # noqa: BLE001
        pass


def set_celery_depth(queue: str, depth: float) -> None:
    try:
        CELERY_QUEUE_DEPTH.labels(queue=queue).set(depth)
    except Exception:  # noqa: BLE001
        pass


async def refresh_celery_queue_depth() -> dict[str, int]:
    """Best-effort LLEN on Celery default queues."""
    depths: dict[str, int] = {}
    try:
        from app.core.redis import get_redis

        redis = await get_redis()
        if redis is None:
            return depths
        for queue in ("celery", "default", "ml_tasks", "notifications"):
            try:
                depth = int(await redis.llen(queue))
            except Exception:  # noqa: BLE001
                depth = 0
            depths[queue] = depth
            set_celery_depth(queue, depth)
    except Exception:  # noqa: BLE001
        pass
    return depths
