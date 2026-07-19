"""Module 3C — logistics brake-condition classification inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from ml.predictive_maintenance.config import (
    BRAKE_CONDITION_MODEL_PATH,
    LOGISTICS_BRAKE_CLASS_NAMES,
    LOGISTICS_BRAKE_FEATURES,
)


@dataclass(frozen=True)
class BrakeConditionResult:
    class_id: int
    condition: str
    confidence: float
    probabilities: dict[str, float]
    severity: str
    maintenance_required: bool


class BrakeConditionClassifier:
    """Load the 3C bundle and classify brakes as Good, Fair, or Poor."""

    def __init__(
        self,
        model_path: str | Path = BRAKE_CONDITION_MODEL_PATH,
        *,
        bundle: Mapping[str, Any] | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self._bundle = dict(bundle) if bundle is not None else None
        self._model: Any | None = None
        self._features: tuple[str, ...] = tuple(LOGISTICS_BRAKE_FEATURES)
        self._class_names: tuple[str, ...] = tuple(LOGISTICS_BRAKE_CLASS_NAMES)
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
            raise ValueError("Unsupported 3C artifact schema_version")
        if "model" not in bundle:
            raise ValueError("3C artifact bundle is missing 'model'")
        if tuple(bundle.get("features", ())) != tuple(LOGISTICS_BRAKE_FEATURES):
            raise ValueError(
                "3C artifact feature contract does not match LOGISTICS_BRAKE_FEATURES"
            )
        if tuple(bundle.get("class_names", ())) != tuple(
            LOGISTICS_BRAKE_CLASS_NAMES
        ):
            raise ValueError(
                "3C artifact class contract does not match "
                "LOGISTICS_BRAKE_CLASS_NAMES"
            )
        if bundle.get("target") != "Brake_Condition":
            raise ValueError("3C artifact target must be Brake_Condition")

        self._model = bundle["model"]
        self._features = tuple(bundle["features"])
        self._class_names = tuple(bundle["class_names"])

    def load(self) -> None:
        if self._model is not None:
            return
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"3C model not found: {self.model_path}. "
                "Run notebooks/train_brake_wear_3c.ipynb locally first."
            )

        import joblib

        bundle = joblib.load(self.model_path)
        if not isinstance(bundle, Mapping):
            raise ValueError("3C artifact must be a mapping bundle")
        self._bundle = dict(bundle)
        self._configure_bundle(self._bundle)

    def _frame_from_snapshot(
        self, telemetry: Mapping[str, float | int]
    ) -> pd.DataFrame:
        missing = [name for name in self._features if name not in telemetry]
        if missing:
            raise ValueError(f"Missing 3C telemetry features: {missing}")

        values: list[float] = []
        for name in self._features:
            value = float(telemetry[name])
            if not np.isfinite(value):
                raise ValueError(f"3C feature {name!r} must be finite")
            values.append(value)
        return pd.DataFrame([values], columns=self._features, dtype=np.float32)

    def predict(
        self, telemetry: Mapping[str, float | int]
    ) -> BrakeConditionResult:
        self.load()
        frame = self._frame_from_snapshot(telemetry)
        raw = np.asarray(self._model.predict_proba(frame), dtype=float)
        if raw.shape != (1, len(self._class_names)):
            raise ValueError(
                f"3C model returned invalid probabilities shape {raw.shape}"
            )

        vector = raw[0]
        class_id = int(np.argmax(vector))
        condition = self._class_names[class_id]
        probabilities = {
            name: float(vector[index])
            for index, name in enumerate(self._class_names)
        }
        return BrakeConditionResult(
            class_id=class_id,
            condition=condition,
            confidence=float(vector[class_id]),
            probabilities=probabilities,
            severity=("normal", "warning", "critical")[class_id],
            maintenance_required=class_id != 0,
        )


def brake_condition_model_ready(
    model_path: str | Path = BRAKE_CONDITION_MODEL_PATH,
) -> bool:
    return Path(model_path).is_file()
