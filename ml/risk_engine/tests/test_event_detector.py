"""Module 4D safety event detector tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ml.risk_engine.event_detector import (
    DRIVER_ASLEEP_DROWSY_FRAMES,
    EventDetector,
    compute_ttc_seconds,
    detect_events,
)


def _vehicle(
    *,
    distance_m: float,
    relative_speed_kmh: float,
    track_id: int = 1,
    confirmed: bool = True,
) -> dict:
    return {
        "class": "car",
        "distance_m": distance_m,
        "relative_speed_kmh": relative_speed_kmh,
        "track_id": track_id,
        "confirmed": confirmed,
    }


def test_compute_ttc_seconds_basic() -> None:
    # 10 m at 36 km/h closing -> 1.0 s
    assert compute_ttc_seconds(10.0, 36.0) == 1.0


def test_compute_ttc_returns_none_when_not_closing() -> None:
    assert compute_ttc_seconds(10.0, 0.0) is None
    assert compute_ttc_seconds(10.0, 0.2) is None


def test_near_collision_triggers_below_two_seconds() -> None:
    detector = EventDetector()
    result = detector.process_frame(
        "vehicle-1",
        {},
        {"objects": [_vehicle(distance_m=9.8, relative_speed_kmh=58.0)]},
        {"speed_kmh": 58.0},
        risk_score=94.0,
    )

    assert len(result.events) == 1
    event = result.events[0]
    assert event.event_type == "NEAR_COLLISION"
    assert event.severity == "CRITICAL"
    assert event.evidence["ttc_seconds"] < 2.0
    assert event.telemetry_snapshot["risk_score_at_event"] == 94.0
    assert event.telemetry_snapshot["object_distance_m"] == 9.8


def test_unsafe_following_requires_highway_speed() -> None:
    detector = EventDetector()
    # TTC ~3.0 s: above near-collision, below unsafe-following threshold
    result = detector.process_frame(
        "vehicle-1",
        {},
        {"objects": [_vehicle(distance_m=30.0, relative_speed_kmh=36.0)]},
        {"speed_kmh": 72.0},
    )

    assert [event.event_type for event in result.events] == [
        "UNSAFE_FOLLOWING_DISTANCE"
    ]
    assert result.events[0].severity == "HIGH"


def test_unsafe_following_skipped_at_city_speed() -> None:
    detector = EventDetector()
    result = detector.process_frame(
        "vehicle-1",
        {},
        {"objects": [_vehicle(distance_m=30.0, relative_speed_kmh=36.0)]},
        {"speed_kmh": 40.0},
    )

    assert not any(
        event.event_type == "UNSAFE_FOLLOWING_DISTANCE" for event in result.events
    )


def test_driver_asleep_requires_more_than_sixty_frames() -> None:
    detector = EventDetector()
    asleep = detector.process_frame(
        "vehicle-1",
        {"consecutive_drowsy_frames": DRIVER_ASLEEP_DROWSY_FRAMES + 1},
        {},
        {},
    )
    awake = detector.process_frame(
        "vehicle-2",
        {"consecutive_drowsy_frames": DRIVER_ASLEEP_DROWSY_FRAMES},
        {},
        {},
    )

    assert [event.event_type for event in asleep.events] == ["DRIVER_ASLEEP"]
    assert not any(event.event_type == "DRIVER_ASLEEP" for event in awake.events)


def test_prolonged_phone_usage_after_five_seconds() -> None:
    detector = EventDetector(fps=10.0)
    # 51 frames at 10 fps -> 5.1 s
    events = []
    for _ in range(51):
        result = detector.process_frame(
            "vehicle-1",
            {"phone_detected": True},
            {},
            {},
        )
        events.extend(result.events)

    phone_events = [
        event for event in events if event.event_type == "PROLONGED_PHONE_USAGE"
    ]
    assert phone_events
    assert phone_events[-1].evidence["duration_s"] > 5.0


def test_hard_braking_detects_rapid_deceleration() -> None:
    detector = EventDetector()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    detector.process_frame("vehicle-1", {}, {}, {"speed_kmh": 80.0}, timestamp=start)
    result = detector.process_frame(
        "vehicle-1",
        {},
        {},
        {"speed_kmh": 50.0},
        timestamp=start + timedelta(seconds=1.0),
    )

    assert [event.event_type for event in result.events] == ["SUDDEN_HARD_BRAKING"]
    assert result.events[0].evidence["deceleration_kmh_per_s"] == -30.0


def test_pedestrian_proximity_requires_confirmed_closing_track() -> None:
    detector = EventDetector()
    result = detector.process_frame(
        "vehicle-1",
        {},
        {
            "objects": [
                {
                    "class": "pedestrian",
                    "distance_m": 12.0,
                    "relative_speed_kmh": 4.0,
                    "track_id": 3,
                    "temporally_confirmed": True,
                }
            ]
        },
        {},
    )

    assert [event.event_type for event in result.events] == [
        "PEDESTRIAN_PROXIMITY_HAZARD"
    ]


def test_missing_sources_are_tolerated() -> None:
    result = detect_events("vehicle-1")

    assert result.events == ()
    assert "ttc_vehicle" in result.skipped_detectors
    assert "driver_asleep" in result.skipped_detectors
    assert "prolonged_phone" in result.skipped_detectors
    assert "hard_braking" in result.skipped_detectors
    assert "pedestrian_proximity" in result.skipped_detectors


def test_unconfirmed_vehicle_track_is_ignored_for_ttc() -> None:
    result = detect_events(
        "vehicle-1",
        {},
        {
            "objects": [
                _vehicle(
                    distance_m=5.0,
                    relative_speed_kmh=80.0,
                    confirmed=False,
                )
            ]
        },
        {"speed_kmh": 60.0},
    )

    assert not any(event.event_type.startswith("NEAR") for event in result.events)
    assert "ttc_vehicle" in result.skipped_detectors


def test_reset_clears_phone_and_speed_history() -> None:
    detector = EventDetector()
    detector.process_frame("vehicle-1", {"phone_detected": True}, {}, {})
    detector.process_frame("vehicle-1", {}, {}, {"speed_kmh": 70.0})
    detector.reset()

    result = detector.process_frame(
        "vehicle-1",
        {"phone_detected": True},
        {},
        {"speed_kmh": 40.0},
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert not result.events
    assert detector._phone_frames == 1


def test_empty_vehicle_id_rejected() -> None:
    with pytest.raises(ValueError, match="vehicle_id"):
        detect_events("  ")


def test_result_serializes_to_dict() -> None:
    result = detect_events(
        "vehicle-1",
        {"consecutive_drowsy_frames": DRIVER_ASLEEP_DROWSY_FRAMES + 5},
        {},
        {"speed_kmh": 30.0},
        risk_score=88.0,
    )
    payload = result.to_dict()

    assert payload["vehicle_id"] == "vehicle-1"
    assert payload["events"][0]["event_type"] == "DRIVER_ASLEEP"
    assert "timestamp" in payload
