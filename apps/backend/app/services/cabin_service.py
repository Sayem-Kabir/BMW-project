"""Module 02 — cabin intelligence orchestration for the API layer."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_detector: Any | None = None


def _ensure_ml_import_path() -> None:
    here = Path(__file__).resolve()
    candidates = [here.parents[4], Path("/")]
    for root in candidates:
        if (root / "ml" / "cabin_intelligence").is_dir():
            root_s = str(root)
            if root_s not in sys.path:
                sys.path.insert(0, root_s)
            return
    if Path("/ml/cabin_intelligence").is_dir() and "/" not in sys.path:
        sys.path.insert(0, "/")


def decode_image_bytes(image_bytes: bytes):
    import cv2
    import numpy as np

    if not image_bytes:
        raise ValueError("Empty image payload")
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Could not decode image — use JPEG or PNG")
    return frame


def analyze_frame_bytes(image_bytes: bytes) -> dict[str, Any]:
    _ensure_ml_import_path()
    from ml.cabin_intelligence.occupancy_detector import analyze_cabin_frame

    frame = decode_image_bytes(image_bytes)
    payload = analyze_cabin_frame(frame)
    payload["phase"] = "02"
    return payload
