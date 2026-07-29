"""Phase 6 Grad-CAM / NL explainer unit tests."""

from __future__ import annotations

import numpy as np

from ml.xai.gradcam import generate_gradcam
from ml.xai.nl_explainer import compose_nl_explanation, shap_waterfall_ascii


def test_generate_gradcam_synthetic(tmp_path) -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[:] = (40, 40, 40)
    result = generate_gradcam(
        frame,
        event_type="drowsiness",
        output_dir=tmp_path,
        filename_stem="drowsy_demo",
    )
    assert result.method == "synthetic_eigen_cam"
    assert "eye" in result.description.lower()
    assert (tmp_path / "drowsy_demo.jpg").is_file()
    assert result.heatmap_url.endswith("drowsy_demo.jpg")


def test_compose_nl_explanation() -> None:
    text = compose_nl_explanation(
        event_type="driver_asleep",
        evidence=["EAR below threshold for 2.7s"],
        visual_description="High activation on eye regions",
        shap_top=[{"feature": "ear", "impact": -0.2, "direction": "increases_risk"}],
        vehicle_state={"speed_kmh": 72},
    )
    assert "Driver Asleep" in text
    assert "EAR" in text
    assert "eye regions" in text
    assert "Action:" in text


def test_shap_waterfall_ascii() -> None:
    text = shap_waterfall_ascii(
        [{"feature": "pad_wear", "contribution": 0.12, "direction": "increases_risk"}]
    )
    assert "pad_wear" in text
    assert "0.1200" in text or "+0.12" in text
