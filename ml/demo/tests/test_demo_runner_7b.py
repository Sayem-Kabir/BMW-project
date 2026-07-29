"""Module 7B — offline demo runner unit tests (no live API required)."""

from __future__ import annotations

import numpy as np

from ml.demo.demo_runner import (
    PHASE,
    _driver_state_for_frame,
    _encode_jpeg,
    _road_state_for_frame,
    _synthetic_frame,
    _telemetry_for_frame,
)


def test_phase_constant():
    assert PHASE == "7B"


def test_synthetic_frame_is_bgr_image():
    frame = _synthetic_frame(0)
    assert frame.ndim == 3
    assert frame.shape[2] == 3
    assert frame.dtype == np.uint8


def test_encode_jpeg_produces_bytes():
    jpeg = _encode_jpeg(_synthetic_frame(3))
    assert jpeg[:2] == b"\xff\xd8"
    assert len(jpeg) > 500


def test_telemetry_and_states_vary_with_frame():
    t0 = _telemetry_for_frame(0)
    t1 = _telemetry_for_frame(20)
    assert "speed_kmh" in t0 and "latitude" in t0
    assert t0["speed_kmh"] != t1["speed_kmh"] or t0["latitude"] != t1["latitude"]

    drowsy = _driver_state_for_frame(0)
    assert "ear_value" in drowsy
    road = _road_state_for_frame(0)
    assert road["objects"]
