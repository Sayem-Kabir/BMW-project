"""Module 4A weighted risk aggregation tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ml.risk_engine import RISK_WEIGHTS, compute_risk, risk_level


def test_no_triggers_is_low_zero_risk() -> None:
    result = compute_risk(
        "vehicle-1",
        {"is_drowsy": False, "phone_detected": False, "seatbelt_worn": True},
        {"objects": []},
    )

    assert result.score == 0.0
    assert result.level == "LOW"
    assert result.factors == ()
    assert result.reasons == ()
    assert result.timestamp.tzinfo is not None


def test_driver_factors_are_additive_and_explainable() -> None:
    result = compute_risk(
        "vehicle-1",
        {
            "is_drowsy": True,
            "ear_value": 0.19,
            "phone_detected": True,
            "phone_confidence": 0.92,
            "seatbelt_worn": False,
        },
        {},
    )

    assert result.score == 75.0
    assert result.level == "HIGH"
    assert [item.key for item in result.factors] == [
        "drowsy",
        "phone_usage",
        "no_seatbelt",
    ]
    assert sum(item.contribution for item in result.factors) == 75.0
    assert result.factors[0].evidence["ear_value"] == 0.19
    assert "EAR 0.190" in result.reasons[0]


def test_nearest_pedestrian_contributes_only_once() -> None:
    result = compute_risk(
        "vehicle-1",
        {},
        {
            "objects": [
                {"class": "pedestrian", "distance_m": 8.5, "track_id": 1},
                {"class_name": "pedestrian", "distance_m": 4.2, "track_id": 2},
                {"class": "pedestrian", "distance_m": 12.0, "track_id": 3},
            ]
        },
    )

    assert result.score == 15.0
    assert len(result.factors) == 1
    factor = result.factors[0]
    assert factor.key == "pedestrian_proximity"
    assert factor.evidence["distance_m"] == 4.2
    assert factor.evidence["track_id"] == 2


def test_aggressive_vehicle_uses_largest_closing_speed() -> None:
    result = compute_risk(
        "vehicle-1",
        {},
        {
            "objects": [
                {"class": "car", "relative_speed_kmh": 21.0, "track_id": 8},
                {"class": "truck", "closing_speed_kmh": 42.5, "track_id": 9},
                {"class": "bicycle", "relative_speed_kmh": 80.0},
            ]
        },
    )

    assert result.score == 10.0
    factor = result.factors[0]
    assert factor.key == "aggressive_vehicle"
    assert factor.evidence["relative_speed_kmh"] == 42.5
    assert factor.evidence["object_class"] == "truck"


def test_all_factors_total_100_and_become_critical() -> None:
    result = compute_risk(
        "vehicle-1",
        {
            "is_drowsy": True,
            "phone_detected": True,
            "seatbelt_worn": False,
        },
        {
            "objects": [
                {"class": "pedestrian", "distance_m": 2.0},
                {"class": "car", "relative_speed_kmh": 50.0},
            ]
        },
    )

    assert sum(RISK_WEIGHTS.values()) == pytest.approx(1.0)
    assert result.score == 100.0
    assert result.level == "CRITICAL"
    assert len(result.factors) == 5


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (-10, "LOW"),
        (0, "LOW"),
        (40, "LOW"),
        (40.1, "MEDIUM"),
        (65, "MEDIUM"),
        (65.1, "HIGH"),
        (85, "HIGH"),
        (85.1, "CRITICAL"),
        (100, "CRITICAL"),
        (120, "CRITICAL"),
    ],
)
def test_risk_level_boundaries(score: float, expected: str) -> None:
    assert risk_level(score) == expected


@pytest.mark.parametrize("score", [float("nan"), float("inf"), "bad", None])
def test_risk_level_rejects_non_finite_values(score: object) -> None:
    with pytest.raises(ValueError, match="finite number"):
        risk_level(score)  # type: ignore[arg-type]


def test_bad_object_values_are_ignored_and_inputs_are_not_mutated() -> None:
    driver = {"seatbelt_worn": True}
    road = {
        "objects": [
            {"class": "pedestrian", "distance_m": "unknown"},
            {"class": "car", "relative_speed_kmh": float("nan")},
            "not-an-object",
        ]
    }
    original_objects = list(road["objects"])

    result = compute_risk("vehicle-1", driver, road)

    assert result.score == 0.0
    assert road["objects"] == original_objects
    assert driver == {"seatbelt_worn": True}


def test_result_serialization_and_explicit_timestamp() -> None:
    timestamp = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    result = compute_risk(
        "vehicle-1",
        {"phone_detected": True},
        {},
        timestamp=timestamp,
    )

    payload = result.to_dict()
    assert payload["vehicle_id"] == "vehicle-1"
    assert payload["score"] == 25.0
    assert payload["level"] == "LOW"
    assert payload["timestamp"] == timestamp.isoformat()
    assert payload["method"] == "weighted_rules_v1"
    assert payload["factors"][0]["key"] == "phone_usage"


def test_empty_vehicle_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="vehicle_id"):
        compute_risk("  ", {}, {})

