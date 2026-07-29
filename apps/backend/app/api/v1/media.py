"""Media URL helpers — CDN / presigned clip resolution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.minio import presigned_get_url, resolve_media_url
from app.core.security import require_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/media", tags=["Media"])


class ResolveRequest(BaseModel):
    url: str


@router.get("/resolve")
async def resolve_clip(
    url: str = Query(..., min_length=1),
    _user: User = Depends(require_user),
):
    """Resolve minio:// to HTTP (CDN or public MinIO) + optional presign."""
    http = resolve_media_url(url)
    signed = None
    if url.startswith("minio://"):
        signed = presigned_get_url(url)
    return {
        "source": url,
        "http_url": signed or http,
        "cdn_or_public": http,
        "phase": "13",
    }
