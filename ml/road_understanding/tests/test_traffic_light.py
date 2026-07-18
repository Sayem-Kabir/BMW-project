"""Tests for Module 2E HSV traffic-light classification."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from ml.road_understanding.traffic_light import TrafficLightClassifier
from ml.road_understanding.tracker import RoadTracks, TrackedRoadObject


def _hsv_signal(hue: int, *, height: int = 30, width: int = 30) -> np.ndarray:
    hsv = np.zeros((height, width, 3), dtype=np.uint8)
    hsv[5:-5, 5:-5] = (hue, 255, 255)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


@pytest.mark.parametrize(
    ("hue", "expected"),
    [(0, "RED"), (20, "AMBER"), (60, "GREEN"), (175, "RED")],
)
def test_classifies_hsv_signal_colors(hue: int, expected: str):
    result = TrafficLightClassifier().classify_crop(_hsv_signal(hue))

    assert result.state == expected
    assert result.confidence == pytest.approx(1.0)
    assert result.active_pixels > 0
    assert result.is_known


def test_low_saturation_crop_is_unknown():
    crop = np.full((30, 30, 3), 180, dtype=np.uint8)
    result = TrafficLightClassifier().classify_crop(crop)

    assert result.state == "UNKNOWN"
    assert result.active_pixels == 0
    assert "Insufficient" in (result.message or "")


def test_ambiguous_red_and_green_crop_is_unknown():
    hsv = np.zeros((30, 30, 3), dtype=np.uint8)
    hsv[:, :15] = (0, 255, 255)
    hsv[:, 15:] = (60, 255, 255)
    crop = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    result = TrafficLightClassifier().classify_crop(crop)

    assert result.state == "UNKNOWN"
    assert result.color_scores["RED"] == pytest.approx(0.5)
    assert result.color_scores["GREEN"] == pytest.approx(0.5)


def test_tiny_crop_is_unknown():
    result = TrafficLightClassifier().classify_crop(
        np.zeros((4, 4, 3), dtype=np.uint8)
    )
    assert result.state == "UNKNOWN"
    assert "at least 8px" in (result.message or "")


def test_classify_tracks_skips_non_traffic_lights_and_clips_bbox():
    frame = np.zeros((40, 50, 3), dtype=np.uint8)
    frame[:30, :30] = _hsv_signal(60)
    tracks = RoadTracks(
        tracks=[
            TrackedRoadObject(
                track_id=1,
                class_name="traffic_light",
                confidence=0.9,
                bbox_xyxy=[-5.0, -5.0, 30.0, 30.0],
            ),
            TrackedRoadObject(
                track_id=2,
                class_name="car",
                confidence=0.8,
                bbox_xyxy=[10.0, 10.0, 30.0, 30.0],
            ),
        ],
        tracker_ready=True,
    )

    result = TrafficLightClassifier().classify_tracks(frame, tracks)

    assert len(result.classifications) == 1
    assert result.classifications[0].id == "track_1"
    assert result.classifications[0].state == "GREEN"
    assert result.classifications[0].bbox_xyxy == [0.0, 0.0, 30.0, 30.0]
    assert result.skipped_non_traffic_lights == 1


def test_annotate_tracks_preserves_depth_and_non_light_state():
    frame = np.zeros((30, 60, 3), dtype=np.uint8)
    frame[:, :30] = _hsv_signal(0)
    tracks = RoadTracks(
        tracks=[
            TrackedRoadObject(
                track_id=3,
                class_name="traffic light",
                confidence=0.95,
                bbox_xyxy=[0.0, 0.0, 30.0, 30.0],
                relative_inverse_depth=4.0,
                distance_m=3.0,
                distance_calibrated=True,
            ),
            TrackedRoadObject(
                track_id=4,
                class_name="car",
                confidence=0.85,
                bbox_xyxy=[30.0, 0.0, 60.0, 30.0],
                state="PARKED",
            ),
        ],
        frame_index=8,
    )

    annotated = TrafficLightClassifier().annotate_tracks(frame, tracks)

    light, car = annotated.tracks
    assert annotated.frame_index == 8
    assert light.state == "RED"
    assert light.state_confidence == pytest.approx(1.0)
    assert light.distance_m == 3.0
    assert light.distance_calibrated is True
    assert car.state == "PARKED"


def test_invalid_track_box_returns_unknown():
    track = TrackedRoadObject(
        track_id=5,
        class_name="traffic light",
        confidence=0.9,
        bbox_xyxy=[50.0, 50.0, 60.0, 60.0],
    )
    result = TrafficLightClassifier().classify_track(
        np.zeros((20, 20, 3), dtype=np.uint8),
        track,
    )

    assert result is not None
    assert result.state == "UNKNOWN"
    assert "Invalid or out-of-frame" in (result.message or "")
