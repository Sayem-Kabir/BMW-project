"""Tests for redefined Module 3C brake-condition inference."""

from __future__ import annotations

import numpy as np
import pytest

from ml.predictive_maintenance.brake_model import BrakeConditionClassifier
from ml.predictive_maintenance.config import (
    LOGISTICS_BRAKE_CLASS_NAMES,
    LOGISTICS_BRAKE_FEATURES,
)


class StubBrakeModel:
    def __init__(self, probabilities: list[float]) -> None:
        self.probabilities = probabilities

    def predict_proba(self, frame):
        assert list(frame.columns) == list(LOGISTICS_BRAKE_FEATURES)
        return np.asarray([self.probabilities])


def _bundle(probabilities: list[float]) -> dict:
    return {
        "schema_version": 1,
        "model": StubBrakeModel(probabilities),
        "features": list(LOGISTICS_BRAKE_FEATURES),
        "class_names": list(LOGISTICS_BRAKE_CLASS_NAMES),
        "target": "Brake_Condition",
    }


def _snapshot() -> dict[str, float]:
    return {
        name: float(index + 1)
        for index, name in enumerate(LOGISTICS_BRAKE_FEATURES)
    }


@pytest.mark.parametrize(
    ("probabilities", "condition", "severity", "required"),
    [
        ([0.90, 0.07, 0.03], "Good", "normal", False),
        ([0.10, 0.80, 0.10], "Fair", "warning", True),
        ([0.05, 0.10, 0.85], "Poor", "critical", True),
    ],
)
def test_predict_maps_condition_to_severity(
    probabilities, condition, severity, required
):
    classifier = BrakeConditionClassifier(bundle=_bundle(probabilities))
    result = classifier.predict(_snapshot())
    assert result.condition == condition
    assert result.severity == severity
    assert result.maintenance_required is required
    assert set(result.probabilities) == set(LOGISTICS_BRAKE_CLASS_NAMES)


def test_rejects_wrong_class_contract():
    bundle = _bundle([0.90, 0.07, 0.03])
    bundle["class_names"] = ["Good", "Poor", "Fair"]
    with pytest.raises(ValueError, match="class contract"):
        BrakeConditionClassifier(bundle=bundle)


def test_rejects_missing_telemetry_feature():
    classifier = BrakeConditionClassifier(bundle=_bundle([0.90, 0.07, 0.03]))
    snapshot = _snapshot()
    snapshot.pop(LOGISTICS_BRAKE_FEATURES[0])
    with pytest.raises(ValueError, match="Missing 3C telemetry features"):
        classifier.predict(snapshot)
