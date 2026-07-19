"""Explainability helpers shared by ML pipelines."""

from ml.xai.shap_explainer import (
    FeatureContribution,
    ShapExplanation,
    TreeShapExplainer,
)

__all__ = [
    "FeatureContribution",
    "ShapExplanation",
    "TreeShapExplainer",
]
"""Explainable AI (Grad-CAM / SHAP) — implemented in Phase 6."""
