"""Native XGBoost SHAP contribution extraction without plotting overhead."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class FeatureContribution:
    feature: str
    value: float
    contribution: float
    direction: str


@dataclass(frozen=True)
class ShapExplanation:
    output_index: int
    base_value: float
    top_features: tuple[FeatureContribution, ...]
    method: str = "xgboost_pred_contribs"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["top_features"] = [asdict(item) for item in self.top_features]
        return result


def shap_plot_base64_from_top_features(
    top_features: Sequence[Mapping[str, Any]] | Sequence[FeatureContribution],
) -> str | None:
    """Optional matplotlib bar plot as base64 PNG for dashboard XAI panels."""
    try:
        import base64
        import io

        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:  # noqa: BLE001
        return None

    names: list[str] = []
    values: list[float] = []
    for item in top_features:
        if isinstance(item, FeatureContribution):
            names.append(item.feature)
            values.append(float(item.contribution))
        else:
            names.append(str(item.get("feature") or item.get("name") or "?"))
            values.append(float(item.get("contribution", item.get("impact", 0.0))))
    if not names:
        return None

    fig, ax = plt.subplots(figsize=(8, 3.2))
    colors = ["#ef4444" if v > 0 else "#22c55e" for v in values]
    ax.barh(names[::-1], values[::-1], color=colors[::-1])
    ax.set_xlabel("SHAP contribution")
    ax.set_title("Top feature contributions")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


class TreeShapExplainer:
    """Return top local XGBoost contributions in raw-margin units."""

    def __init__(self, *, top_k: int = 3) -> None:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.top_k = top_k

    def explain(
        self,
        model: Any,
        telemetry: Mapping[str, float | int],
        features: Sequence[str],
        *,
        output_index: int = 0,
        risk_sign: int = 1,
    ) -> ShapExplanation:
        if risk_sign not in (-1, 1):
            raise ValueError("risk_sign must be -1 or 1")
        missing = [feature for feature in features if feature not in telemetry]
        if missing:
            raise ValueError(f"Missing explanation features: {missing}")

        values = [float(telemetry[feature]) for feature in features]
        if not np.isfinite(values).all():
            raise ValueError("Explanation features must be finite")
        frame = pd.DataFrame([values], columns=features, dtype=np.float32)

        try:
            import xgboost as xgb
        except ImportError as exc:
            raise RuntimeError("XGBoost is required for SHAP contributions") from exc

        booster = model.get_booster() if hasattr(model, "get_booster") else model
        matrix = xgb.DMatrix(frame, feature_names=list(features))
        raw = np.asarray(
            booster.predict(matrix, pred_contribs=True, strict_shape=True),
            dtype=float,
        )
        if raw.ndim != 3 or raw.shape[0] != 1:
            raise ValueError(f"Unexpected SHAP contribution shape {raw.shape}")
        if not 0 <= output_index < raw.shape[1]:
            raise ValueError(
                f"SHAP output_index {output_index} outside 0..{raw.shape[1] - 1}"
            )
        vector = raw[0, output_index]
        if vector.size != len(features) + 1:
            raise ValueError("SHAP contribution count does not match feature contract")

        ranked = sorted(
            zip(features, values, vector[:-1], strict=True),
            key=lambda item: abs(float(item[2])),
            reverse=True,
        )
        top = tuple(
            FeatureContribution(
                feature=feature,
                value=float(value),
                contribution=float(contribution),
                direction=(
                    "increases_risk"
                    if float(contribution) * risk_sign > 0
                    else "decreases_risk"
                ),
            )
            for feature, value, contribution in ranked[: self.top_k]
        )
        return ShapExplanation(
            output_index=output_index,
            base_value=float(vector[-1]),
            top_features=top,
        )
