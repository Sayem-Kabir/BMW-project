"""MinIO object storage helpers for safety-event video clips (Module 4E)."""

from __future__ import annotations

import io
import logging
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def build_object_url(bucket: str, object_name: str) -> str:
    """Spec-style URI used in ``safety_events.video_clip_url``."""
    return f"minio://{bucket}/{object_name.lstrip('/')}"


def clip_object_name(vehicle_id: str, event_id: str) -> str:
    return f"{vehicle_id}/{event_id}.mp4"


@lru_cache(maxsize=1)
def _client() -> Any:
    from minio import Minio

    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_endpoint.startswith("https"),
    )


def ensure_bucket(bucket: str | None = None) -> bool:
    """Create the events bucket when MinIO is reachable."""
    target = bucket or settings.minio_bucket_events
    try:
        client = _client()
        if not client.bucket_exists(target):
            client.make_bucket(target)
        return True
    except Exception:  # noqa: BLE001 — callers decide how to degrade
        logger.exception("MinIO bucket check failed for %s", target)
        return False


def upload_bytes(
    object_name: str,
    data: bytes,
    *,
    bucket: str | None = None,
    content_type: str = "video/mp4",
) -> str | None:
    """Upload clip bytes and return the ``minio://`` URL, or ``None`` on failure."""
    if not data:
        return None
    target = bucket or settings.minio_bucket_events
    try:
        client = _client()
        if not client.bucket_exists(target):
            client.make_bucket(target)
        client.put_object(
            target,
            object_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return build_object_url(target, object_name)
    except Exception:  # noqa: BLE001
        logger.exception("MinIO upload failed for %s", object_name)
        return None


def upload_event_clip(
    vehicle_id: str,
    event_id: str,
    clip_bytes: bytes,
) -> str | None:
    return upload_bytes(
        clip_object_name(vehicle_id, event_id),
        clip_bytes,
        content_type="video/mp4",
    )
