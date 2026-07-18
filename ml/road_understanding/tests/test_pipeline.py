"""Tests for Module 2G unified road-understanding pipeline."""

from __future__ import annotations

import json
from dataclasses import replace

import numpy as np

from ml.road_understanding.depth_estimator import (
    DepthMap,
    ObjectDepthEstimate,
    RoadDepthResult,
)
from ml.road_understanding.object_detector import RoadDetection, RoadDetections
from ml.road_understanding.pedestrian_temporal import (
    PedestrianTemporalLocalization,
)
from ml.road_understanding.pipeline import (
    RoadPipelineOptions,
    RoadUnderstandingPipeline,
)
from ml.road_understanding.road_segmenter import RoadSegmentation
from ml.road_understanding.tracker import RoadTracks, TrackedRoadObject
from ml.road_understanding.traffic_light import (
    TrafficLightClassification,
    TrafficLightResults,
)


class _FakeSegmenter:
    def __init__(self, calls):
        self.calls = calls

    def segment(self, frame, *, input_color="bgr"):
        self.calls.append("segmentation")
        return RoadSegmentation(
            mask=np.zeros(frame.shape[:2], dtype=np.uint8),
            confidence=np.ones(frame.shape[:2], dtype=np.float32),
            model_loaded=True,
        )


class _FakeDetector:
    def __init__(self, calls):
        self.calls = calls

    def detect(self, frame):
        self.calls.append("detection")
        return RoadDetections(
            detections=[
                RoadDetection("pedestrian", 0.9, [10, 10, 40, 70], class_id=0),
                RoadDetection("traffic light", 0.8, [70, 10, 85, 35], class_id=9),
            ],
            model_loaded=True,
        )


class _FakeTracker:
    def __init__(self, calls):
        self.calls = calls
        self.frame_index = 0
        self.reset_count = 0

    def update(self, detections):
        self.calls.append("tracking")
        self.frame_index += 1
        return RoadTracks(
            tracks=[
                TrackedRoadObject(
                    track_id=1,
                    class_name="pedestrian",
                    confidence=0.9,
                    bbox_xyxy=[10, 10, 40, 70],
                    confirmed=True,
                ),
                TrackedRoadObject(
                    track_id=2,
                    class_name="traffic light",
                    confidence=0.8,
                    bbox_xyxy=[70, 10, 85, 35],
                    confirmed=True,
                ),
            ],
            frame_index=self.frame_index,
            tracker_ready=True,
            input_detection_count=len(detections.detections),
            detector_model_loaded=detections.model_loaded,
        )

    def reset(self):
        self.frame_index = 0
        self.reset_count += 1


class _FakeDepthEstimator:
    def __init__(self, calls, *, fail=False):
        self.calls = calls
        self.fail = fail

    def estimate_tracks(self, frame, tracks, *, input_color="bgr"):
        self.calls.append("depth")
        if self.fail:
            raise RuntimeError("depth unavailable")
        return RoadDepthResult(
            depth_map=DepthMap(
                relative_inverse_depth=np.ones(frame.shape[:2], dtype=np.float32),
                model_loaded=True,
            ),
            objects=[
                ObjectDepthEstimate(
                    track_id=track.track_id,
                    class_name=track.class_name,
                    bbox_xyxy=track.bbox_xyxy,
                    relative_inverse_depth=float(track.track_id),
                    distance_m=10.0 * track.track_id,
                    metric_calibrated=True,
                )
                for track in tracks.tracks
            ],
        )


class _FakeTrafficLightClassifier:
    def __init__(self, calls):
        self.calls = calls

    def classify_tracks(self, frame, tracks, *, input_color="bgr"):
        self.calls.append("traffic_lights")
        return TrafficLightResults(
            classifications=[
                TrafficLightClassification(
                    state="RED",
                    confidence=0.95,
                    track_id=2,
                    bbox_xyxy=[70, 10, 85, 35],
                )
            ],
            input_track_count=len(tracks.tracks),
            skipped_non_traffic_lights=1,
        )


class _FakePedestrianLocalizer:
    def __init__(self, calls):
        self.calls = calls
        self.reset_count = 0

    def update(self, frame, *, input_color="bgr"):
        self.calls.append("pedestrian_temporal")
        return PedestrianTemporalLocalization(
            detected=True,
            confidence=0.92,
            bbox_xyxy=[10, 10, 40, 70],
            normalized_bbox_xywh=[0.25, 0.4, 0.3, 0.6],
            frames_used=5,
            model_loaded=True,
        )

    def associate_tracks(self, localization, tracks):
        return replace(
            tracks,
            tracks=[
                (
                    replace(
                        track,
                        temporal_confidence=localization.confidence,
                        temporal_bbox_xyxy=localization.bbox_xyxy,
                        temporally_confirmed=True,
                    )
                    if track.track_id == 1
                    else track
                )
                for track in tracks.tracks
            ],
        )

    def reset(self):
        self.reset_count += 1


def _pipeline(*, depth_fail=False, options=None):
    calls = []
    tracker = _FakeTracker(calls)
    localizer = _FakePedestrianLocalizer(calls)
    pipeline = RoadUnderstandingPipeline(
        segmenter=_FakeSegmenter(calls),
        detector=_FakeDetector(calls),
        tracker=tracker,
        depth_estimator=_FakeDepthEstimator(calls, fail=depth_fail),
        traffic_light_classifier=_FakeTrafficLightClassifier(calls),
        pedestrian_localizer=localizer,
        options=options,
    )
    return pipeline, calls, tracker, localizer


def test_pipeline_runs_modules_in_dependency_order_and_merges_annotations():
    pipeline, calls, _, _ = _pipeline()

    result = pipeline.process_frame(np.zeros((100, 100, 3), dtype=np.uint8))

    assert calls == [
        "segmentation",
        "detection",
        "tracking",
        "depth",
        "traffic_lights",
        "pedestrian_temporal",
    ]
    assert result.frame_index == 1
    assert result.segmentation.is_valid
    assert result.depth.is_valid
    pedestrian, traffic_light = result.tracks.tracks
    assert pedestrian.distance_m == 10.0
    assert pedestrian.temporally_confirmed
    assert pedestrian.temporal_confidence == 0.92
    assert traffic_light.distance_m == 20.0
    assert traffic_light.state == "RED"
    assert traffic_light.state_confidence == 0.95
    assert set(result.stage_times_ms) == set(calls)
    assert result.processing_ms >= sum(result.stage_times_ms.values())


def test_pipeline_result_serializes_without_full_resolution_arrays():
    pipeline, _, _, _ = _pipeline()
    result = pipeline.process_frame(np.zeros((50, 80, 3), dtype=np.uint8))

    payload = result.to_dict()
    encoded = json.dumps(payload)

    assert '"phase": "2G"' in encoded
    assert payload["segmentation"]["mask_shape"] == [50, 80]
    assert payload["depth"]["depth"]["map_shape"] == [50, 80]
    assert payload["objects"][0]["temporally_confirmed"]
    assert "relative_inverse_depth" not in payload["depth"]["depth"]


def test_pipeline_returns_partial_result_when_one_stage_raises():
    pipeline, calls, _, _ = _pipeline(depth_fail=True)

    result = pipeline.process_frame(np.zeros((40, 60, 3), dtype=np.uint8))

    assert len(result.tracks.tracks) == 2
    assert result.tracks.tracks[1].state == "RED"
    assert result.tracks.tracks[0].temporally_confirmed
    assert any("depth unavailable" in warning for warning in result.warnings)
    assert result.message == "Road frame processed with degraded stages"
    assert calls[-2:] == ["traffic_lights", "pedestrian_temporal"]


def test_invalid_frame_does_not_advance_state_or_call_modules():
    pipeline, calls, _, _ = _pipeline()

    result = pipeline.process_frame(np.asarray([]))

    assert not result.is_valid
    assert result.frame_index == 0
    assert pipeline.frame_index == 0
    assert calls == []
    assert result.message == "Invalid frame"


def test_reset_clears_pipeline_tracker_and_temporal_history():
    pipeline, _, tracker, localizer = _pipeline()
    pipeline.process_frame(np.zeros((20, 20, 3), dtype=np.uint8))

    pipeline.reset()

    assert pipeline.frame_index == 0
    assert tracker.reset_count == 1
    assert localizer.reset_count == 1


def test_pipeline_options_skip_disabled_expensive_stages():
    options = RoadPipelineOptions(
        segmentation=False,
        depth=False,
        traffic_lights=False,
        pedestrian_temporal=False,
    )
    pipeline, calls, _, _ = _pipeline(options=options)

    result = pipeline.process_frame(np.zeros((20, 20, 3), dtype=np.uint8))

    assert calls == ["detection", "tracking"]
    assert result.segmentation.message == "Segmentation disabled"
    assert result.depth.message == "Depth disabled"
    assert result.pedestrian_temporal.message == (
        "Temporal pedestrian localization disabled"
    )
