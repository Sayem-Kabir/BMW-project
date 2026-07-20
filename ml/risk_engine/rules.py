"""Module 4B — safe declarative hard-override rule evaluation.

Rules are data, not executable expressions. YAML conditions use an allowlisted
source/field/operator structure and are never passed to ``eval``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from ml.risk_engine.aggregator import RiskFactor, RiskResult, compute_risk, risk_level

DEFAULT_RULES_PATH = Path(__file__).with_name("rules.yaml")

_LEVEL_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
_ALLOWED_SOURCES = {"driver", "road", "telemetry", "derived"}
_ALLOWED_OPERATORS = {"eq", "ne", "lt", "lte", "gt", "gte", "in", "truthy"}


@dataclass(frozen=True)
class RuleCondition:
    source: str
    field: str
    operator: str
    value: Any = None


@dataclass(frozen=True)
class OverrideRule:
    id: str
    description: str
    conditions: tuple[RuleCondition, ...]
    minimum_score: float
    minimum_level: str
    reason: str
    enabled: bool = True


@dataclass(frozen=True)
class AppliedOverride:
    rule_id: str
    reason: str
    previous_score: float
    resulting_score: float
    previous_level: str
    resulting_level: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskDecision:
    """Final risk after Module 4B overrides are applied to a 4A result."""

    base: RiskResult
    score: float
    level: str
    overrides: tuple[AppliedOverride, ...]
    method: str = "weighted_rules_with_overrides_v1"

    @property
    def vehicle_id(self) -> str:
        return self.base.vehicle_id

    @property
    def factors(self) -> tuple[RiskFactor, ...]:
        return self.base.factors

    @property
    def timestamp(self):
        return self.base.timestamp

    @property
    def reasons(self) -> tuple[str, ...]:
        return self.base.reasons + tuple(item.reason for item in self.overrides)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "score": self.score,
            "level": self.level,
            "base_score": self.base.score,
            "base_level": self.base.level,
            "factors": [factor.to_dict() for factor in self.factors],
            "overrides": [item.to_dict() for item in self.overrides],
            "reasons": list(self.reasons),
            "timestamp": self.timestamp.isoformat(),
            "method": self.method,
        }


def load_rules(path: str | Path = DEFAULT_RULES_PATH) -> tuple[OverrideRule, ...]:
    """Load and validate the 4B YAML contract."""
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Risk rules file not found: {source}")
    with source.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, Mapping):
        raise ValueError("Risk rules YAML root must be a mapping")
    if str(payload.get("schema_version", "")).strip() != "1.0":
        raise ValueError("Unsupported risk rules schema_version")
    raw_rules = payload.get("risk_overrides")
    if not isinstance(raw_rules, Sequence) or isinstance(raw_rules, (str, bytes)):
        raise ValueError("risk_overrides must be a list")

    parsed = tuple(_parse_rule(item, index) for index, item in enumerate(raw_rules))
    ids = [rule.id for rule in parsed]
    if len(ids) != len(set(ids)):
        raise ValueError("Risk rule IDs must be unique")
    return parsed


def apply_overrides(
    base: RiskResult,
    driver_state: Mapping[str, Any] | None,
    road_state: Mapping[str, Any] | None,
    telemetry: Mapping[str, Any] | None,
    *,
    rules: Sequence[OverrideRule] | None = None,
) -> RiskDecision:
    """Apply matching rules in declaration order without ever reducing risk."""
    active_rules = tuple(rules) if rules is not None else load_rules()
    context = {
        "driver": driver_state or {},
        "road": road_state or {},
        "telemetry": telemetry or {},
        "derived": _derive_context(road_state or {}),
    }
    score = base.score
    level = base.level
    applied: list[AppliedOverride] = []

    for rule in active_rules:
        if not rule.enabled:
            continue
        matched, evidence = _matches(rule, context)
        if not matched:
            continue
        previous_score = score
        previous_level = level
        score = round(max(score, rule.minimum_score), 1)
        level = _higher_level(
            level,
            rule.minimum_level,
            risk_level(score),
        )
        applied.append(
            AppliedOverride(
                rule_id=rule.id,
                reason=f"OVERRIDE: {rule.reason}",
                previous_score=previous_score,
                resulting_score=score,
                previous_level=previous_level,
                resulting_level=level,
                evidence=evidence,
            )
        )

    return RiskDecision(
        base=base,
        score=score,
        level=level,
        overrides=tuple(applied),
    )


def compute_risk_with_overrides(
    vehicle_id: str,
    driver_state: Mapping[str, Any] | None,
    road_state: Mapping[str, Any] | None,
    telemetry: Mapping[str, Any] | None = None,
    *,
    rules: Sequence[OverrideRule] | None = None,
    timestamp=None,
) -> RiskDecision:
    """Convenience composition of the Module 4A and 4B stages."""
    base = compute_risk(
        vehicle_id,
        driver_state,
        road_state,
        telemetry,
        timestamp=timestamp,
    )
    return apply_overrides(
        base,
        driver_state,
        road_state,
        telemetry,
        rules=rules,
    )


def _parse_rule(raw: Any, index: int) -> OverrideRule:
    if not isinstance(raw, Mapping):
        raise ValueError(f"risk_overrides[{index}] must be a mapping")
    rule_id = str(raw.get("id", "")).strip()
    if not rule_id:
        raise ValueError(f"risk_overrides[{index}].id is required")
    when = raw.get("when")
    if not isinstance(when, Mapping):
        raise ValueError(f"Rule {rule_id!r} requires a when mapping")
    raw_conditions = when.get("all")
    if not isinstance(raw_conditions, Sequence) or isinstance(
        raw_conditions, (str, bytes)
    ):
        raise ValueError(f"Rule {rule_id!r} when.all must be a list")
    if not raw_conditions:
        raise ValueError(f"Rule {rule_id!r} must contain at least one condition")
    conditions = tuple(
        _parse_condition(item, rule_id, condition_index)
        for condition_index, item in enumerate(raw_conditions)
    )

    action = raw.get("action")
    if not isinstance(action, Mapping):
        raise ValueError(f"Rule {rule_id!r} requires an action mapping")
    minimum_score = _bounded_score(action.get("minimum_score"), rule_id)
    minimum_level = str(action.get("minimum_level", "")).strip().upper()
    if minimum_level not in _LEVEL_RANK:
        raise ValueError(f"Rule {rule_id!r} has invalid minimum_level")
    reason = str(action.get("reason", "")).strip()
    if not reason:
        raise ValueError(f"Rule {rule_id!r} action.reason is required")
    enabled = raw.get("enabled", True)
    if not isinstance(enabled, bool):
        raise ValueError(f"Rule {rule_id!r} enabled must be a boolean")

    return OverrideRule(
        id=rule_id,
        description=str(raw.get("description", "")).strip(),
        conditions=conditions,
        minimum_score=minimum_score,
        minimum_level=minimum_level,
        reason=reason,
        enabled=enabled,
    )


def _parse_condition(raw: Any, rule_id: str, index: int) -> RuleCondition:
    if not isinstance(raw, Mapping):
        raise ValueError(f"Rule {rule_id!r} condition {index} must be a mapping")
    source = str(raw.get("source", "")).strip()
    field = str(raw.get("field", "")).strip()
    operator = str(raw.get("operator", "")).strip()
    if source not in _ALLOWED_SOURCES:
        raise ValueError(f"Rule {rule_id!r} condition {index} has invalid source")
    if not field or field.startswith(".") or field.endswith("."):
        raise ValueError(f"Rule {rule_id!r} condition {index} has invalid field")
    if operator not in _ALLOWED_OPERATORS:
        raise ValueError(f"Rule {rule_id!r} condition {index} has invalid operator")
    if operator != "truthy" and "value" not in raw:
        raise ValueError(f"Rule {rule_id!r} condition {index} requires value")
    return RuleCondition(
        source=source,
        field=field,
        operator=operator,
        value=raw.get("value"),
    )


def _matches(
    rule: OverrideRule,
    context: Mapping[str, Mapping[str, Any]],
) -> tuple[bool, dict[str, Any]]:
    evidence: dict[str, Any] = {}
    for condition in rule.conditions:
        actual = _resolve(context[condition.source], condition.field)
        evidence[f"{condition.source}.{condition.field}"] = actual
        if not _compare(actual, condition.operator, condition.value):
            return False, evidence
    return True, evidence


def _resolve(source: Mapping[str, Any], field: str) -> Any:
    current: Any = source
    for segment in field.split("."):
        if not isinstance(current, Mapping) or segment not in current:
            return None
        current = current[segment]
    return current


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "eq":
        if isinstance(expected, bool):
            return actual is expected
        return actual == expected
    if operator == "ne":
        if isinstance(expected, bool):
            return actual is not expected
        return actual != expected
    if operator == "truthy":
        return bool(actual)
    if operator == "in":
        return (
            isinstance(expected, Sequence)
            and not isinstance(expected, (str, bytes))
            and actual in expected
        )
    if actual is None:
        return False
    try:
        left = float(actual)
        right = float(expected)
    except (TypeError, ValueError):
        return False
    if not isfinite(left) or not isfinite(right):
        return False
    return {
        "lt": left < right,
        "lte": left <= right,
        "gt": left > right,
        "gte": left >= right,
    }[operator]


def _derive_context(road_state: Mapping[str, Any]) -> dict[str, Any]:
    objects = road_state.get("objects", ())
    distances: list[float] = []
    if isinstance(objects, Sequence) and not isinstance(objects, (str, bytes)):
        for item in objects:
            if not isinstance(item, Mapping):
                continue
            object_class = str(
                item.get("class", item.get("class_name", ""))
            ).strip().lower()
            if object_class != "pedestrian":
                continue
            try:
                distance = float(item.get("distance_m"))
            except (TypeError, ValueError):
                continue
            if isfinite(distance) and distance >= 0:
                distances.append(distance)
    return {
        "nearest_pedestrian_distance_m": min(distances) if distances else None,
    }


def _bounded_score(value: Any, rule_id: str) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Rule {rule_id!r} has invalid minimum_score") from exc
    if not isfinite(score) or not 0.0 <= score <= 100.0:
        raise ValueError(f"Rule {rule_id!r} minimum_score must be within 0..100")
    return round(score, 1)


def _higher_level(*levels: str) -> str:
    return max(levels, key=lambda item: _LEVEL_RANK[item])

