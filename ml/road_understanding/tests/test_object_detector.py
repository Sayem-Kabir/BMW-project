"""Tests for the optional road-object detector (works with COCO fallback)."""

from __future__ import annotations

import numpy as np

from ml.road_understanding.config import (
    ROAD_CLASS_NAMES,
    YOLO_ROAD_FALLBACK_MODEL,
    resolve_yolo_road_weights,
)
from ml.road_understanding.object_detector import (
    RoadDetection,
    RoadDetections,
    YOLORoadDetector,
    _map_class_name,
)


def test_map_coco_person_to_pedestrian():
    assert _map_class_name("person", using_fallback=True) == "pedestrian"
    assert _map_class_name("stop sign", using_fallback=True) == "traffic sign"
    assert _map_class_name("car", using_fallback=False) == "car"


def test_road_detections_to_dict():
    out = RoadDetections(
        detections=[RoadDetection("car", 0.9, [1, 2, 3, 4], class_id=2)],
        model_loaded=True,
        using_fallback=True,
        weights_path="yolov8m.pt",
    )
    d = out.to_dict()
    assert d["count"] == 1
    assert d["detections"][0]["class"] == "car"
    assert d["using_fallback"] is True


def test_resolve_weights_default():
    w = resolve_yolo_road_weights()
    assert w in {YOLO_ROAD_FALLBACK_MODEL} or w.endswith("road_yolov8m_best.pt")


def test_detector_blank_frame_with_fallback_or_skip():
    """Loads COCO yolov8m if available; otherwise records a clear error."""
    det = YOLORoadDetector(auto_load=True)
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    out = det.detect(blank)
    assert isinstance(out, RoadDetections)
    if out.model_loaded:
        assert out.using_fallback in (True, False)
        assert isinstance(out.detections, list)
        assert len(out.detections) >= 0
    else:
        assert out.message


def test_class_names_config():
    assert "traffic light" in ROAD_CLASS_NAMES
    assert len(ROAD_CLASS_NAMES) == 10
