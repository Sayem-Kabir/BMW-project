"""Module 3H maintenance REST/service tests with ML inference mocked."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import maintenance_service
from ml.predictive_maintenance.pipeline import (
    ComponentPrediction,
    MaintenanceAlert,
    MaintenancePipelineResult,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _fake_result() -> MaintenancePipelineResult:
    return MaintenancePipelineResult(
        status="partial",
        overall_severity="critical",
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        components={
            "engine": ComponentPrediction(
                component="engine",
                status="ok",
                severity="critical",
                health_score=0.12,
                maintenance_required=True,
                confidence=0.9,
                result={"class_name": "motor_fault", "fault_detected": True},
                explanation={"top_features": []},
            ),
            "brake": ComponentPrediction(
                component="brake",
                status="ok",
                severity="normal",
                health_score=1.0,
                maintenance_required=False,
                confidence=0.8,
                result={"condition": "Good"},
            ),
            "battery": ComponentPrediction(
                component="battery",
                status="unavailable",
                missing_features=("Cycle",),
                error="battery: missing 1 required features",
            ),
            "tire": ComponentPrediction(
                component="tire",
                status="error",
                error="tire: RuntimeError: broken",
            ),
        },
        alerts=(
            MaintenanceAlert(
                component="engine",
                severity="critical",
                message="Engine fault classification: motor_fault",
            ),
        ),
        warnings=("battery: missing 1 required features",),
        processing_ms=12.5,
        stage_times_ms={"engine": 5.0, "brake": 4.0, "battery": 0.1, "tire": 3.4},
    )


@pytest.mark.asyncio
async def test_predict_rejects_empty_telemetry():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/maintenance/{uuid4()}/predict",
            json={"telemetry": {}},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_predict_returns_partial_pipeline_contract():
    with patch(
        "app.services.maintenance_service.run_pipeline",
        return_value=_fake_result(),
    ) as run:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/maintenance/{uuid4()}/predict",
                json={"telemetry": {"engine": {"Voltage (V)": 0.5}}},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "3H"
    assert data["status"] == "partial"
    assert data["overall_severity"] == "critical"
    assert data["components"]["engine"]["health_score"] == 0.12
    assert data["components"]["battery"]["status"] == "unavailable"
    assert data["components"]["battery"]["missing_features"] == ["Cycle"]
    assert data["alerts"][0]["component"] == "engine"
    assert data["persisted"] == 2
    assert data["ml_model_version"] == maintenance_service.ML_MODEL_VERSION
    run.assert_called_once()


@pytest.mark.asyncio
async def test_predict_returns_503_when_pipeline_unavailable():
    with patch(
        "app.services.maintenance_service.run_pipeline",
        side_effect=RuntimeError("bundles missing"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/maintenance/{uuid4()}/predict",
                json={"telemetry": {"engine": {"Voltage (V)": 0.5}}},
            )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_status_reports_component_readiness():
    fake_status = {
        "components": {"engine": {"model_ready": True, "required_features": []}},
        "all_models_ready": False,
        "ml_model_version": maintenance_service.ML_MODEL_VERSION,
    }
    with patch(
        "app.services.maintenance_service.component_status",
        return_value=fake_status,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/maintenance/status")
    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "3H"
    assert data["all_models_ready"] is False


@pytest.mark.asyncio
async def test_trigger_queues_celery_task():
    fake_task = MagicMock()
    fake_task.id = "task-123"
    with patch(
        "app.tasks.maintenance.run_batch_predictions.delay",
        return_value=fake_task,
    ) as delay:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/maintenance/{uuid4()}/trigger",
                json={"telemetry": {"engine": {"Voltage (V)": 0.5}}},
            )
    assert response.status_code == 200
    assert response.json()["task_id"] == "task-123"
    delay.assert_called_once()


@pytest.mark.asyncio
async def test_unknown_component_returns_404():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/maintenance/{uuid4()}/gearbox")
    assert response.status_code == 404


def test_predictions_from_result_maps_only_successful_components():
    vehicle_id = uuid4()
    rows = maintenance_service.predictions_from_result(vehicle_id, _fake_result())

    assert {row.component for row in rows} == {"engine", "brake"}
    engine = next(row for row in rows if row.component == "engine")
    assert engine.vehicle_id == vehicle_id
    assert engine.health_score == 0.12
    assert engine.anomaly_score == pytest.approx(0.88)
    assert engine.shap_explanation["severity"] == "critical"
    assert engine.ml_model_version == maintenance_service.ML_MODEL_VERSION

    brake = next(row for row in rows if row.component == "brake")
    assert brake.anomaly_score is None


def test_run_batch_predictions_requires_vehicle_and_telemetry():
    from app.tasks.maintenance import run_batch_predictions

    assert run_batch_predictions.run()["status"] == "skipped"
    assert run_batch_predictions.run(vehicle_id="abc")["status"] == "skipped"
