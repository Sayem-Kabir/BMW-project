"""Module 3E — TPI-derived tire-wear proxy regression inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from ml.predictive_maintenance.config import (
    LOGISTICS_TIRE_MODEL_FEATURES,
    LOGISTICS_TIRE_TARGET,
    TIRE_WEAR_CRITICAL_PCT,
    TIRE_WEAR_MODEL_PATH,
    TIRE_WEAR_WARN_PCT,
)


@dataclass(frozen=True)
class TireWearResult:
    wear_pct: float
    severity: str
    maintenance_required: bool
    within_training_range: bool


class TireWearPredictor:
    """Load the 3E artifact and estimate the TPI-derived wear percentage."""

    def __init__(
        self,
        model_path: str | Path = TIRE_WEAR_MODEL_PATH,
        *,
        bundle: Mapping[str, Any] | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self._bundle = dict(bundle) if bundle is not None else None
        self._model: Any | None = None
        self._features = tuple(LOGISTICS_TIRE_MODEL_FEATURES)
        self._feature_ranges: dict[str, tuple[float, float]] = {}
        if self._bundle is not None:
            self._configure_bundle(self._bundle)

    @property
    def ready(self) -> bool:
        return self._bundle is not None or self.model_path.is_file()

    @property
    def model(self) -> Any:
        """Loaded estimator exposed for Module 3G explanations."""
        self.load()
        return self._model

    def _configure_bundle(self, bundle: Mapping[str, Any]) -> None:
        if int(bundle.get("schema_version", 0)) != 1:
            raise ValueError("Unsupported 3E artifact schema_version")
        if "model" not in bundle:
            raise ValueError("3E artifact bundle is missing 'model'")
        if tuple(bundle.get("features", ())) != self._features:
            raise ValueError(
                "3E artifact feature contract does not match "
                "LOGISTICS_TIRE_MODEL_FEATURES"
            )
        if bundle.get("target") != LOGISTICS_TIRE_TARGET:
            raise ValueError(f"3E artifact target must be {LOGISTICS_TIRE_TARGET}")

        raw_ranges = bundle.get("feature_ranges")
        if not isinstance(raw_ranges, Mapping):
            raise ValueError("3E artifact is missing feature_ranges")
        ranges: dict[str, tuple[float, float]] = {}
        for feature in self._features:
            bounds = raw_ranges.get(feature)
            if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                raise ValueError(f"3E artifact has invalid range for {feature}")
            ranges[feature] = (float(bounds[0]), float(bounds[1]))

        self._model = bundle["model"]
        self._feature_ranges = ranges

    def load(self) -> None:
        if self._model is not None:
            return
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"3E model not found: {self.model_path}. "
                "Run notebooks/train_tire_wear_3e.ipynb locally first."
            )

        import joblib

        bundle = joblib.load(self.model_path)
        if not isinstance(bundle, Mapping):
            raise ValueError("3E artifact must be a mapping bundle")
        self._bundle = dict(bundle)
        self._configure_bundle(self._bundle)

    def _frame_from_snapshot(
        self, telemetry: Mapping[str, float | int]
    ) -> tuple[pd.DataFrame, bool]:
        missing = [name for name in self._features if name not in telemetry]
        if missing:
            raise ValueError(f"Missing 3E tire features: {missing}")

        values: list[float] = []
        within_range = True
        for name in self._features:
            value = float(telemetry[name])
            if not np.isfinite(value):
                raise ValueError(f"3E feature {name!r} must be finite")
            low, high = self._feature_ranges[name]
            within_range = within_range and low <= value <= high
            values.append(value)
        return (
            pd.DataFrame([values], columns=self._features, dtype=np.float32),
            within_range,
        )

    def predict(self, telemetry: Mapping[str, float | int]) -> TireWearResult:
        self.load()
        frame, within_range = self._frame_from_snapshot(telemetry)
        raw = np.asarray(self._model.predict(frame), dtype=float).reshape(-1)
        if raw.size != 1 or not np.isfinite(raw[0]):
            raise ValueError("3E model returned an invalid prediction")

        wear_pct = float(np.clip(raw[0], 0.0, 100.0))
        if wear_pct >= TIRE_WEAR_CRITICAL_PCT:
            severity = "critical"
        elif wear_pct >= TIRE_WEAR_WARN_PCT:
            severity = "warning"
        else:
            severity = "normal"
        return TireWearResult(
            wear_pct=wear_pct,
            severity=severity,
            maintenance_required=severity != "normal",
            within_training_range=within_range,
        )


def tire_wear_model_ready(
    model_path: str | Path = TIRE_WEAR_MODEL_PATH,
) -> bool:
    return Path(model_path).is_file()
