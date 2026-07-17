"""Tests for Module 1E combined driver monitoring pipeline."""

from __future__ import annotations

import numpy as np

from ml.driver_monitoring.head_pose import HeadPoseState
from ml.driver_monitoring.pipeline import (
    DriverMonitoringPipeline,
    compute_alertness_score,
    risk_level_from_alertness,
)
from ml.driver_monitoring.yolo_detector import DriverObjectDetections


def test_risk_level_bands():
    assert risk_level_from_alertness(90) == "LOW"
    assert risk_level_from_alertness(70) == "MEDIUM"
    assert risk_level_from_alertness(40) == "HIGH"
    assert risk_level_from_alertness(10) == "CRITICAL"


def test_alertness_penalties_stack():
    score = compute_alertness_score(
        ear=0.20,
        distracted=True,
        phone_detected=True,
        smoking_detected=False,
        seatbelt_worn=False,
        closed_eye_detected=False,
        yolo_model_loaded=True,
        consecutive_drowsy_frames=0,
    )
    # 100 - 30 (ear) - 20 (pose) - 25 (phone) - 15 (seatbelt) = 10
    assert score == 10
    assert risk_level_from_alertness(score) == "CRITICAL"


def test_seatbelt_not_penalized_when_yolo_missing():
    score = compute_alertness_score(
        ear=0.30,
        distracted=False,
        phone_detected=False,
        smoking_detected=False,
        seatbelt_worn=False,
        closed_eye_detected=False,
        yolo_model_loaded=False,
        consecutive_drowsy_frames=0,
    )
    assert score == 100


class _FakePose:
    def estimate(self, frame):
        return HeadPoseState(
            pitch=0.0, yaw=0.0, roll=0.0, distracted=False, face_detected=False
        )

    def close(self):
        pass


class _FakeYolo:
    def detect(self, frame):
        return DriverObjectDetections(model_loaded=True, seatbelt_worn=True)


def test_pipeline_blank_frame_with_fakes():
    # Avoid loading MediaPipe / Dlib / YOLO — still call real analyze_frame on blank.
    pipe = DriverMonitoringPipeline(head_pose=_FakePose(), yolo=_FakeYolo())
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    out = pipe.process_frame(blank, vehicle_id="v1", session_id="s1")

    assert out["vehicle_id"] == "v1"
    assert out["session_id"] == "s1"
    assert out["alertness_score"] == 100
    assert out["risk_level"] == "LOW"
    assert out["face_detected"] is False
    assert out["phone_detected"] is False
    assert out["consecutive_drowsy_frames"] == 0
    assert "head_pose" in out
    pipe.close()


def test_pipeline_reset_counters():
    pipe = DriverMonitoringPipeline(head_pose=_FakePose(), yolo=_FakeYolo())
    pipe._drowsy_frame_count = 12
    pipe._yawn_count = 3
    pipe.reset()
    assert pipe._drowsy_frame_count == 0
    assert pipe._yawn_count == 0
