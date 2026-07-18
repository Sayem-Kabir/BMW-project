"""Tests for redefined Module 2F temporal pedestrian localization."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from ml.road_understanding.config import PEDESTRIAN_TEMPORAL_MODEL_PATH
from ml.road_understanding.pedestrian_temporal import (
    PedestrianTemporalLocalization,
    TemporalPedestrianLocalizer,
)
from ml.road_understanding.tracker import RoadTracks, TrackedRoadObject


class _DummyTemporalModel(torch.nn.Module):
    def __init__(self, confidence: float = 0.9) -> None:
        super().__init__()
        self.confidence = confidence

    def forward(self, frames: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        batch = frames.shape[0]
        bbox = frames.new_tensor([[0.5, 0.5, 0.5, 0.5]]).repeat(batch, 1)
        confidence = frames.new_full((batch,), self.confidence)
        return bbox, confidence


def _localizer(*, confidence: float = 0.9) -> TemporalPedestrianLocalizer:
    return TemporalPedestrianLocalizer(
        sequence_length=3,
        input_size=224,
        confidence_threshold=0.5,
        device="cpu",
        model=_DummyTemporalModel(confidence),
    )


def test_temporal_buffer_warms_before_inference():
    localizer = _localizer()
    frame = np.zeros((100, 200, 3), dtype=np.uint8)

    first = localizer.update(frame)
    second = localizer.update(frame)
    third = localizer.update(frame)

    assert not first.detected
    assert "1/3" in (first.message or "")
    assert "2/3" in (second.message or "")
    assert third.detected
    assert third.frames_used == 3


def test_localize_converts_normalized_xywh_to_frame_xyxy():
    result = _localizer().localize(
        [np.zeros((100, 200, 3), dtype=np.uint8) for _ in range(3)]
    )

    assert result.detected
    assert result.confidence == pytest.approx(0.9)
    assert result.normalized_bbox_xywh == pytest.approx([0.5, 0.5, 0.5, 0.5])
    assert result.bbox_xyxy == pytest.approx([50.0, 25.0, 150.0, 75.0])


def test_below_threshold_does_not_emit_box():
    result = _localizer(confidence=0.2).localize(
        [np.zeros((50, 80, 3), dtype=np.uint8) for _ in range(3)]
    )

    assert not result.detected
    assert result.bbox_xyxy is None
    assert result.normalized_bbox_xywh is not None


def test_associate_tracks_marks_best_pedestrian_and_preserves_prior_fields():
    localizer = _localizer()
    localization = PedestrianTemporalLocalization(
        detected=True,
        confidence=0.88,
        bbox_xyxy=[10.0, 10.0, 40.0, 60.0],
    )
    tracks = RoadTracks(
        tracks=[
            TrackedRoadObject(
                track_id=1,
                class_name="pedestrian",
                confidence=0.8,
                bbox_xyxy=[11.0, 11.0, 41.0, 61.0],
                distance_m=8.0,
                state="VISIBLE",
            ),
            TrackedRoadObject(
                track_id=2,
                class_name="car",
                confidence=0.9,
                bbox_xyxy=[10.0, 10.0, 40.0, 60.0],
            ),
        ],
        frame_index=4,
    )

    annotated = localizer.associate_tracks(localization, tracks)

    pedestrian, car = annotated.tracks
    assert pedestrian.temporally_confirmed
    assert pedestrian.temporal_confidence == pytest.approx(0.88)
    assert pedestrian.temporal_bbox_xyxy == localization.bbox_xyxy
    assert pedestrian.distance_m == 8.0
    assert pedestrian.state == "VISIBLE"
    assert not car.temporally_confirmed
    assert annotated.frame_index == 4


def test_reset_clears_sequence_buffer():
    localizer = _localizer()
    localizer.update(np.zeros((20, 20, 3), dtype=np.uint8))
    assert localizer.buffered_frames == 1
    localizer.reset()
    assert localizer.buffered_frames == 0


def test_new_session_shares_weights_but_has_independent_frame_buffer():
    localizer = _localizer()
    session = localizer.new_session()

    localizer.update(np.zeros((20, 20, 3), dtype=np.uint8))

    assert localizer.buffered_frames == 1
    assert session.buffered_frames == 0
    assert session.is_ready


def test_existing_checkpoint_matches_redefined_architecture():
    if not PEDESTRIAN_TEMPORAL_MODEL_PATH.is_file():
        pytest.skip("Local gitignored temporal pedestrian checkpoint is absent")

    localizer = TemporalPedestrianLocalizer(device="cpu")
    assert localizer.is_ready, localizer._load_error
