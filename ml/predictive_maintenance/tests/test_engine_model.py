"""Tests for Module 3B fault-classifier inference."""

from __future__ import annotations

import numpy as np
import pytest

from ml.predictive_maintenance.config import (
    NEV_FAULT_CLASS_NAMES,
    NEV_FAULT_FEATURES,
)
from ml.predictive_maintenance.engine_model import EngineFaultClassifier


class StubFaultModel:
    def __init__(self, probabilities: list[float]) -> None:
        self.probabilities = probabilities

    def predict_proba(self, frame):
        assert list(frame.columns) == list(NEV_FAULT_FEATURES)
        return np.asarray([self.probabilities], dtype=float)


def _bundle(probabilities: list[float]) -> dict:
    return {
        "schema_version": 1,
        "model": StubFaultModel(probabilities),
        "features": list(NEV_FAULT_FEATURES),
        "class_names": list(NEV_FAULT_CLASS_NAMES),
    }


def _snapshot() -> dict[str, float]:
    return {name: index / 10 for index, name in enumerate(NEV_FAULT_FEATURES)}


def test_predict_returns_fault_class_and_probabilities():
    classifier = EngineFaultClassifier(bundle=_bundle([0.05, 0.80, 0.10, 0.05]))
    result = classifier.predict(_snapshot())

    assert result.class_id == 1
    assert result.class_name == "motor_fault"
    assert result.confidence == pytest.approx(0.80)
    assert result.fault_detected is True
    assert set(result.probabilities) == set(NEV_FAULT_CLASS_NAMES)


def test_normal_class_is_not_fault():
    classifier = EngineFaultClassifier(bundle=_bundle([0.90, 0.04, 0.03, 0.03]))
    assert classifier.predict(_snapshot()).fault_detected is False


def test_predict_rejects_missing_feature():
    classifier = EngineFaultClassifier(bundle=_bundle([0.90, 0.04, 0.03, 0.03]))
    snapshot = _snapshot()
    snapshot.pop(NEV_FAULT_FEATURES[0])
    with pytest.raises(ValueError, match="Missing 3B telemetry features"):
        classifier.predict(snapshot)


def test_bundle_contract_must_match_config():
    bundle = _bundle([0.90, 0.04, 0.03, 0.03])
    bundle["features"] = bundle["features"][:-1]
    with pytest.raises(ValueError, match="feature contract"):
        EngineFaultClassifier(bundle=bundle)
