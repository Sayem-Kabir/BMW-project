"""Module 3H service adapter for the Module 3G maintenance pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping
from uuid import UUID

from app.models.maintenance import MaintenancePrediction

ML_MODEL_VERSION = "phase3-3g-v1"

_pipeline: Any | None = None
_pipeline_lock = RLock()


def get_pipeline() -> Any:
    """Lazily build one shared MaintenancePipeline (model bundles load once)."""
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            from ml.predictive_maintenance import MaintenancePipeline

            _pipeline = MaintenancePipeline()
        return _pipeline


def reset_pipeline() -> None:
    global _pipeline
    with _pipeline_lock:
        _pipeline = None


def run_pipeline(telemetry: Mapping[str, Any]) -> Any:
    """Run 3B–3E through the 3G orchestrator for one telemetry payload."""
    return get_pipeline().predict(telemetry)


def component_status() -> dict[str, Any]:
    """Cheap artifact readiness report without loading model bundles."""
    from ml.predictive_maintenance import (
        COMPONENT_FEATURES,
        battery_soh_model_ready,
        brake_condition_model_ready,
        engine_fault_model_ready,
        tire_wear_model_ready,
    )

    ready = {
        "engine": engine_fault_model_ready(),
        "brake": brake_condition_model_ready(),
        "battery": battery_soh_model_ready(),
        "tire": tire_wear_model_ready(),
    }
    return {
        "components": {
            name: {
                "model_ready": ready[name],
                "required_features": list(COMPONENT_FEATURES[name]),
            }
            for name in ready
        },
        "all_models_ready": all(ready.values()),
        "ml_model_version": ML_MODEL_VERSION,
    }


def _anomaly_score(component: str, prediction: Any) -> float | None:
    if prediction.health_score is None:
        return None
    if component == "engine":
        return round(1.0 - float(prediction.health_score), 6)
    return None


def predictions_from_result(
    vehicle_id: UUID | str,
    result: Any,
) -> list[MaintenancePrediction]:
    """Map successful 3G component outputs to maintenance_predictions rows."""
    rows: list[MaintenancePrediction] = []
    for component, prediction in result.components.items():
        if prediction.status != "ok" or prediction.health_score is None:
            continue
        rows.append(
            MaintenancePrediction(
                vehicle_id=UUID(str(vehicle_id)),
                component=component,
                health_score=float(prediction.health_score),
                anomaly_score=_anomaly_score(component, prediction),
                confidence=prediction.confidence,
                shap_explanation={
                    "severity": prediction.severity,
                    "maintenance_required": prediction.maintenance_required,
                    "result": prediction.result,
                    "explanation": prediction.explanation,
                    "explanation_error": prediction.explanation_error,
                },
                ml_model_version=ML_MODEL_VERSION,
            )
        )
    return rows


async def persist_result(
    session: Any,
    vehicle_id: UUID | str,
    result: Any,
) -> list[MaintenancePrediction]:
    rows = predictions_from_result(vehicle_id, result)
    for row in rows:
        session.add(row)
    if rows:
        await session.commit()
        from app.services.event_service import publish_maintenance_alert

        for row in rows:
            shap = row.shap_explanation or {}
            severity = str(shap.get("severity") or "normal")
            if severity.lower() in {"critical", "high"} or float(row.health_score) <= 0.35:
                await publish_maintenance_alert(
                    vehicle_id=vehicle_id,
                    component=row.component,
                    health_score=float(row.health_score),
                    severity=severity,
                    confidence=row.confidence,
                )
    return rows


async def run_and_persist(
    vehicle_id: UUID | str,
    telemetry: Mapping[str, Any],
) -> dict[str, Any]:
    """Celery/back-office entry point: one pipeline run persisted to Postgres."""
    from app.core.database import async_session_maker

    result = run_pipeline(telemetry)
    async with async_session_maker() as session:
        rows = await persist_result(session, vehicle_id, result)
    payload = result.to_dict()
    payload.update(
        {
            "vehicle_id": str(vehicle_id),
            "persisted": len(rows),
            "ml_model_version": ML_MODEL_VERSION,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return payload
