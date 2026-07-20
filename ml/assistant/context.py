"""Module 5F — vehicle / telemetry / maintenance context builders for prompts."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

PHASE = "5F"


def format_telemetry_context(telemetry: Mapping[str, Any] | None) -> str:
    if not telemetry:
        return "Live telemetry unavailable."
    return (
        "Current vehicle sensor readings:\n"
        f"- Speed: {telemetry.get('speed_kmh', 'N/A')} km/h\n"
        f"- Tire Pressures: FL={telemetry.get('tire_fl', 'N/A')} PSI, "
        f"FR={telemetry.get('tire_fr', 'N/A')} PSI, "
        f"RL={telemetry.get('tire_rl', 'N/A')} PSI, "
        f"RR={telemetry.get('tire_rr', 'N/A')} PSI\n"
        f"- Battery SoC: {telemetry.get('battery_soc', 'N/A')}%\n"
        f"- Oil Temp: {telemetry.get('oil_temp', 'N/A')}°C"
    )


def format_maintenance_context(
    predictions: Sequence[Mapping[str, Any]] | None,
) -> str:
    """Format latest predictive-maintenance rows for the LLM prompt."""
    if not predictions:
        return "Personalized maintenance history unavailable."

    lines = ["Latest predictive maintenance status for this vehicle:"]
    for row in predictions:
        component = str(row.get("component") or "unknown")
        health = row.get("health_score")
        severity = row.get("severity") or (
            (row.get("shap_explanation") or {}).get("severity")
            if isinstance(row.get("shap_explanation"), Mapping)
            else None
        )
        confidence = row.get("confidence")
        remaining_km = row.get("predicted_remaining_km")
        replacement = row.get("predicted_replacement_date")
        created = row.get("created_at")

        parts = [f"- {component}: health={health}"]
        if severity is not None:
            parts.append(f"severity={severity}")
        if confidence is not None:
            parts.append(f"confidence={confidence}")
        if remaining_km is not None:
            parts.append(f"remaining_km={remaining_km}")
        if replacement is not None:
            parts.append(f"replacement={replacement}")
        if created is not None:
            parts.append(f"as_of={created}")
        lines.append(" · ".join(parts))

    return "\n".join(lines)


def demo_maintenance_snapshot(vehicle_id: str) -> list[dict[str, Any]]:
    """Demo maintenance rows used when Postgres has no predictions yet."""
    return [
        {
            "vehicle_id": vehicle_id,
            "component": "tire",
            "health_score": 0.62,
            "severity": "medium",
            "confidence": 0.81,
            "predicted_remaining_km": 12000,
            "predicted_replacement_date": None,
            "created_at": "demo",
        },
        {
            "vehicle_id": vehicle_id,
            "component": "brake",
            "health_score": 0.78,
            "severity": "low",
            "confidence": 0.74,
            "predicted_remaining_km": 22000,
            "predicted_replacement_date": None,
            "created_at": "demo",
        },
        {
            "vehicle_id": vehicle_id,
            "component": "battery",
            "health_score": 0.88,
            "severity": "low",
            "confidence": 0.79,
            "predicted_remaining_km": None,
            "predicted_replacement_date": None,
            "created_at": "demo",
        },
        {
            "vehicle_id": vehicle_id,
            "component": "engine",
            "health_score": 0.91,
            "severity": "low",
            "confidence": 0.83,
            "predicted_remaining_km": None,
            "predicted_replacement_date": None,
            "created_at": "demo",
        },
    ]


def should_inject_maintenance(intent: str, route: str) -> bool:
    return intent in {"maintenance_question", "vehicle_warning", "obd_code"} or route in {
        "rag_only",
        "rag_with_telemetry",
    }


def should_inject_telemetry(intent: str, route: str) -> bool:
    return route == "rag_with_telemetry" or intent in {"vehicle_warning", "obd_code"}
