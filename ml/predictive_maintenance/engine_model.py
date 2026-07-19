"""Module 3B — NEV multiclass fault-classifier inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from ml.predictive_maintenance.config import (
    ENGINE_FAULT_MODEL_PATH,
    NEV_FAULT_CLASS_NAMES,
    NEV_FAULT_FEATURES,
)


@dataclass(frozen=True)
class EngineFaultResult:
    """One 3B fault-classification result."""

    class_id: int
    class_name: str
    confidence: float
    probabilities: dict[str, float]
    fault_detected: bool


class EngineFaultClassifier:
    """Load the local 3B joblib artifact and classify one telemetry snapshot."""

    def __init__(
        self,
        model_path: str | Path = ENGINE_FAULT_MODEL_PATH,
        *,
        bundle: Mapping[str, Any] | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self._bundle = dict(bundle) if bundle is not None else None
        self._model: Any | None = None
        self._features: tuple[str, ...] = tuple(NEV_FAULT_FEATURES)
        self._class_names: tuple[str, ...] = tuple(NEV_FAULT_CLASS_NAMES)

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
        if "model" not in bundle:
            raise ValueError("3B artifact bundle is missing 'model'")
        if int(bundle.get("schema_version", 0)) != 1:
            raise ValueError("Unsupported 3B artifact schema_version")

        features = tuple(bundle.get("features", ()))
        class_names = tuple(bundle.get("class_names", ()))
        if features != tuple(NEV_FAULT_FEATURES):
            raise ValueError(
                "3B artifact feature contract does not match NEV_FAULT_FEATURES"
            )
        if class_names != tuple(NEV_FAULT_CLASS_NAMES):
            raise ValueError(
                "3B artifact class contract does not match NEV_FAULT_CLASS_NAMES"
            )

        self._model = bundle["model"]
        self._features = features
        self._class_names = class_names

    def load(self) -> None:
        """Load and validate the joblib bundle once."""
        if self._model is not None:
            return
        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"3B model not found: {self.model_path}. "
                "Run notebooks/train_engine_fault_3b.ipynb locally first."
            )

        import joblib

        bundle = joblib.load(self.model_path)
        if not isinstance(bundle, Mapping):
            raise ValueError("3B artifact must be a mapping bundle")
        self._bundle = dict(bundle)
        self._configure_bundle(self._bundle)

    def _frame_from_snapshot(
        self, telemetry: Mapping[str, float | int]
    ) -> pd.DataFrame:
        missing = [name for name in self._features if name not in telemetry]
        if missing:
            raise ValueError(f"Missing 3B telemetry features: {missing}")

        values = []
        for name in self._features:
            value = float(telemetry[name])
            if not np.isfinite(value):
                raise ValueError(f"3B feature {name!r} must be finite")
            values.append(value)
        return pd.DataFrame([values], columns=self._features, dtype=np.float32)

    def predict(self, telemetry: Mapping[str, float | int]) -> EngineFaultResult:
        """Classify a normalized NEV telemetry snapshot."""
        self.load()
        frame = self._frame_from_snapshot(telemetry)
        probabilities_raw = np.asarray(self._model.predict_proba(frame), dtype=float)
        if probabilities_raw.shape != (1, len(self._class_names)):
            raise ValueError(
                "3B model returned invalid probabilities shape "
                f"{probabilities_raw.shape}"
            )

        probabilities_vector = probabilities_raw[0]
        class_id = int(np.argmax(probabilities_vector))
        confidence = float(probabilities_vector[class_id])
        probabilities = {
            name: float(probabilities_vector[index])
            for index, name in enumerate(self._class_names)
        }
        return EngineFaultResult(
            class_id=class_id,
            class_name=self._class_names[class_id],
            confidence=confidence,
            probabilities=probabilities,
            fault_detected=class_id != 0,
        )


def engine_fault_model_ready(
    model_path: str | Path = ENGINE_FAULT_MODEL_PATH,
) -> bool:
    return Path(model_path).is_file()
