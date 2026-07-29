"""MinIO object storage helpers for safety-event video clips (Module 4E + CDN)."""

from __future__ import annotations

import io
import logging
from datetime import timedelta
from functools import lru_cache
from typing import Any
from urllib.parse import quote

from app.core.config import settings

logger = logging.getLogger(__name__)


def build_object_url(bucket: str, object_name: str) -> str:
    """Spec-style URI used in ``safety_events.video_clip_url``."""
    return f"minio://{bucket}/{object_name.lstrip('/')}"


def public_http_url(bucket: str, object_name: str) -> str:
    """HTTP URL via CDN_BASE_URL or MinIO public endpoint (Phase 13 / §19)."""
    key = object_name.lstrip("/")
    cdn = (settings.cdn_base_url or "").rstrip("/")
    if cdn:
        return f"{cdn}/{bucket}/{quote(key)}"
    base = (settings.minio_public_base or "http://localhost:9000").rstrip("/")
    return f"{base}/{bucket}/{quote(key)}"


def parse_minio_uri(uri: str) -> tuple[str, str] | None:
    if not uri.startswith("minio://"):
        return None
    rest = uri[len("minio://") :]
    slash = rest.find("/")
    if slash <= 0:
        return None
    return rest[:slash], rest[slash + 1 :]


def resolve_media_url(uri: str | None) -> str | None:
    """Turn minio:// into publicly fetchable HTTP URL when possible."""
    if not uri:
        return None
    if uri.startswith("http://") or uri.startswith("https://"):
        return uri
    parsed = parse_minio_uri(uri)
    if parsed:
        return public_http_url(parsed[0], parsed[1])
    return uri


def presigned_get_url(
    uri_or_object: str,
    *,
    bucket: str | None = None,
    expires_hours: int = 24,
) -> str | None:
    """Generate a time-limited GET URL for a clip."""
    bkt = bucket or settings.minio_bucket_events
    obj = uri_or_object
    parsed = parse_minio_uri(uri_or_object)
    if parsed:
        bkt, obj = parsed
    try:
        client = _client()
        return client.presigned_get_object(
            bkt,
            obj.lstrip("/"),
            expires=timedelta(hours=max(1, expires_hours)),
        )
    except Exception:  # noqa: BLE001
        logger.debug("presign failed for %s — falling back to public URL", obj)
        return public_http_url(bkt, obj)


def clip_object_name(vehicle_id: str, event_id: str) -> str:
    return f"{vehicle_id}/{event_id}.mp4"


@lru_cache(maxsize=1)
def _client() -> Any:
    from minio import Minio

    endpoint = settings.minio_endpoint.replace("https://", "").replace("http://", "")
    return Minio(
        endpoint,
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
