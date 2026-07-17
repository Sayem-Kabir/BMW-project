"""Tests for Module 1H cabin intelligence (no YOLO weights required)."""

from __future__ import annotations

import numpy as np

from ml.cabin_intelligence.child_classifier import child_height_ratio, is_child
from ml.cabin_intelligence.config import SEAT_ZONE_NAMES, SEAT_ZONES
from ml.cabin_intelligence.occupancy_detector import (
    CabinOccupancyDetector,
    CabinOccupancyResult,
    PersonDetection,
    assign_seat_zone,
)


def test_five_seat_zones_defined():
    assert set(SEAT_ZONE_NAMES) == {
        "driver",
        "front_right",
        "rear_left",
        "rear_center",
        "rear_right",
    }
    for name, zone in SEAT_ZONES.items():
        x1, y1, x2, y2 = zone
        assert 0.0 <= x1 < x2 <= 1.0
        assert 0.0 <= y1 < y2 <= 1.0


def test_assign_seat_zone_driver_and_rear():
    w, h = 1000, 1000
    # Mostly inside driver band (y < 0.55)
    driver_bbox = [50, 100, 300, 500]
    assert assign_seat_zone(driver_bbox, w, h) == "driver"

    rear_left_bbox = [20, 600, 250, 950]
    assert assign_seat_zone(rear_left_bbox, w, h) == "rear_left"

    outside = [480, 20, 520, 60]
    assert assign_seat_zone(outside, w, h) is None


def test_child_height_heuristic():
    zone = (0.0, 0.0, 1.0, 1.0)  # full frame zone
    frame_h = 100
    short_bbox = [10, 60, 40, 90]  # height 30 → ratio 0.30
    tall_bbox = [10, 10, 40, 90]  # height 80 → ratio 0.80
    assert child_height_ratio(short_bbox, zone, frame_h) == 0.3
    assert is_child(short_bbox, zone, frame_h, threshold=0.5) is True
    assert is_child(tall_bbox, zone, frame_h, threshold=0.5) is False


def test_occupancy_map_schema_without_model():
    det = CabinOccupancyDetector(model_path="__missing_cabin__.pt")
    # Force model failure path without downloading
    det._model_error = "forced"
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    out = det.analyze_frame(blank)
    assert isinstance(out, CabinOccupancyResult)
    d = out.to_dict()
    assert d["model_loaded"] is False
    assert d["total_occupants"] == 0
    assert set(d["occupant_map"].keys()) == set(SEAT_ZONE_NAMES)
    assert all(v is False for v in d["occupant_map"].values())


def test_analyze_with_injected_persons():
    """Simulate detections without calling ultralytics."""
    det = CabinOccupancyDetector(unattended_timeout_sec=10.0)

    def fake_persons(frame):
        # Adult-sized box mostly in driver zone
        return [
            PersonDetection(confidence=0.9, bbox_xyxy=[80, 100, 280, 480]),
            # Short box in rear_left → child
            PersonDetection(confidence=0.8, bbox_xyxy=[40, 620, 160, 780]),
        ]

    det.detect_persons = fake_persons  # type: ignore[method-assign]
    det._model = object()  # pretend loaded
    det._model_error = None

    frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
    out = det.analyze_frame(frame, now=100.0)
    assert out.model_loaded is True
    assert out.driver_present is True
    assert out.occupant_map["driver"] is True
    assert out.occupant_map["rear_left"] is True
    assert out.total_occupants == 2
    assert out.rear_passengers == 1
    assert out.child_detected is True
    assert out.child_alert is False  # driver present
    assert out.unattended_vehicle is False


def test_unattended_when_occupants_no_driver():
    det = CabinOccupancyDetector()

    def fake_persons(frame):
        return [PersonDetection(confidence=0.9, bbox_xyxy=[700, 100, 900, 480])]

    det.detect_persons = fake_persons  # type: ignore[method-assign]
    det._model = object()
    frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
    out = det.analyze_frame(frame, now=1.0)
    assert out.front_passenger is True
    assert out.driver_present is False
    assert out.unattended_vehicle is True


def test_unattended_after_no_driver_motion():
    det = CabinOccupancyDetector(unattended_timeout_sec=5.0, motion_px=8.0)

    def fake_persons(frame):
        # Static driver + rear passenger
        return [
            PersonDetection(confidence=0.9, bbox_xyxy=[100, 100, 280, 480]),
            PersonDetection(confidence=0.8, bbox_xyxy=[50, 650, 180, 900]),
        ]

    det.detect_persons = fake_persons  # type: ignore[method-assign]
    det._model = object()
    frame = np.zeros((1000, 1000, 3), dtype=np.uint8)

    t0 = 1000.0
    first = det.analyze_frame(frame, now=t0)
    assert first.unattended_vehicle is False

    later = det.analyze_frame(frame, now=t0 + 6.0)
    assert later.driver_present is True
    assert later.unattended_vehicle is True
