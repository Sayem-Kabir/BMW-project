"""Upload validation — Spec Phase 10C MIME type + size limits."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile, status

# Default max frame upload (5 MB)
DEFAULT_MAX_BYTES = 5 * 1024 * 1024

ALLOWED_IMAGE_MIME = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
        "image/gif",
    }
)

# Magic-byte sniff for common image types when Content-Type is missing/wrong
_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"RIFF", "image/webp"),  # RIFF....WEBP
)


def sniff_image_mime(data: bytes) -> str | None:
    if not data:
        return None
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            if mime == "image/webp" and b"WEBP" not in data[:16]:
                continue
            return mime
    return None


async def read_upload_bytes(
    file: UploadFile,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    allowed_mime: frozenset[str] = ALLOWED_IMAGE_MIME,
) -> bytes:
    """Read an upload with size + MIME checks. Raises HTTP 400/413."""
    declared = (file.content_type or "").split(";")[0].strip().lower()
    chunks: list[bytes] = []
    total = 0
    while True:
        piece = await file.read(64 * 1024)
        if not piece:
            break
        total += len(piece)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {max_bytes} bytes",
            )
        chunks.append(piece)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    sniffed = sniff_image_mime(data)
    if sniffed is None and declared not in allowed_mime:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type (got {declared or 'unknown'}); "
            f"allowed: {sorted(allowed_mime)}",
        )
    if sniffed is not None and sniffed not in allowed_mime:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type {sniffed}",
        )
    if declared and declared not in allowed_mime and sniffed is None:
        raise HTTPException(
            status_code=400,
            detail=f"Content-Type {declared} is not an allowed image type",
        )
    return data
