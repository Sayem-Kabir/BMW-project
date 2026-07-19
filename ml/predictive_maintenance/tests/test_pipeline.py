"""Tests for Module 3G unified maintenance orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from ml.predictive_maintenance.battery_model import BatterySoHResult
from ml.predictive_maintenance.brake_model import BrakeConditionResult
from ml.predictive_maintenance.config import (
    BATTERY_SOH_FEATURES,
    LOGISTICS_BRAKE_FEATURES,
    LOGISTICS_TIRE_MODEL_FEATURES,
    NEV_FAULT_FEATURES,
)
from ml.predictive_maintenance.engine_model import EngineFaultResult
from ml.predictive_maintenance.pipeline import MaintenancePipeline
from ml.predictive_maintenance.tire_model import TireWearResult
from ml.xai import TreeShapExplainer


class StubPredictor:
    ready = True

    def __init__(self, result=None, *, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.model = object()

    def predict(self, _telemetry):
        if self.error:
            raise self.error
        return self.result


def _inputs() -> dict[str, dict[str, float]]:
    return {
        "engine": {name: 0.5 for name in NEV_FAULT_FEATURES},
        "brake": {name: 50.0 for name in LOGISTICS_BRAKE_FEATURES},
        "battery": {name: 50.0 for name in BATTERY_SOH_FEATURES},
        "tire": {name: 50.0 for name in LOGISTICS_TIRE_MODEL_FEATURES},
    }


def _predictors() -> dict[str, StubPredictor]:
    return {
        "engine": StubPredictor(
            EngineFaultResult(
                class_id=1,
                class_name="motor_fault",
                confidence=0.85,
                probabilities={
                    "normal": 0.05,
                    "motor_fault": 0.85,
                    "inverter_fault": 0.05,
                    "battery_fault": 0.05,
                },
                fault_detected=True,
            )
        ),
        "brake": StubPredictor(
            BrakeConditionResult(
                class_id=1,
                condition="Fair",
                confidence=0.75,
                probabilities={"Good": 0.1, "Fair": 0.75, "Poor": 0.15},
                severity="warning",
                maintenance_required=True,
            )
        ),
        "battery": StubPredictor(
            BatterySoHResult(
                soh_pct=91.0,
                severity="normal",
                maintenance_required=False,
                within_training_range=True,
            )
        ),
        "tire": StubPredictor(
            TireWearResult(
                wear_pct=93.0,
                severity="critical",
                maintenance_required=True,
                within_training_range=True,
            )
        ),
    }


def test_complete_pipeline_preserves_component_results_and_alerts():
    pipeline = MaintenancePipeline(
        predictors=_predictors(),
        enable_explanations=False,
    )
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)
    result = pipeline.predict(_inputs(), timestamp=timestamp)

    assert result.status == "complete"
    assert result.overall_severity == "critical"
    assert result.succeeded == 4
    assert result.timestamp == timestamp
    assert result.components["engine"].severity == "critical"
    assert result.components["engine"].health_score == pytest.approx(0.05)
    assert result.components["battery"].health_score == pytest.approx(0.91)
    assert result.components["tire"].health_score == pytest.approx(0.07)
    assert result.components["battery"].maintenance_required is False
    assert result.processing_ms >= 0.0
    assert set(result.stage_times_ms) == {"engine", "brake", "battery", "tire"}
    assert {alert.component for alert in result.alerts} == {
        "engine",
        "brake",
        "tire",
    }
    assert result.to_dict()["overall_severity"] == "critical"


def test_missing_component_features_produce_partial_result():
    pipeline = MaintenancePipeline(
        predictors=_predictors(),
        enable_explanations=False,
    )
    result = pipeline.predict({"battery": _inputs()["battery"]})

    assert result.status == "partial"
    assert result.overall_severity == "normal"
    assert result.succeeded == 1
    assert result.components["battery"].status == "ok"
    assert result.components["engine"].status == "unavailable"
    assert result.components["engine"].missing_features


def test_one_predictor_failure_does_not_discard_other_results():
    predictors = _predictors()
    predictors["brake"] = StubPredictor(error=RuntimeError("broken model"))
    pipeline = MaintenancePipeline(
        predictors=predictors,
        enable_explanations=False,
    )
    result = pipeline.predict(_inputs())

    assert result.status == "partial"
    assert result.succeeded == 3
    assert result.components["brake"].status == "error"
    assert "broken model" in result.components["brake"].error
    assert result.components["tire"].status == "ok"


class BrokenExplainer:
    def explain(self, *_args, **_kwargs):
        raise RuntimeError("explanation failed")


def test_explanation_failure_does_not_discard_prediction():
    pipeline = MaintenancePipeline(
        predictors=_predictors(),
        explainer=BrokenExplainer(),
    )
    result = pipeline.predict(_inputs())

    assert result.status == "complete"
    assert result.succeeded == 4
    assert result.components["engine"].result is not None
    assert "explanation failed" in result.components["engine"].explanation_error
    assert any("explanation unavailable" in warning for warning in result.warnings)


class FakeBooster:
    def predict(self, _matrix, *, pred_contribs, strict_shape):
        assert pred_contribs is True
        assert strict_shape is True
        return np.asarray([[[0.1, -0.5, 0.2]]])


class FakeXGBModel:
    def get_booster(self):
        return FakeBooster()


def test_tree_explainer_ranks_absolute_contributions_and_risk_direction():
    explanation = TreeShapExplainer(top_k=2).explain(
        FakeXGBModel(),
        {"a": 1.0, "b": 2.0},
        ("a", "b"),
        risk_sign=1,
    )
    assert explanation.base_value == 0.2
    assert explanation.top_features[0].feature == "b"
    assert explanation.top_features[0].direction == "decreases_risk"
    assert explanation.top_features[1].direction == "increases_risk"
