"""Explainability helpers shared by ML pipelines — Modules 3G / 6F / 6G / 8A."""

from ml.xai.gradcam import GradCamResult, generate_gradcam
from ml.xai.integrated_gradients import (
    IntegratedGradientsResult,
    generate_integrated_gradients,
)
from ml.xai.nl_explainer import compose_nl_explanation, shap_waterfall_ascii
from ml.xai.shap_explainer import (
    FeatureContribution,
    ShapExplanation,
    TreeShapExplainer,
    shap_plot_base64_from_top_features,
)

__all__ = [
    "FeatureContribution",
    "GradCamResult",
    "IntegratedGradientsResult",
    "ShapExplanation",
    "TreeShapExplainer",
    "compose_nl_explanation",
    "generate_gradcam",
    "generate_integrated_gradients",
    "shap_plot_base64_from_top_features",
    "shap_waterfall_ascii",
]
