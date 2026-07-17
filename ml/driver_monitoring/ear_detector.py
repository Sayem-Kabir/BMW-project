"""Eye Aspect Ratio (EAR) + frame analysis for drowsiness (Module 1B)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import dlib
import numpy as np
from scipy.spatial import distance

from ml.driver_monitoring.config import (
    DLIB_LANDMARK_PATH,
    EAR_THRESHOLD,
    LEFT_EYE_IDX,
    MAR_THRESHOLD,
    MOUTH_IDX,
    RIGHT_EYE_IDX,
    dlib_landmark_ready,
)
from ml.driver_monitoring.mar_detector import compute_mar

_detector: dlib.fhog_object_detector | None = None
_predictor: dlib.shape_predictor | None = None


@dataclass
class DriverFaceState:
    ear: Optional[float]
    mar: Optional[float]
    is_drowsy: bool
    is_yawning: bool
    face_detected: bool


def compute_ear(eye_points: np.ndarray) -> float:
    """
    Eye Aspect Ratio from 6 eye landmarks.

    EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    where eye_points are ordered [p1..p6] as in Dlib's eye contour.
    """
    if eye_points.shape[0] < 6:
        raise ValueError(f"Expected 6 eye points, got {eye_points.shape[0]}")

    a = distance.euclidean(eye_points[1], eye_points[5])
    b = distance.euclidean(eye_points[2], eye_points[4])
    c = distance.euclidean(eye_points[0], eye_points[3])
    if c <= 0:
        return 0.0
    return float((a + b) / (2.0 * c))


def _landmark_to_array(landmarks: dlib.full_object_detection, indices: list[int]) -> np.ndarray:
    return np.array(
        [(landmarks.part(i).x, landmarks.part(i).y) for i in indices],
        dtype=np.float64,
    )


def _get_models() -> tuple[dlib.fhog_object_detector, dlib.shape_predictor]:
    global _detector, _predictor
    if _detector is not None and _predictor is not None:
        return _detector, _predictor

    if not dlib_landmark_ready():
        raise FileNotFoundError(
            f"Dlib landmark model missing at {DLIB_LANDMARK_PATH}. "
            "Run: python -m ml.driver_monitoring.download_assets"
        )

    _detector = dlib.get_frontal_face_detector()
    _predictor = dlib.shape_predictor(str(DLIB_LANDMARK_PATH))
    return _detector, _predictor


def analyze_frame(
    frame: np.ndarray,
    *,
    ear_threshold: float = EAR_THRESHOLD,
    mar_threshold: float = MAR_THRESHOLD,
) -> DriverFaceState:
    """
    Detect face landmarks and compute EAR/MAR for one BGR frame.

    Returns face_detected=False (and null ratios) when no face is found.
    """
    if frame is None or frame.size == 0:
        return DriverFaceState(
            ear=None,
            mar=None,
            is_drowsy=False,
            is_yawning=False,
            face_detected=False,
        )

    detector, predictor = _get_models()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray, 0)

    if not faces:
        return DriverFaceState(
            ear=None,
            mar=None,
            is_drowsy=False,
            is_yawning=False,
            face_detected=False,
        )

    # Prefer the largest face (closest to cabin camera)
    face = max(faces, key=lambda r: r.width() * r.height())
    landmarks = predictor(gray, face)

    left_eye = _landmark_to_array(landmarks, LEFT_EYE_IDX)
    right_eye = _landmark_to_array(landmarks, RIGHT_EYE_IDX)
    mouth = _landmark_to_array(landmarks, MOUTH_IDX)

    ear = (compute_ear(left_eye) + compute_ear(right_eye)) / 2.0
    mar = compute_mar(mouth)

    return DriverFaceState(
        ear=round(ear, 4),
        mar=round(mar, 4),
        is_drowsy=ear < ear_threshold,
        is_yawning=mar > mar_threshold,
        face_detected=True,
    )
