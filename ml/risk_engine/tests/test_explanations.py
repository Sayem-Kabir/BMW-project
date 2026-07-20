"""Module 4E rule-based safety event explanation tests."""

from __future__ import annotations

from ml.risk_engine.explanations import explain_safety_event


def test_near_collision_explanation_includes_ttc_and_ear() -> None:
    text = explain_safety_event(
        "NEAR_COLLISION",
        reason="Near collision",
        evidence={"ttc_seconds": 1.7, "object_class": "car", "distance_m": 9.8},
        telemetry_snapshot={"driver_ear": 0.22, "speed_kmh": 58},
    )

    assert "1.7s" in text
    assert "2.0s" in text
    assert "0.22" in text


def test_driver_asleep_explanation_mentions_frame_threshold() -> None:
    text = explain_safety_event(
        "DRIVER_ASLEEP",
        reason="Driver asleep",
        evidence={"consecutive_drowsy_frames": 72},
        telemetry_snapshot={"driver_ear": 0.18},
    )

    assert "72" in text
    assert "60" in text
    assert "0.18" in text


def test_unknown_event_falls_back_to_reason() -> None:
    assert explain_safety_event("CUSTOM", reason="Custom hazard observed") == (
        "Custom hazard observed"
    )
