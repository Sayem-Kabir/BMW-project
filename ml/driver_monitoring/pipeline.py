"""Combined driver monitoring pipeline — Module 1E.

Merges EAR/MAR (1B), head pose (1C), and YOLO DMS detections (1D)
into a single per-frame analysis with alertness score + risk level.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from ml.driver_monitoring.config import (
    DROWSY_FRAME_COUNT,
    EAR_THRESHOLD,
    YOLO_DRIVER_MODEL_PATH,
)
from ml.driver_monitoring.ear_detector import analyze_frame
from ml.driver_monitoring.head_pose import HeadPoseEstimator, HeadPoseState
from ml.driver_monitoring.yolo_detector import YOLODriverDetector


def risk_level_from_alertness(score: int) -> str:
    if score < 30:
        return "CRITICAL"
    if score < 50:
        return "HIGH"
    if score < 75:
        return "MEDIUM"
    return "LOW"


def compute_alertness_score(
    *,
    ear: float | None,
    distracted: bool,
    phone_detected: bool,
    smoking_detected: bool,
    seatbelt_worn: bool,
    closed_eye_detected: bool,
    yolo_model_loaded: bool,
    consecutive_drowsy_frames: int,
) -> int:
    """Weighted alertness 0–100 (higher = more alert)."""
    alertness = 100

    if ear is not None and ear < EAR_THRESHOLD:
        alertness -= 30
    elif closed_eye_detected:
        # YOLO closed-eye as backup when EAR unavailable / complementary
        alertness -= 20

    if distracted:
        alertness -= 20
    if phone_detected:
        alertness -= 25
    if smoking_detected:
        alertness -= 15
    # Only penalize missing seatbelt when YOLO actually ran
    if yolo_model_loaded and not seatbelt_worn:
        alertness -= 15
    if consecutive_drowsy_frames >= DROWSY_FRAME_COUNT:
        alertness -= 10

    return max(0, min(100, alertness))


class DriverMonitoringPipeline:
    """Stateful frame pipeline for one monitoring session."""

    def __init__(
        self,
        yolo_model_path: str | Path | None = None,
        *,
        head_pose: HeadPoseEstimator | None = None,
        yolo: YOLODriverDetector | None = None,
    ) -> None:
        self.head_pose = head_pose or HeadPoseEstimator()
        self.yolo = yolo or YOLODriverDetector(yolo_model_path or YOLO_DRIVER_MODEL_PATH)
        self._drowsy_frame_count = 0
        self._yawn_count = 0

    def reset(self) -> None:
        """Clear session counters (call when starting a new drive session)."""
        self._drowsy_frame_count = 0
        self._yawn_count = 0

    def close(self) -> None:
        close = getattr(self.head_pose, "close", None)
        if callable(close):
            close()

    def __enter__(self) -> DriverMonitoringPipeline:
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def process_frame(
        self,
        frame: np.ndarray,
        vehicle_id: str = "unknown",
        session_id: str = "unknown",
    ) -> dict[str, Any]:
        face_state = analyze_frame(frame)
        pose: HeadPoseState = self.head_pose.estimate(frame)
        yolo = self.yolo.detect(frame)

        # Drowsy if EAR says so, or YOLO closed-eye with no open-eye
        is_drowsy = face_state.is_drowsy or (
            yolo.closed_eye_detected and not yolo.open_eye_detected
        )

        if is_drowsy:
            self._drowsy_frame_count += 1
        else:
            self._drowsy_frame_count = 0

        if face_state.is_yawning:
            self._yawn_count += 1

        alertness = compute_alertness_score(
            ear=face_state.ear,
            distracted=pose.distracted,
            phone_detected=yolo.phone_detected,
            smoking_detected=yolo.smoking_detected,
            seatbelt_worn=yolo.seatbelt_worn,
            closed_eye_detected=yolo.closed_eye_detected,
            yolo_model_loaded=yolo.model_loaded,
            consecutive_drowsy_frames=self._drowsy_frame_count,
        )

        return {
            "vehicle_id": vehicle_id,
            "session_id": session_id,
            "alertness_score": alertness,
            "risk_level": risk_level_from_alertness(alertness),
            "ear_value": face_state.ear,
            "mar_value": face_state.mar,
            "is_drowsy": is_drowsy,
            "is_yawning": face_state.is_yawning,
            "consecutive_drowsy_frames": self._drowsy_frame_count,
            "yawn_count": self._yawn_count,
            "head_pose": {
                "pitch": pose.pitch,
                "yaw": pose.yaw,
                "roll": pose.roll,
                "distracted": pose.distracted,
                "face_detected": pose.face_detected,
            },
            "phone_detected": yolo.phone_detected,
            "smoking_detected": yolo.smoking_detected,
            "seatbelt_worn": yolo.seatbelt_worn,
            "open_eye_detected": yolo.open_eye_detected,
            "closed_eye_detected": yolo.closed_eye_detected,
            "face_detected": face_state.face_detected or pose.face_detected,
            "yolo_model_loaded": yolo.model_loaded,
            "yolo_message": yolo.message,
        }


_pipeline: DriverMonitoringPipeline | None = None


def get_pipeline() -> DriverMonitoringPipeline:
    """Process-wide lazy pipeline singleton (used by API layer later)."""
    global _pipeline
    if _pipeline is None:
        _pipeline = DriverMonitoringPipeline()
    return _pipeline
