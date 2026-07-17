"""Cabin intelligence — Module 1H (seat occupancy, child heuristic, unattended)."""

from ml.cabin_intelligence.child_classifier import (
    child_height_ratio,
    is_child,
)
from ml.cabin_intelligence.config import (
    CHILD_HEIGHT_RATIO_THRESHOLD,
    SEAT_ZONE_NAMES,
    SEAT_ZONES,
    UNATTENDED_TIMEOUT_SEC,
    YOLO_PERSON_MODEL_PATH,
)
from ml.cabin_intelligence.occupancy_detector import (
    CabinOccupancyDetector,
    CabinOccupancyResult,
    analyze_cabin_frame,
    assign_seat_zone,
    get_cabin_detector,
)

__all__ = [
    "SEAT_ZONES",
    "SEAT_ZONE_NAMES",
    "CHILD_HEIGHT_RATIO_THRESHOLD",
    "UNATTENDED_TIMEOUT_SEC",
    "YOLO_PERSON_MODEL_PATH",
    "child_height_ratio",
    "is_child",
    "assign_seat_zone",
    "CabinOccupancyDetector",
    "CabinOccupancyResult",
    "get_cabin_detector",
    "analyze_cabin_frame",
]
