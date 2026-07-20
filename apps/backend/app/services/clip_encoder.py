"""Encode buffered JPEG frames into an MP4 clip for MinIO upload (Module 4E)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def encode_jpeg_sequence_to_mp4(
    frames: list[bytes],
    *,
    fps: float = 30.0,
) -> bytes | None:
    """Return MP4 bytes for a JPEG frame sequence, or ``None`` if encoding fails."""
    if not frames:
        return None
    try:
        import cv2  # type: ignore[import-untyped]
        import numpy as np  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("opencv-python not installed; video clip encoding skipped")
        return None

    decoded: list = []
    for payload in frames:
        array = np.frombuffer(payload, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if image is not None:
            decoded.append(image)
    if not decoded:
        return None

    height, width = decoded[0].shape[:2]
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
        temp_path = Path(handle.name)

    writer = cv2.VideoWriter(
        str(temp_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        float(fps),
        (width, height),
    )
    if not writer.isOpened():
        temp_path.unlink(missing_ok=True)
        return None

    try:
        for image in decoded:
            writer.write(image)
    finally:
        writer.release()

    try:
        return temp_path.read_bytes()
    finally:
        temp_path.unlink(missing_ok=True)
