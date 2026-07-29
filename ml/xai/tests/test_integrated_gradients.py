"""Unit tests for Module 8A Captum IG (synthetic fallback path)."""

from __future__ import annotations

import numpy as np

from ml.xai.integrated_gradients import generate_integrated_gradients


def test_generate_ig_synthetic_fallback(tmp_path):
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[40:60, 50:70] = 200
    result = generate_integrated_gradients(
        frame,
        event_type="drowsiness",
        model=None,
        output_dir=tmp_path,
        filename_stem="test_ig",
    )
    assert result.method in {"synthetic_ig", "captum_ig"}
    assert result.phase == "8A"
    assert (tmp_path / "test_ig.jpg").is_file()
    assert result.activation_mass >= 0.0
    assert "/api/v1/xai/heatmap/" in result.heatmap_url
