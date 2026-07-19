"""Tests for Module 3E tire-wear proxy inference."""

from __future__ import annotations

import numpy as np
import pytest

from ml.predictive_maintenance.config import LOGISTICS_TIRE_MODEL_FEATURES
from ml.predictive_maintenance.tire_model import TireWearPredictor


class StubTireModel:
    def __init__(self, prediction: float) -> None:
        self.prediction = prediction

    def predict(self, frame):
        assert list(frame.columns) == list(LOGISTICS_TIRE_MODEL_FEATURES)
        return np.asarray([self.prediction])


def _bundle(prediction: float) -> dict:
    return {
        "schema_version": 1,
        "model": StubTireModel(prediction),
        "features": list(LOGISTICS_TIRE_MODEL_FEATURES),
        "target": "Tire_Wear_pct",
        "feature_ranges": {
            name: [0.0, 100.0] for name in LOGISTICS_TIRE_MODEL_FEATURES
        },
    }


def _snapshot(value: float = 50.0) -> dict[str, float]:
    return {name: value for name in LOGISTICS_TIRE_MODEL_FEATURES}


@pytest.mark.parametrize(
    ("prediction", "severity", "required"),
    [
        (40.0, "normal", False),
        (70.0, "warning", True),
        (90.0, "critical", True),
    ],
)
def test_predict_maps_wear_to_severity(prediction, severity, required):
    predictor = TireWearPredictor(bundle=_bundle(prediction))
    result = predictor.predict(_snapshot())
    assert result.wear_pct == pytest.approx(prediction)
    assert result.severity == severity
    assert result.maintenance_required is required
    assert result.within_training_range is True


def test_clips_prediction_and_reports_out_of_range():
    predictor = TireWearPredictor(bundle=_bundle(105.0))
    result = predictor.predict(_snapshot(101.0))
    assert result.wear_pct == 100.0
    assert result.severity == "critical"
    assert result.within_training_range is False


def test_rejects_missing_feature():
    predictor = TireWearPredictor(bundle=_bundle(50.0))
    snapshot = _snapshot()
    snapshot.pop(LOGISTICS_TIRE_MODEL_FEATURES[0])
    with pytest.raises(ValueError, match="Missing 3E tire features"):
        predictor.predict(snapshot)


def test_rejects_feature_contract_mismatch():
    bundle = _bundle(50.0)
    bundle["features"] = list(reversed(bundle["features"]))
    with pytest.raises(ValueError, match="feature contract"):
        TireWearPredictor(bundle=bundle)
