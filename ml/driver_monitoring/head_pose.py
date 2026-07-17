"""Head pose estimation via MediaPipe Face Mesh + solvePnP (Module 1C)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from ml.driver_monitoring.config import (
    DISTRACTION_PITCH_THRESHOLD,
    DISTRACTION_YAW_THRESHOLD,
)

# Standard 3D face model points (mm) aligned with MediaPipe landmark indices below
FACE_3D_MODEL = np.array(
    [
        [0.0, 0.0, 0.0],  # nose tip
        [0.0, -330.0, -65.0],  # chin
        [-225.0, 170.0, -135.0],  # left eye outer corner
        [225.0, 170.0, -135.0],  # right eye outer corner
        [-150.0, -150.0, -125.0],  # left mouth corner
        [150.0, -150.0, -125.0],  # right mouth corner
    ],
    dtype=np.float64,
)

# MediaPipe Face Mesh indices matching FACE_3D_MODEL order
FACE_LM_INDICES = (4, 152, 263, 33, 287, 57)


@dataclass
class HeadPoseState:
    pitch: float
    yaw: float
    roll: float
    distracted: bool
    face_detected: bool


def _no_face_state() -> HeadPoseState:
    return HeadPoseState(
        pitch=0.0,
        yaw=0.0,
        roll=0.0,
        distracted=False,
        face_detected=False,
    )


def _is_distracted(
    pitch: float,
    yaw: float,
    *,
    pitch_threshold: float,
    yaw_threshold: float,
) -> bool:
    return abs(pitch) > pitch_threshold or abs(yaw) > yaw_threshold


class HeadPoseEstimator:
    """Estimates head pitch/yaw/roll and distraction from a BGR frame."""

    def __init__(
        self,
        *,
        pitch_threshold: float = DISTRACTION_PITCH_THRESHOLD,
        yaw_threshold: float = DISTRACTION_YAW_THRESHOLD,
        min_detection_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        import mediapipe as mp

        self._pitch_threshold = pitch_threshold
        self._yaw_threshold = yaw_threshold
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def close(self) -> None:
        self._face_mesh.close()

    def __enter__(self) -> HeadPoseEstimator:
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def estimate(self, frame: np.ndarray) -> HeadPoseState:
        if frame is None or frame.size == 0:
            return _no_face_state()

        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self._face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return _no_face_state()

        landmarks = results.multi_face_landmarks[0].landmark
        face_2d = np.array(
            [(landmarks[i].x * w, landmarks[i].y * h) for i in FACE_LM_INDICES],
            dtype=np.float64,
        )

        focal_length = float(w)
        cam_matrix = np.array(
            [
                [focal_length, 0.0, w / 2.0],
                [0.0, focal_length, h / 2.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        ok, rvec, _tvec = cv2.solvePnP(
            FACE_3D_MODEL,
            face_2d,
            cam_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not ok:
            return _no_face_state()

        rmat, _ = cv2.Rodrigues(rvec)
        angles, *_ = cv2.RQDecomp3x3(rmat)
        pitch = float(angles[0] * 360)
        yaw = float(angles[1] * 360)
        roll = float(angles[2] * 360)

        distracted = _is_distracted(
            pitch,
            yaw,
            pitch_threshold=self._pitch_threshold,
            yaw_threshold=self._yaw_threshold,
        )

        return HeadPoseState(
            pitch=round(pitch, 2),
            yaw=round(yaw, 2),
            roll=round(roll, 2),
            distracted=distracted,
            face_detected=True,
        )


_estimator: HeadPoseEstimator | None = None


def get_head_pose_estimator() -> HeadPoseEstimator:
    global _estimator
    if _estimator is None:
        _estimator = HeadPoseEstimator()
    return _estimator


def estimate_head_pose(frame: np.ndarray) -> HeadPoseState:
    """Convenience wrapper using a process-wide lazy HeadPoseEstimator."""
    return get_head_pose_estimator().estimate(frame)
