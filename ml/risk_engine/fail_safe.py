"""ISO 26262-inspired fail-safe when sensor feeds drop — Spec Section 19.1."""

from __future__ import annotations

from typing import Any, Mapping


# Map operational severity → illustrative ASIL-inspired class (portfolio demo)
ASIL_MAP = {
    "LOW": "QM",
    "MEDIUM": "A",
    "HIGH": "B",
    "CRITICAL": "C",
}

SAFE_STATE = "DEGRADED_SAFE"


def classify_asil(severity: str) -> str:
    return ASIL_MAP.get(str(severity).upper(), "QM")


def feed_status(
    *,
    driver_state: Mapping[str, Any] | None,
    road_state: Mapping[str, Any] | None,
    telemetry: Mapping[str, Any] | None,
) -> dict[str, Any]:
    driver_ok = bool(driver_state) and (
        driver_state.get("face_detected") is not False
        or "alertness_score" in driver_state
        or "is_drowsy" in driver_state
    )
    road_ok = bool(road_state) and (
        "objects" in road_state or "segmentation" in road_state or "risk" in road_state
    )
    telem_ok = bool(telemetry) and (
        telemetry.get("speed_kmh") is not None or telemetry.get("battery_soc_pct") is not None
    )
    return {
        "camera_driver": driver_ok,
        "camera_road": road_ok,
        "kuksa_telemetry": telem_ok,
        "any_feed_down": not (driver_ok and telem_ok),
    }


def apply_fail_safe(
    base_level: str,
    base_score: float,
    *,
    driver_state: Mapping[str, Any] | None = None,
    road_state: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Elevate risk when critical feeds are missing (documented fail-safe)."""
    feeds = feed_status(
        driver_state=driver_state, road_state=road_state, telemetry=telemetry
    )
    level = str(base_level or "LOW").upper()
    score = float(base_score)
    actions: list[str] = []
    state = "NORMAL"

    if not feeds["kuksa_telemetry"]:
        score = max(score, 70.0)
        if level in {"LOW", "MEDIUM"}:
            level = "HIGH"
        actions.append("telemetry_feed_lost→HIGH_floor")
        state = SAFE_STATE

    if not feeds["camera_driver"]:
        score = max(score, 75.0)
        if level != "CRITICAL":
            level = "HIGH"
        actions.append("driver_camera_lost→HIGH_floor")
        state = SAFE_STATE

    return {
        "level": level,
        "score": round(score, 1),
        "asil": classify_asil(level),
        "safe_state": state,
        "feeds": feeds,
        "actions": actions,
        "phase": "19.1",
    }
