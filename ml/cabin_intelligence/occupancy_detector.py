"""Seat-zone occupancy via COCO YOLOv8n person detection (Module 1H)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ml.cabin_intelligence.child_classifier import is_child
from ml.cabin_intelligence.config import (
    CHILD_HEIGHT_RATIO_THRESHOLD,
    MOTION_PIXEL_THRESHOLD,
    PERSON_CONFIDENCE,
    PERSON_IOU,
    SEAT_ZONE_NAMES,
    SEAT_ZONES,
    UNATTENDED_TIMEOUT_SEC,
    YOLO_PERSON_MODEL_PATH,
)
from ml.common.gpu_detector import get_inference_device


@dataclass
class PersonDetection:
    confidence: float
    bbox_xyxy: list[float]
    seat_zone: str | None = None
    is_child: bool = False


@dataclass
class CabinOccupancyResult:
    total_occupants: int = 0
    driver_present: bool = False
    front_passenger: bool = False
    rear_passengers: int = 0
    child_detected: bool = False
    child_alert: bool = False
    unattended_vehicle: bool = False
    occupant_map: dict[str, bool] = field(default_factory=dict)
    persons: list[PersonDetection] = field(default_factory=list)
    model_loaded: bool = False
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_occupants": self.total_occupants,
            "driver_present": self.driver_present,
            "front_passenger": self.front_passenger,
            "rear_passengers": self.rear_passengers,
            "child_detected": self.child_detected,
            "child_alert": self.child_alert,
            "unattended_vehicle": self.unattended_vehicle,
            "occupant_map": dict(self.occupant_map),
            "persons": [
                {
                    "confidence": p.confidence,
                    "bbox": p.bbox_xyxy,
                    "seat_zone": p.seat_zone,
                    "is_child": p.is_child,
                }
                for p in self.persons
            ],
            "model_loaded": self.model_loaded,
            "message": self.message,
        }


def _zone_abs(
    zone: tuple[float, float, float, float], w: int, h: int
) -> tuple[float, float, float, float]:
    x1, y1, x2, y2 = zone
    return x1 * w, y1 * h, x2 * w, y2 * h


def bbox_center(bbox: list[float]) -> tuple[float, float]:
    return (bbox[0] + bbox[2]) * 0.5, (bbox[1] + bbox[3]) * 0.5


def _intersection_area(
    a: tuple[float, float, float, float] | list[float],
    b: tuple[float, float, float, float] | list[float],
) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    return iw * ih


def assign_seat_zone(
    bbox_xyxy: list[float],
    frame_w: int,
    frame_h: int,
    zones: dict[str, tuple[float, float, float, float]] | None = None,
) -> str | None:
    """Assign person to the seat zone with the largest bbox overlap."""
    zones = zones or SEAT_ZONES
    best_name: str | None = None
    best_area = 0.0
    for name, zone in zones.items():
        area = _intersection_area(bbox_xyxy, _zone_abs(zone, frame_w, frame_h))
        if area > best_area:
            best_area = area
            best_name = name
    return best_name if best_area > 0 else None


def _empty_map() -> dict[str, bool]:
    return {name: False for name in SEAT_ZONE_NAMES}


class CabinOccupancyDetector:
    """
    Detect persons with COCO YOLOv8n and map them onto 5 cabin seat ROIs.

    Uses ultralytics pretrained weights (downloads yolov8n.pt on first use if missing).
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        seat_zones: dict[str, tuple[float, float, float, float]] | None = None,
        person_conf: float = PERSON_CONFIDENCE,
        child_threshold: float = CHILD_HEIGHT_RATIO_THRESHOLD,
        unattended_timeout_sec: float = UNATTENDED_TIMEOUT_SEC,
        motion_px: float = MOTION_PIXEL_THRESHOLD,
        device: str | int | None = None,
    ) -> None:
        self.model_path = Path(model_path) if model_path else YOLO_PERSON_MODEL_PATH
        self.seat_zones = seat_zones or dict(SEAT_ZONES)
        self.person_conf = person_conf
        self.child_threshold = child_threshold
        self.unattended_timeout_sec = unattended_timeout_sec
        self.motion_px = motion_px
        self.device = get_inference_device(device)
        self._model = None
        self._model_error: str | None = None
        self._last_driver_centroid: tuple[float, float] | None = None
        self._last_driver_motion_at: float | None = None

    def reset(self) -> None:
        self._last_driver_centroid = None
        self._last_driver_motion_at = None

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        if self._model_error:
            return False
        try:
            from ultralytics import YOLO

            # Prefer local path; else let ultralytics fetch 'yolov8n.pt'
            path = self.model_path if self.model_path.is_file() else "yolov8n.pt"
            self._model = YOLO(str(path))
            return True
        except Exception as exc:  # noqa: BLE001
            self._model_error = str(exc)
            return False

    def detect_persons(self, frame: np.ndarray) -> list[PersonDetection]:
        if not self._ensure_model():
            return []
        assert self._model is not None
        results = self._model.predict(
            frame,
            conf=self.person_conf,
            iou=PERSON_IOU,
            classes=[0],  # COCO person
            device=self.device,
            verbose=False,
        )
        persons: list[PersonDetection] = []
        if not results:
            return persons
        boxes = results[0].boxes
        if boxes is None:
            return persons
        for box in boxes:
            conf = float(box.conf[0])
            xyxy = [float(v) for v in box.xyxy[0].tolist()]
            persons.append(PersonDetection(confidence=conf, bbox_xyxy=xyxy))
        return persons

    def analyze_frame(
        self,
        frame: np.ndarray,
        *,
        now: float | None = None,
    ) -> CabinOccupancyResult:
        """Run person detection + seat mapping + child / unattended heuristics."""
        h, w = frame.shape[:2]
        now = time.monotonic() if now is None else now

        if not self._ensure_model():
            return CabinOccupancyResult(
                occupant_map=_empty_map(),
                model_loaded=False,
                message=self._model_error
                or "YOLO person model unavailable — install ultralytics / allow yolov8n.pt download",
            )

        persons = self.detect_persons(frame)
        occupied = _empty_map()
        child_any = False
        annotated: list[PersonDetection] = []

        for person in persons:
            zone = assign_seat_zone(person.bbox_xyxy, w, h, self.seat_zones)
            person.seat_zone = zone
            if zone is not None:
                occupied[zone] = True
                zone_norm = self.seat_zones[zone]
                person.is_child = is_child(
                    person.bbox_xyxy,
                    zone_norm,
                    h,
                    threshold=self.child_threshold,
                )
                if person.is_child:
                    child_any = True
            annotated.append(person)

        driver_present = occupied.get("driver", False)
        front_passenger = occupied.get("front_right", False)
        rear_passengers = sum(
            1 for z in ("rear_left", "rear_center", "rear_right") if occupied.get(z)
        )
        total = sum(1 for v in occupied.values() if v)

        # Driver motion tracking for unattended alert
        driver_centroid = None
        for p in annotated:
            if p.seat_zone == "driver":
                driver_centroid = bbox_center(p.bbox_xyxy)
                break

        if driver_centroid is not None:
            if self._last_driver_centroid is not None:
                dx = driver_centroid[0] - self._last_driver_centroid[0]
                dy = driver_centroid[1] - self._last_driver_centroid[1]
                if (dx * dx + dy * dy) ** 0.5 >= self.motion_px:
                    self._last_driver_motion_at = now
            else:
                self._last_driver_motion_at = now
            self._last_driver_centroid = driver_centroid
        else:
            self._last_driver_centroid = None
            # No driver: do not refresh motion clock (timeout can elapse)

        occupants_present = total > 0
        unattended = False
        if occupants_present and not driver_present:
            # Occupants without a driver is immediately an unattended/unsafe cabin
            unattended = True
        elif occupants_present and driver_present:
            if self._last_driver_motion_at is None:
                self._last_driver_motion_at = now
            elif (now - self._last_driver_motion_at) >= self.unattended_timeout_sec:
                unattended = True

        # Child left alone: child present, no adult in front seats
        child_alert = child_any and not driver_present and not front_passenger

        return CabinOccupancyResult(
            total_occupants=total,
            driver_present=driver_present,
            front_passenger=front_passenger,
            rear_passengers=rear_passengers,
            child_detected=child_any,
            child_alert=child_alert,
            unattended_vehicle=unattended,
            occupant_map=occupied,
            persons=annotated,
            model_loaded=True,
            message=None,
        )


_detector: CabinOccupancyDetector | None = None


def get_cabin_detector() -> CabinOccupancyDetector:
    global _detector
    if _detector is None:
        _detector = CabinOccupancyDetector()
    return _detector


def analyze_cabin_frame(frame: np.ndarray) -> dict[str, Any]:
    """Convenience: occupancy map JSON for one frame."""
    return get_cabin_detector().analyze_frame(frame).to_dict()
