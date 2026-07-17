"""Module 1H — cabin seat-zone geometry and thresholds."""

from __future__ import annotations

from pathlib import Path

# COCO-pretrained YOLOv8n (person = class 0). Cached under ml/models/ when first loaded.
ML_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ML_ROOT / "models"
YOLO_PERSON_MODEL_PATH = MODELS_DIR / "yolov8n.pt"

# Seat zones as normalized [x1, y1, x2, y2] (cabin-facing camera).
# Front and rear bands are split to avoid double-counting on the mid-cabin line.
SEAT_ZONES: dict[str, tuple[float, float, float, float]] = {
    "driver": (0.00, 0.08, 0.48, 0.55),
    "front_right": (0.52, 0.08, 1.00, 0.55),
    "rear_left": (0.00, 0.55, 0.34, 1.00),
    "rear_center": (0.34, 0.55, 0.66, 1.00),
    "rear_right": (0.66, 0.55, 1.00, 1.00),
}

SEAT_ZONE_NAMES = tuple(SEAT_ZONES.keys())

# Person detection
PERSON_CONFIDENCE = 0.45
PERSON_IOU = 0.45

# Child heuristic: bbox height / assigned seat-zone height < this → child
CHILD_HEIGHT_RATIO_THRESHOLD = 0.50

# Unattended vehicle: occupants present + no driver-zone motion for this many seconds
UNATTENDED_TIMEOUT_SEC = 300.0
MOTION_PIXEL_THRESHOLD = 8.0  # centroid movement (frame pixels) counts as motion
