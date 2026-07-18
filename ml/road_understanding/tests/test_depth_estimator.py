"""Tests for Module 2D pretrained MiDaS depth estimation."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from ml.road_understanding.depth_estimator import (
    DepthCalibration,
    MiDaSDepthEstimator,
    sample_bbox_inverse_depth,
)
from ml.road_understanding.tracker import RoadTracks, TrackedRoadObject


class _DummyDepthModel(torch.nn.Module):
    def forward(self, image: torch.Tensor) -> torch.Tensor:
        height, width = image.shape[-2:]
        values = torch.linspace(
            1.0,
            4.0,
            steps=height * width,
            device=image.device,
        )
        return values.reshape(1, height, width).repeat(image.shape[0], 1, 1)


def _dummy_transform(image: np.ndarray) -> torch.Tensor:
    return (
        torch.from_numpy(np.ascontiguousarray(image))
        .permute(2, 0, 1)
        .unsqueeze(0)
        .float()
        .div(255.0)
    )


def _estimator(*, calibrated: bool = False) -> MiDaSDepthEstimator:
    return MiDaSDepthEstimator(
        device="cpu",
        calibration=DepthCalibration(
            scale=12.0,
            calibrated=calibrated,
        ),
        model=_DummyDepthModel(),
        transform=_dummy_transform,
    )


def test_depth_map_restores_original_frame_resolution():
    estimator = _estimator()
    result = estimator.estimate(np.zeros((20, 30, 3), dtype=np.uint8))

    assert result.is_valid
    assert result.relative_inverse_depth.shape == (20, 30)
    assert result.model_loaded is True
    assert result.normalized_nearness().shape == (20, 30)
    assert result.normalized_nearness().dtype == np.uint8


def test_sample_bbox_uses_inner_median_and_clips_to_frame():
    depth = np.arange(1, 101, dtype=np.float32).reshape(10, 10)

    sampled = sample_bbox_inverse_depth(
        depth,
        [-5.0, -5.0, 6.0, 6.0],
        inset_ratio=0.0,
    )

    assert sampled == pytest.approx(float(np.median(depth[:6, :6])))


def test_sample_bbox_rejects_invalid_or_empty_regions():
    depth = np.ones((10, 10), dtype=np.float32)
    assert sample_bbox_inverse_depth(depth, [5, 5, 4, 8]) is None
    assert sample_bbox_inverse_depth(depth, [20, 20, 30, 30]) is None

    invalid = np.full((10, 10), np.nan, dtype=np.float32)
    assert sample_bbox_inverse_depth(invalid, [0, 0, 10, 10]) is None


def test_calibration_converts_inverse_depth_and_caps_range():
    calibration = DepthCalibration(scale=12.0, offset=0.0, max_distance_m=100.0)
    assert calibration.to_meters(3.0) == pytest.approx(4.0)
    assert calibration.to_meters(0.0) is None

    capped = DepthCalibration(scale=1000.0, max_distance_m=50.0)
    assert capped.to_meters(1.0) == 50.0


def test_estimate_tracks_associates_depth_by_track_id():
    estimator = _estimator(calibrated=True)
    tracks = RoadTracks(
        tracks=[
            TrackedRoadObject(
                track_id=9,
                class_name="car",
                confidence=0.9,
                bbox_xyxy=[5.0, 5.0, 20.0, 15.0],
                confirmed=True,
            )
        ],
        tracker_ready=True,
    )

    result = estimator.estimate_tracks(
        np.zeros((20, 30, 3), dtype=np.uint8),
        tracks,
    )

    assert result.is_valid
    assert len(result.objects) == 1
    assert result.objects[0].id == "track_9"
    assert result.objects[0].relative_inverse_depth is not None
    assert result.objects[0].distance_m is not None
    assert result.objects[0].metric_calibrated is True
    assert result.message is None


def test_uncalibrated_distance_is_explicitly_marked():
    estimator = _estimator(calibrated=False)
    tracks = RoadTracks(
        tracks=[
            TrackedRoadObject(
                track_id=1,
                class_name="pedestrian",
                confidence=0.8,
                bbox_xyxy=[0.0, 0.0, 10.0, 10.0],
            )
        ]
    )

    result = estimator.estimate_tracks(
        np.zeros((10, 10, 3), dtype=np.uint8),
        tracks,
    )

    assert result.objects[0].metric_calibrated is False
    assert result.objects[0].distance_m is None
    assert result.objects[0].relative_inverse_depth is not None
    assert "distance_m stays null" in (result.message or "")


def test_annotate_tracks_copies_depth_onto_tracked_objects():
    estimator = _estimator(calibrated=True)
    tracks = RoadTracks(
        tracks=[
            TrackedRoadObject(
                track_id=4,
                class_name="car",
                confidence=0.95,
                bbox_xyxy=[2.0, 2.0, 12.0, 12.0],
                confirmed=True,
            )
        ],
        tracker_ready=True,
        frame_index=3,
    )

    annotated = estimator.annotate_tracks(
        np.zeros((16, 16, 3), dtype=np.uint8),
        tracks,
    )

    assert annotated.frame_index == 3
    assert annotated.tracks[0].id == "track_4"
    assert annotated.tracks[0].relative_inverse_depth is not None
    assert annotated.tracks[0].distance_m is not None
    assert annotated.tracks[0].distance_calibrated is True
    assert annotated.tracks[0].to_dict()["distance_m"] == annotated.tracks[0].distance_m


def test_empty_frame_returns_clear_error():
    result = _estimator().estimate(np.array([], dtype=np.uint8))
    assert not result.is_valid
    assert result.message == "Empty frame"
