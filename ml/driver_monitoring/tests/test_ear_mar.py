"""Unit tests for Module 1B EAR / MAR geometry (no webcam required)."""

from __future__ import annotations

import numpy as np
import pytest

from ml.driver_monitoring.config import EAR_THRESHOLD, MAR_THRESHOLD
from ml.driver_monitoring.ear_detector import DriverFaceState, analyze_frame, compute_ear
from ml.driver_monitoring.mar_detector import compute_mar


def _open_eye() -> np.ndarray:
    """Synthetic open eye: tall vertical spans relative to width."""
    return np.array(
        [
            [0.0, 0.0],  # p1 left
            [1.0, -2.0],  # p2
            [2.0, -2.0],  # p3
            [3.0, 0.0],  # p4 right
            [2.0, 2.0],  # p5
            [1.0, 2.0],  # p6
        ],
        dtype=np.float64,
    )


def _closed_eye() -> np.ndarray:
    """Synthetic nearly-closed eye: tiny vertical spans."""
    return np.array(
        [
            [0.0, 0.0],
            [1.0, -0.1],
            [2.0, -0.1],
            [3.0, 0.0],
            [2.0, 0.1],
            [1.0, 0.1],
        ],
        dtype=np.float64,
    )


def _closed_mouth() -> np.ndarray:
    """8 inner-mouth points — small vertical opening."""
    return np.array(
        [
            [0.0, 0.0],  # 0 left
            [1.0, -0.2],
            [2.0, -0.2],  # 2 top mid
            [3.0, -0.2],
            [4.0, 0.0],  # 4 right
            [3.0, 0.2],
            [2.0, 0.2],  # 6 bottom mid
            [1.0, 0.2],
        ],
        dtype=np.float64,
    )


def _open_mouth() -> np.ndarray:
    """8 inner-mouth points — large yawn-like opening."""
    return np.array(
        [
            [0.0, 0.0],
            [1.0, -2.0],
            [2.0, -2.5],
            [3.0, -2.0],
            [4.0, 0.0],
            [3.0, 2.0],
            [2.0, 2.5],
            [1.0, 2.0],
        ],
        dtype=np.float64,
    )


def test_compute_ear_open_above_threshold():
    ear = compute_ear(_open_eye())
    assert ear > EAR_THRESHOLD
    assert ear == pytest.approx(4.0 / 3.0, rel=1e-3)


def test_compute_ear_closed_below_threshold():
    ear = compute_ear(_closed_eye())
    assert ear < EAR_THRESHOLD


def test_compute_mar_closed_below_threshold():
    mar = compute_mar(_closed_mouth())
    assert mar < MAR_THRESHOLD


def test_compute_mar_open_above_threshold():
    mar = compute_mar(_open_mouth())
    assert mar > MAR_THRESHOLD


def test_compute_ear_rejects_bad_shape():
    with pytest.raises(ValueError):
        compute_ear(np.zeros((3, 2)))


def test_compute_mar_rejects_bad_shape():
    with pytest.raises(ValueError):
        compute_mar(np.zeros((4, 2)))


def test_analyze_frame_no_face_on_blank():
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    state = analyze_frame(blank)
    assert isinstance(state, DriverFaceState)
    assert state.face_detected is False
    assert state.ear is None
    assert state.mar is None
    assert state.is_drowsy is False
    assert state.is_yawning is False
