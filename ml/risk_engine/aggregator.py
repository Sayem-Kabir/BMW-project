"""Module 4A — pure, explainable weighted risk aggregation.

This module deliberately performs no Redis, database, API, or filesystem I/O.
It converts already-computed driver/road states into a deterministic 0–100
risk score. Module 4B applies hard overrides; Module 4C distributes results.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping, Sequence

RISK_WEIGHTS: dict[str, float] = {
    "drowsy": 0.35,
    "phone_usage": 0.25,
    "no_seatbelt": 0.15,
    "pedestrian_proximity": 0.15,
    "aggressive_vehicle": 0.10,
}

PEDESTRIAN_DISTANCE_THRESHOLD_M = 10.0
AGGRESSIVE_RELATIVE_SPEED_THRESHOLD_KMH = 20.0

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

_VEHICLE_CLASSES = {
    "car",
    "truck",
    "bus",
    "motorcycle",
    "vehicle",
}


@dataclass(frozen=True)
class RiskFactor:
    """One triggered input and its additive contribution."""

    key: str
    label: str
    weight: float
    contribution: float
    reason: str
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RiskResult:
    """Stable output contract for one Module 4A evaluation."""

    vehicle_id: str
    score: float
    level: str
    factors: tuple[RiskFactor, ...]
    timestamp: datetime
    method: str = "weighted_rules_v1"

    @property
    def reasons(self) -> tuple[str, ...]:
        return tuple(factor.reason for factor in self.factors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "score": self.score,
            "level": self.level,
            "factors": [factor.to_dict() for factor in self.factors],
            "reasons": list(self.reasons),
            "timestamp": self.timestamp.isoformat(),
            "method": self.method,
        }


def risk_level(score: float) -> str:
    """Map any finite numeric score onto the documented inclusive bands."""
    value = _finite_float(score, "score")
    value = max(0.0, min(100.0, value))
    if value <= 40.0:
        return "LOW"
    if value <= 65.0:
        return "MEDIUM"
    if value <= 85.0:
        return "HIGH"
    return "CRITICAL"


def compute_risk(
    vehicle_id: str,
    driver_state: Mapping[str, Any] | None,
    road_state: Mapping[str, Any] | None,
    telemetry: Mapping[str, Any] | None = None,
    *,
    timestamp: datetime | None = None,
) -> RiskResult:
    """Compute additive risk from existing pipeline outputs.

    ``telemetry`` is accepted now to establish the cross-phase contract, but
    Module 4A has no weighted telemetry-only factor. Speed-dependent hard
    overrides belong to Module 4B.
    """
    del telemetry
    identity = str(vehicle_id).strip()
    if not identity:
        raise ValueError("vehicle_id must not be empty")

    driver = driver_state or {}
    road = road_state or {}
    factors: list[RiskFactor] = []

    if bool(driver.get("is_drowsy", False)):
        ear = _optional_float(driver.get("ear_value"))
        evidence = {"is_drowsy": True}
        if ear is not None:
            evidence["ear_value"] = ear
        detail = f" (EAR {ear:.3f})" if ear is not None else ""
        factors.append(
            _factor(
                "drowsy",
                "Driver drowsiness",
                f"Drowsiness detected{detail}",
                evidence,
            )
        )

    if bool(driver.get("phone_detected", False)):
        confidence = _optional_float(
            driver.get("phone_confidence", driver.get("phone_detection_confidence"))
        )
        evidence = {"phone_detected": True}
        if confidence is not None:
            evidence["confidence"] = confidence
        factors.append(
            _factor(
                "phone_usage",
                "Phone usage",
                "Phone usage detected",
                evidence,
            )
        )

    if driver.get("seatbelt_worn", True) is False:
        factors.append(
            _factor(
                "no_seatbelt",
                "Seatbelt not worn",
                "Seatbelt not worn",
                {"seatbelt_worn": False},
            )
        )

    objects = _road_objects(road)
    pedestrians = [
        (item, distance)
        for item in objects
        if _object_class(item) == "pedestrian"
        and (distance := _object_distance(item)) is not None
        and distance < PEDESTRIAN_DISTANCE_THRESHOLD_M
    ]
    if pedestrians:
        nearest_item, nearest_distance = min(pedestrians, key=lambda pair: pair[1])
        factors.append(
            _factor(
                "pedestrian_proximity",
                "Pedestrian proximity",
                f"Pedestrian within {nearest_distance:.1f} m",
                {
                    "distance_m": nearest_distance,
                    "threshold_m": PEDESTRIAN_DISTANCE_THRESHOLD_M,
                    "track_id": nearest_item.get("track_id"),
                },
            )
        )

    aggressive = [
        (item, speed)
        for item in objects
        if _object_class(item) in _VEHICLE_CLASSES
        and (speed := _relative_speed(item)) is not None
        and speed > AGGRESSIVE_RELATIVE_SPEED_THRESHOLD_KMH
    ]
    if aggressive:
        fastest_item, relative_speed = max(aggressive, key=lambda pair: pair[1])
        factors.append(
            _factor(
                "aggressive_vehicle",
                "Aggressive vehicle nearby",
                f"Nearby vehicle closing at {relative_speed:.1f} km/h",
                {
                    "relative_speed_kmh": relative_speed,
                    "threshold_kmh": AGGRESSIVE_RELATIVE_SPEED_THRESHOLD_KMH,
                    "object_class": _object_class(fastest_item),
                    "track_id": fastest_item.get("track_id"),
                },
            )
        )

    score = round(min(100.0, sum(item.contribution for item in factors)), 1)
    evaluated_at = timestamp or datetime.now(timezone.utc)
    if evaluated_at.tzinfo is None:
        evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)

    return RiskResult(
        vehicle_id=identity,
        score=score,
        level=risk_level(score),
        factors=tuple(factors),
        timestamp=evaluated_at,
    )


def _factor(
    key: str,
    label: str,
    reason: str,
    evidence: dict[str, Any],
) -> RiskFactor:
    weight = RISK_WEIGHTS[key]
    return RiskFactor(
        key=key,
        label=label,
        weight=weight,
        contribution=round(weight * 100.0, 1),
        reason=reason,
        evidence=evidence,
    )


def _road_objects(road_state: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    raw = road_state.get("objects", ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    return tuple(item for item in raw if isinstance(item, Mapping))


def _object_class(item: Mapping[str, Any]) -> str:
    return str(item.get("class", item.get("class_name", ""))).strip().lower()


def _object_distance(item: Mapping[str, Any]) -> float | None:
    return _optional_non_negative_float(item.get("distance_m"))


def _relative_speed(item: Mapping[str, Any]) -> float | None:
    value = item.get(
        "relative_speed_kmh",
        item.get("closing_speed_kmh", item.get("estimated_relative_speed_kmh")),
    )
    return _optional_non_negative_float(value)


def _optional_non_negative_float(value: Any) -> float | None:
    parsed = _optional_float(value)
    return parsed if parsed is not None and parsed >= 0.0 else None


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _finite_float(value: Any, name: str) -> float:
    parsed = _optional_float(value)
    if parsed is None:
        raise ValueError(f"{name} must be a finite number")
    return parsed

