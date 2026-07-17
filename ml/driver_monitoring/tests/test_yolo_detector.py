"""Tests for Module 1D YOLO detector (no trained weights required)."""

from __future__ import annotations

import numpy as np

from ml.driver_monitoring.config import YOLO_CLASS_NAMES, YOLO_DRIVER_MODEL_PATH, yolo_driver_model_ready
from ml.driver_monitoring.yolo_detector import (
    DriverObjectDetections,
    YOLODriverDetector,
    detect_driver_objects,
)


def test_class_names_match_spec():
    assert YOLO_CLASS_NAMES == ("phone", "smoking", "no_seatbelt")


def test_yolo_weights_missing_by_default_or_optional():
    # In a fresh checkout the fine-tuned weights are not committed
    if not yolo_driver_model_ready():
        assert not YOLO_DRIVER_MODEL_PATH.is_file() or YOLO_DRIVER_MODEL_PATH.stat().st_size == 0


def test_detect_without_weights_returns_safe_defaults():
    detector = YOLODriverDetector(model_path=YOLO_DRIVER_MODEL_PATH.parent / "does_not_exist.pt")
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = detector.detect(frame)
    assert isinstance(result, DriverObjectDetections)
    assert result.model_loaded is False
    assert result.phone_detected is False
    assert result.smoking_detected is False
    assert result.seatbelt_worn is True
    assert result.message is not None
    assert "Weights missing" in result.message


def test_detect_empty_frame():
    detector = YOLODriverDetector(model_path=YOLO_DRIVER_MODEL_PATH.parent / "does_not_exist.pt")
    result = detector.detect(np.array([]))
    assert result.message == "Empty frame"


def test_to_dict_shape():
    result = DriverObjectDetections(phone_detected=True, model_loaded=False, message="x")
    d = result.to_dict()
    assert d["phone_detected"] is True
    assert "detections" in d
    assert "seatbelt_worn" in d


def test_convenience_wrapper():
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    # May or may not have weights; either way should not crash
    result = detect_driver_objects(frame)
    assert isinstance(result, DriverObjectDetections)
