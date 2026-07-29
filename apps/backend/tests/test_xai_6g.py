"""Module 6G — unified XAI panel tests (SHAP + NL + rule trace)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import xai_service
from ml.xai import compose_nl_explanation, shap_plot_base64_from_top_features, shap_waterfall_ascii


def test_compose_nl_includes_shap_and_visual():
    text = compose_nl_explanation(
        event_type="maintenance_engine",
        evidence=["engine health=42% severity=warning"],
        visual_description=None,
        shap_top=[
            {"feature": "Temperature (°C)", "contribution": 0.22, "direction": "increases_risk"},
            {"feature": "Vibration (g)", "contribution": -0.05, "direction": "decreases_risk"},
        ],
    )
    assert "Temperature" in text
    assert "Action:" in text
    assert "maintenance engine" in text.lower() or "Maintenance Engine" in text


def test_shap_plot_and_waterfall_from_top_features():
    top = [
        {"feature": "Usage_Hours", "contribution": 0.31, "direction": "increases_risk"},
        {"feature": "Oil_Quality", "contribution": -0.12, "direction": "decreases_risk"},
    ]
    ascii_plot = shap_waterfall_ascii(top)
    assert "Usage_Hours" in ascii_plot
    plot = shap_plot_base64_from_top_features(top)
    assert plot is None or len(plot) > 100


@pytest.mark.asyncio
async def test_xai_explain_maintenance_shap(monkeypatch):
    vehicle_id = uuid4()
    top = [
        {"feature": "Temperature (°C)", "contribution": 0.4, "direction": "increases_risk"},
        {"feature": "Vibration (g)", "contribution": 0.15, "direction": "increases_risk"},
    ]
    row = SimpleNamespace(
        component="engine",
        health_score=0.41,
        shap_explanation={
            "severity": "warning",
            "explanation": {"top_features": top},
        },
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return row

    class FakeSession:
        async def execute(self, _stmt):
            return FakeResult()

    payload = await xai_service.explain(
        FakeSession(),
        vehicle_id=vehicle_id,
        component="engine",
    )
    assert payload["phase"] == "6G"
    assert "xgboost_pred_contribs" in payload["method"]
    assert payload["shap_values"] is not None
    assert payload["shap_values"]["top_features"][0]["feature"] == "Temperature (°C)"
    assert "Temperature" in payload["explanation"]
    assert payload["shap_values"]["waterfall_ascii"]
