"""Module 4B declarative hard-override tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from ml.risk_engine import (
    OverrideRule,
    RuleCondition,
    compute_risk_with_overrides,
    load_rules,
)


def _pedestrian(distance: float) -> dict:
    return {"class": "pedestrian", "distance_m": distance, "track_id": 7}


def test_default_yaml_loads_expected_rules() -> None:
    rules = load_rules()

    assert [rule.id for rule in rules] == [
        "drowsy_pedestrian_path",
        "unbelted_highway_speed",
        "phone_in_school_zone",
    ]
    assert all(rule.enabled for rule in rules)
    assert rules[0].minimum_score == 100.0
    assert rules[0].minimum_level == "CRITICAL"


def test_drowsy_pedestrian_forces_critical_100() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"is_drowsy": True, "seatbelt_worn": True},
        {"objects": [_pedestrian(4.5)]},
        {"speed_kmh": 20.0},
    )

    # Phase 13: CRITICAL override short-circuits before full 4A scoring
    assert decision.method == "override_first_short_circuit_v1"
    assert decision.base.method == "override_gate_v1"
    assert decision.score == 100.0
    assert decision.level == "CRITICAL"
    assert [item.rule_id for item in decision.overrides] == [
        "drowsy_pedestrian_path"
    ]
    assert decision.overrides[0].evidence[
        "derived.nearest_pedestrian_distance_m"
    ] == 4.5
    assert decision.reasons[-1].startswith("OVERRIDE:")


def test_pedestrian_threshold_is_strictly_less_than_ten() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"is_drowsy": True},
        {"objects": [_pedestrian(10.0)]},
        {},
    )

    assert decision.base.score == 35.0
    assert decision.score == 35.0
    assert decision.level == "LOW"
    assert decision.overrides == ()


def test_unbelted_highway_speed_sets_high_floor() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"seatbelt_worn": False},
        {},
        {"speed_kmh": 72.0},
    )

    assert decision.base.score == 15.0
    assert decision.base.level == "LOW"
    assert decision.score == 75.0
    assert decision.level == "HIGH"
    assert decision.overrides[0].rule_id == "unbelted_highway_speed"


def test_highway_threshold_does_not_match_at_sixty() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"seatbelt_worn": False},
        {},
        {"speed_kmh": 60.0},
    )

    assert decision.score == 15.0
    assert decision.overrides == ()


def test_phone_in_school_zone_forces_critical() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"phone_detected": True},
        {},
        {"school_zone": True},
    )

    assert decision.method == "override_first_short_circuit_v1"
    assert decision.score == 100.0
    assert decision.level == "CRITICAL"
    assert decision.overrides[0].rule_id == "phone_in_school_zone"


def test_missing_telemetry_never_matches_speed_or_zone_rules() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"phone_detected": True, "seatbelt_worn": False},
        {},
        None,
    )

    assert decision.base.score == 40.0
    assert decision.score == 40.0
    assert decision.overrides == ()


def test_boolean_conditions_do_not_accept_numeric_lookalikes() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"phone_detected": 1},
        {},
        {"school_zone": 1},
    )

    # 4A treats truthy detector output as a weighted factor, but safety
    # overrides require the explicit boolean contract.
    assert decision.base.score == 25.0
    assert decision.overrides == ()


def test_multiple_overrides_apply_in_order_without_downgrading() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {
            "is_drowsy": True,
            "phone_detected": True,
            "seatbelt_worn": False,
        },
        {"objects": [_pedestrian(3.0)]},
        {"speed_kmh": 80.0, "school_zone": True},
    )

    assert decision.method == "override_first_short_circuit_v1"
    assert decision.score == 100.0
    assert decision.level == "CRITICAL"
    assert [item.rule_id for item in decision.overrides] == [
        "drowsy_pedestrian_path",
        "unbelted_highway_speed",
        "phone_in_school_zone",
    ]
    assert decision.overrides[1].previous_score == 100.0
    assert decision.overrides[1].resulting_score == 100.0
    assert decision.overrides[1].resulting_level == "CRITICAL"


def test_disabled_custom_rule_is_skipped() -> None:
    rule = OverrideRule(
        id="disabled",
        description="disabled test",
        conditions=(RuleCondition("driver", "is_drowsy", "eq", True),),
        minimum_score=100.0,
        minimum_level="CRITICAL",
        reason="Must not apply",
        enabled=False,
    )
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"is_drowsy": True},
        {},
        {},
        rules=[rule],
    )

    assert decision.score == 35.0
    assert decision.overrides == ()


def test_decision_serialization_contains_base_and_override_audit() -> None:
    decision = compute_risk_with_overrides(
        "vehicle-1",
        {"seatbelt_worn": False},
        {},
        {"speed_kmh": 90},
    )
    payload = decision.to_dict()

    assert payload["score"] == 75.0
    assert payload["base_score"] == 15.0
    assert payload["base_level"] == "LOW"
    assert payload["method"] == "weighted_rules_with_overrides_v1"
    assert payload["overrides"][0]["previous_score"] == 15.0
    assert payload["overrides"][0]["resulting_score"] == 75.0


@pytest.mark.parametrize(
    ("yaml_body", "message"),
    [
        ("schema_version: '2.0'\nrisk_overrides: []\n", "schema_version"),
        (
            "schema_version: '1.0'\nrisk_overrides:\n"
            "  - id: bad\n    when:\n      all:\n"
            "        - {source: os, field: system, operator: eq, value: x}\n"
            "    action: {minimum_score: 50, minimum_level: HIGH, reason: bad}\n",
            "invalid source",
        ),
        (
            "schema_version: '1.0'\nrisk_overrides:\n"
            "  - id: bad\n    when:\n      all:\n"
            "        - {source: driver, field: is_drowsy, operator: execute, value: true}\n"
            "    action: {minimum_score: 50, minimum_level: HIGH, reason: bad}\n",
            "invalid operator",
        ),
        (
            "schema_version: '1.0'\nrisk_overrides:\n"
            "  - id: bad\n    when:\n      all:\n"
            "        - {source: driver, field: is_drowsy, operator: eq, value: true}\n"
            "    action: {minimum_score: 101, minimum_level: HIGH, reason: bad}\n",
            "within 0..100",
        ),
        (
            "schema_version: '1.0'\nrisk_overrides:\n"
            "  - id: bad\n    enabled: 'false'\n    when:\n      all:\n"
            "        - {source: driver, field: is_drowsy, operator: eq, value: true}\n"
            "    action: {minimum_score: 100, minimum_level: CRITICAL, reason: bad}\n",
            "enabled must be a boolean",
        ),
    ],
)
def test_malformed_or_unsafe_yaml_is_rejected(
    tmp_path: Path,
    yaml_body: str,
    message: str,
) -> None:
    path = tmp_path / "rules.yaml"
    path.write_text(yaml_body, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_rules(path)


def test_duplicate_rule_ids_are_rejected(tmp_path: Path) -> None:
    rule = """
  - id: duplicate
    when:
      all:
        - {source: driver, field: is_drowsy, operator: eq, value: true}
    action: {minimum_score: 100, minimum_level: CRITICAL, reason: duplicate}
"""
    path = tmp_path / "rules.yaml"
    path.write_text(
        f"schema_version: '1.0'\nrisk_overrides:\n{rule}{rule}",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unique"):
        load_rules(path)

