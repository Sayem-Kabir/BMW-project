"""Module 4E — deterministic natural-language explanations for safety events.

Rule-based templates keep explanations auditable without requiring an LLM at
runtime. Module 10 can later wrap these strings or replace them via
``ml/xai/nl_explainer.py``.
"""

from __future__ import annotations

from typing import Any, Mapping

from ml.risk_engine.event_detector import (
    DRIVER_ASLEEP_DROWSY_FRAMES,
    HARD_BRAKING_DECEL_KMH_PER_S,
    NEAR_COLLISION_TTC_SECONDS,
    PEDESTRIAN_HAZARD_DISTANCE_M,
    PROLONGED_PHONE_SECONDS,
    UNSAFE_FOLLOWING_MIN_SPEED_KMH,
    UNSAFE_FOLLOWING_TTC_SECONDS,
)

_EXPLANATION_METHOD = "rule_template_v1"


def explain_safety_event(
    event_type: str,
    *,
    reason: str,
    evidence: Mapping[str, Any] | None = None,
    telemetry_snapshot: Mapping[str, Any] | None = None,
) -> str:
    """Return a human-readable XAI string for one detected safety event."""
    evidence = evidence or {}
    telemetry = telemetry_snapshot or {}
    key = str(event_type).strip().upper()

    if key == "NEAR_COLLISION":
        ttc = _first_float(evidence, telemetry, "ttc_seconds")
        distance = _first_float(evidence, telemetry, "object_distance_m", "distance_m")
        obj_class = evidence.get("object_class") or telemetry.get("object_class") or "object"
        parts = [
            f"Near collision detected because TTC dropped to {ttc:.1f}s "
            f"(threshold: {NEAR_COLLISION_TTC_SECONDS:.1f}s)"
            if ttc is not None
            else (
                f"Near collision detected (threshold: "
                f"{NEAR_COLLISION_TTC_SECONDS:.1f}s TTC)"
            )
        ]
        if distance is not None:
            parts.append(f"a {obj_class} was {distance:.1f} m ahead")
        ear = telemetry.get("driver_ear")
        if ear is not None:
            parts.append(f"Driver EAR of {float(ear):.2f} may indicate reduced alertness")
        return ". ".join(parts) + "."

    if key == "DRIVER_ASLEEP":
        frames = evidence.get("consecutive_drowsy_frames")
        ear = telemetry.get("driver_ear")
        base = (
            f"Driver asleep event triggered after {int(frames)} consecutive drowsy frames "
            f"(threshold: {DRIVER_ASLEEP_DROWSY_FRAMES})"
            if frames is not None
            else (
                f"Driver asleep event triggered after sustained drowsiness "
                f"(threshold: {DRIVER_ASLEEP_DROWSY_FRAMES} frames)"
            )
        )
        if ear is not None:
            return f"{base}. EAR of {float(ear):.2f} supports the drowsiness signal."
        return base + "."

    if key == "UNSAFE_FOLLOWING_DISTANCE":
        ttc = _first_float(evidence, telemetry, "ttc_seconds")
        speed = _first_float(evidence, telemetry, "speed_kmh")
        lead = (
            f"TTC of {ttc:.1f}s at {speed:.0f} km/h is below the "
            f"{UNSAFE_FOLLOWING_MIN_SPEED_KMH:.0f} km/h / "
            f"{UNSAFE_FOLLOWING_TTC_SECONDS:.1f}s following-distance limit"
            if ttc is not None and speed is not None
            else (
                f"Following distance is unsafe above "
                f"{UNSAFE_FOLLOWING_MIN_SPEED_KMH:.0f} km/h when TTC falls below "
                f"{UNSAFE_FOLLOWING_TTC_SECONDS:.1f}s"
            )
        )
        return lead + "."

    if key == "SUDDEN_HARD_BRAKING":
        decel = _first_float(evidence, telemetry, "deceleration_kmh_per_s")
        speed = _first_float(evidence, telemetry, "speed_kmh")
        if decel is not None and speed is not None:
            return (
                f"Sudden hard braking detected at {decel:.1f} km/h/s while travelling "
                f"{speed:.0f} km/h (threshold: {HARD_BRAKING_DECEL_KMH_PER_S:.1f} km/h/s)."
            )
        return (
            f"Sudden hard braking exceeded the "
            f"{HARD_BRAKING_DECEL_KMH_PER_S:.1f} km/h/s deceleration threshold."
        )

    if key == "PROLONGED_PHONE_USAGE":
        duration = _first_float(evidence, telemetry, "duration_s")
        if duration is not None:
            return (
                f"Phone usage persisted for {duration:.1f}s "
                f"(threshold: {PROLONGED_PHONE_SECONDS:.1f}s)."
            )
        return (
            f"Phone usage exceeded the {PROLONGED_PHONE_SECONDS:.1f}s continuous-use threshold."
        )

    if key == "PEDESTRIAN_PROXIMITY_HAZARD":
        distance = _first_float(evidence, telemetry, "distance_m")
        rel_speed = _first_float(evidence, telemetry, "relative_speed_kmh")
        if distance is not None and rel_speed is not None:
            return (
                f"Pedestrian proximity hazard: confirmed pedestrian at {distance:.1f} m "
                f"with closing motion ({rel_speed:.1f} km/h) inside the "
                f"{PEDESTRIAN_HAZARD_DISTANCE_M:.0f} m hazard zone."
            )
        if distance is not None:
            return (
                f"Pedestrian proximity hazard: pedestrian within {distance:.1f} m "
                f"(threshold: {PEDESTRIAN_HAZARD_DISTANCE_M:.0f} m)."
            )
        return (
            f"Pedestrian proximity hazard inside the "
            f"{PEDESTRIAN_HAZARD_DISTANCE_M:.0f} m zone with closing motion."
        )

    return reason.strip() or f"{key} safety event detected."


def explanation_method() -> str:
    return _EXPLANATION_METHOD


def _first_float(
    evidence: Mapping[str, Any],
    telemetry: Mapping[str, Any],
    *keys: str,
) -> float | None:
    for mapping in (evidence, telemetry):
        for key in keys:
            value = mapping.get(key)
            if value is None or isinstance(value, bool):
                continue
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                continue
            return parsed
    return None
