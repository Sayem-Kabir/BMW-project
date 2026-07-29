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
    FACE_GATE_ENABLED,
    FACE_GATE_MIN_PIXELS,
    FRAME_SAMPLE_EVERY,
    YOLO_DRIVER_MODEL_PATH,
)
from ml.driver_monitoring.ear_detector import analyze_frame
from ml.driver_monitoring.head_pose import HeadPoseEstimator, HeadPoseState
from ml.driver_monitoring.yolo_detector import YOLODriverDetector


def _cheap_face_present(frame: np.ndarray) -> bool:
    """Low-cost presence proxy before MediaPipe/Dlib (Phase 13 face gate)."""
    if frame is None or getattr(frame, "size", 0) == 0:
        return False
    try:
        # Downsample + luminance variance — empty cabin frames are near-uniform
        small = frame[::8, ::8]
        if small.ndim == 3:
            gray = small.mean(axis=2)
        else:
            gray = small.astype(float)
        return float(np.var(gray)) >= float(FACE_GATE_MIN_PIXELS)
    except Exception:  # noqa: BLE001
        return True


def _optical_flow_magnitude(
    prev: np.ndarray | None, curr: np.ndarray
) -> float | None:
    """Farneback mean flow magnitude between frames (Phase 13 optical flow)."""
    if prev is None or curr is None:
        return None
    try:
        import cv2

        def _gray(img: np.ndarray) -> np.ndarray:
            small = img[::4, ::4]
            if small.ndim == 3:
                return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            return small.astype(np.uint8)

        g0, g1 = _gray(prev), _gray(curr)
        if g0.shape != g1.shape:
            g1 = cv2.resize(g1, (g0.shape[1], g0.shape[0]))
        flow = cv2.calcOpticalFlowFarneback(
            g0, g1, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        mag = float(np.mean(np.linalg.norm(flow, axis=2)))
        return mag
    except Exception:  # noqa: BLE001
        return None


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
        self._frame_idx = 0
        self._last_result: dict[str, Any] | None = None
        self._last_frame: np.ndarray | None = None

    def reset(self) -> None:
        """Clear session counters (call when starting a new drive session)."""
        self._drowsy_frame_count = 0
        self._yawn_count = 0
        self._frame_idx = 0
        self._last_result = None
        self._last_frame = None

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
        self._frame_idx += 1
        sample_every = max(1, int(FRAME_SAMPLE_EVERY))
        # Phase 13 adaptive sampling: optical-flow motion check between keyframes
        if (
            self._last_result is not None
            and sample_every > 1
            and (self._frame_idx % sample_every) != 1
        ):
            reused = dict(self._last_result)
            reused["vehicle_id"] = vehicle_id
            reused["session_id"] = session_id
            flow_mag = _optical_flow_magnitude(self._last_frame, frame)
            reused["inference_mode"] = "optical_flow_hold" if flow_mag is not None else "interpolated"
            reused["optical_flow_magnitude"] = flow_mag
            reused["frame_idx"] = self._frame_idx
            # Large scene change → force full inference next
            if flow_mag is not None and flow_mag > 8.0:
                pass  # fall through to full inference below
            else:
                return reused

        if FACE_GATE_ENABLED and not _cheap_face_present(frame):
            empty = {
                "vehicle_id": vehicle_id,
                "session_id": session_id,
                "alertness_score": 100,
                "risk_level": "LOW",
                "ear_value": None,
                "mar_value": None,
                "is_drowsy": False,
                "is_yawning": False,
                "consecutive_drowsy_frames": 0,
                "yawn_count": self._yawn_count,
                "head_pose": {
                    "pitch": 0.0,
                    "yaw": 0.0,
                    "roll": 0.0,
                    "distracted": False,
                    "face_detected": False,
                },
                "phone_detected": False,
                "smoking_detected": False,
                "seatbelt_worn": True,
                "open_eye_detected": False,
                "closed_eye_detected": False,
                "face_detected": False,
                "yolo_model_loaded": getattr(self.yolo, "model_loaded", False),
                "yolo_message": "face_gate_skip",
                "inference_mode": "face_gate_skip",
                "frame_idx": self._frame_idx,
            }
            self._last_result = empty
            return empty

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

        result = {
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
            "inference_mode": "full",
            "frame_idx": self._frame_idx,
        }
        self._last_result = result
        try:
            self._last_frame = frame.copy()
        except Exception:  # noqa: BLE001
            self._last_frame = frame
        return result


_pipeline: DriverMonitoringPipeline | None = None


def get_pipeline() -> DriverMonitoringPipeline:
    """Process-wide lazy pipeline singleton (used by API layer later)."""
    global _pipeline
    if _pipeline is None:
        _pipeline = DriverMonitoringPipeline()
    return _pipeline
