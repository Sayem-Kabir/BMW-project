"""Tests for Module 2C ByteTrack road-object tracking."""

from __future__ import annotations

import numpy as np

from ml.road_understanding.object_detector import RoadDetection, RoadDetections
from ml.road_understanding.tracker import (
    RoadObjectTracker,
    RoadTracks,
    TrackedRoadObject,
    format_track_id,
)


def _detections(
    bbox: list[float] | None = None,
    *,
    class_name: str = "car",
    class_id: int = 2,
) -> RoadDetections:
    return RoadDetections(
        detections=[
            RoadDetection(
                class_name=class_name,
                confidence=0.9,
                bbox_xyxy=bbox or [10.0, 10.0, 30.0, 30.0],
                class_id=class_id,
            )
        ],
        model_loaded=True,
        using_fallback=True,
    )


def test_format_track_id_matches_api_contract():
    assert format_track_id(12) == "track_12"


def test_stable_id_and_confirmation_across_frames():
    tracker = RoadObjectTracker(min_hits=3)

    first = tracker.update(_detections())
    second = tracker.update(_detections([11.0, 10.0, 31.0, 30.0]))
    third = tracker.update(_detections([12.0, 10.0, 32.0, 30.0]))

    assert len(first.tracks) == len(second.tracks) == len(third.tracks) == 1
    assert first.tracks[0].track_id == second.tracks[0].track_id
    assert second.tracks[0].track_id == third.tracks[0].track_id
    assert first.tracks[0].confirmed is False
    assert second.tracks[0].confirmed is False
    assert third.tracks[0].confirmed is True
    assert third.tracks[0].hits == 3
    assert third.tracks[0].age_frames == 3


def test_reset_starts_a_new_frame_sequence():
    tracker = RoadObjectTracker()
    tracker.update(_detections())

    tracker.reset()
    result = tracker.update(_detections())

    assert result.frame_index == 1
    assert len(result.tracks) == 1
    assert result.tracks[0].hits == 1


def test_invalid_boxes_are_dropped_safely():
    tracker = RoadObjectTracker()
    detections = RoadDetections(
        detections=[
            RoadDetection("car", 0.9, [20.0, 20.0, 10.0, 10.0], class_id=2),
            RoadDetection("car", 0.9, [1.0, 2.0, 3.0], class_id=2),
        ],
        model_loaded=True,
    )

    result = tracker.update(detections)

    assert result.tracks == []
    assert result.input_detection_count == 2
    assert result.dropped_detection_count == 2
    assert result.tracker_ready is True


def test_empty_detection_frame_advances_tracker():
    tracker = RoadObjectTracker()
    result = tracker.update(RoadDetections(model_loaded=True))

    assert result.frame_index == 1
    assert result.tracks == []
    assert result.input_detection_count == 0


def test_track_frame_uses_supplied_detector():
    class FakeDetector:
        def detect(self, frame: np.ndarray) -> RoadDetections:
            assert frame.shape == (12, 16, 3)
            return _detections(class_name="pedestrian", class_id=0)

    tracker = RoadObjectTracker(min_hits=1)
    result = tracker.track_frame(
        np.zeros((12, 16, 3), dtype=np.uint8),
        detector=FakeDetector(),  # type: ignore[arg-type]
    )

    assert result.tracks[0].class_name == "pedestrian"
    assert result.tracks[0].confirmed is True


def test_result_serialization():
    result = RoadTracks(
        tracks=[
            TrackedRoadObject(
                track_id=7,
                class_name="car",
                confidence=0.8,
                bbox_xyxy=[1.0, 2.0, 3.0, 4.0],
                confirmed=True,
            )
        ],
        frame_index=4,
        tracker_ready=True,
        input_detection_count=1,
    )

    payload = result.to_dict()
    assert payload["count"] == 1
    assert payload["confirmed_count"] == 1
    assert payload["tracks"][0]["track_id"] == 7
    assert payload["tracks"][0]["id"] == "track_7"
