"""Tests for Module 1C head pose estimation."""

from __future__ import annotations

import numpy as np
import pytest

from ml.driver_monitoring.config import (
    DISTRACTION_PITCH_THRESHOLD,
    DISTRACTION_YAW_THRESHOLD,
)
from ml.driver_monitoring.head_pose import (
    HeadPoseEstimator,
    HeadPoseState,
    _is_distracted,
    estimate_head_pose,
)

mediapipe = pytest.importorskip("mediapipe")


def test_is_distracted_pitch():
    assert _is_distracted(
        DISTRACTION_PITCH_THRESHOLD + 1,
        0.0,
        pitch_threshold=DISTRACTION_PITCH_THRESHOLD,
        yaw_threshold=DISTRACTION_YAW_THRESHOLD,
    )


def test_is_distracted_yaw():
    assert _is_distracted(
        0.0,
        -(DISTRACTION_YAW_THRESHOLD + 1),
        pitch_threshold=DISTRACTION_PITCH_THRESHOLD,
        yaw_threshold=DISTRACTION_YAW_THRESHOLD,
    )


def test_is_not_distracted_when_centered():
    assert not _is_distracted(
        0.0,
        0.0,
        pitch_threshold=DISTRACTION_PITCH_THRESHOLD,
        yaw_threshold=DISTRACTION_YAW_THRESHOLD,
    )


def test_estimate_blank_frame_no_face():
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    with HeadPoseEstimator() as estimator:
        state = estimator.estimate(blank)
    assert isinstance(state, HeadPoseState)
    assert state.face_detected is False
    assert state.pitch == 0.0
    assert state.yaw == 0.0
    assert state.roll == 0.0
    assert state.distracted is False


def test_estimate_head_pose_convenience():
    blank = np.zeros((240, 320, 3), dtype=np.uint8)
    state = estimate_head_pose(blank)
    assert state.face_detected is False
