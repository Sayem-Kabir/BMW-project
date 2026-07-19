"""Tests for Module 3D battery SoH inference."""

from __future__ import annotations

import numpy as np
import pytest

from ml.predictive_maintenance.battery_model import BatterySoHPredictor
from ml.predictive_maintenance.config import BATTERY_SOH_FEATURES


class StubBatteryModel:
    def __init__(self, prediction: float) -> None:
        self.prediction = prediction

    def predict(self, frame):
        assert list(frame.columns) == list(BATTERY_SOH_FEATURES)
        return np.asarray([self.prediction])


def _bundle(prediction: float) -> dict:
    return {
        "schema_version": 1,
        "model": StubBatteryModel(prediction),
        "features": list(BATTERY_SOH_FEATURES),
        "target": "SOH_pct",
        "feature_ranges": {name: [0.0, 100.0] for name in BATTERY_SOH_FEATURES},
    }


def _snapshot(value: float = 50.0) -> dict[str, float]:
    return {name: value for name in BATTERY_SOH_FEATURES}


@pytest.mark.parametrize(
    ("prediction", "severity", "required"),
    [
        (90.0, "normal", False),
        (75.0, "warning", True),
        (60.0, "critical", True),
    ],
)
def test_predict_maps_soh_to_severity(prediction, severity, required):
    predictor = BatterySoHPredictor(bundle=_bundle(prediction))
    result = predictor.predict(_snapshot())
    assert result.soh_pct == pytest.approx(prediction)
    assert result.severity == severity
    assert result.maintenance_required is required
    assert result.within_training_range is True


def test_reports_out_of_training_range():
    predictor = BatterySoHPredictor(bundle=_bundle(85.0))
    result = predictor.predict(_snapshot(101.0))
    assert result.within_training_range is False


def test_rejects_missing_feature():
    predictor = BatterySoHPredictor(bundle=_bundle(85.0))
    snapshot = _snapshot()
    snapshot.pop(BATTERY_SOH_FEATURES[0])
    with pytest.raises(ValueError, match="Missing 3D battery features"):
        predictor.predict(snapshot)
