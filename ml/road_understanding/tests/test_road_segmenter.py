"""Tests for Module 2B DeepLabV3+ road segmentation."""

from __future__ import annotations

import numpy as np
import pytest
import torch

from ml.road_understanding.config import (
    SEG_ROAD_CLASS_NAMES,
    SEG_ROAD_MODEL_PATH,
    seg_road_model_ready,
)
from ml.road_understanding.road_segmenter import (
    RoadSegmentation,
    RoadSegmenter,
)


class _RoadOnlyModel(torch.nn.Module):
    def forward(self, image: torch.Tensor) -> torch.Tensor:
        logits = torch.zeros(
            (image.shape[0], len(SEG_ROAD_CLASS_NAMES), image.shape[2], image.shape[3]),
            device=image.device,
        )
        logits[:, 0] = 8.0
        return logits


def test_result_ratios_masks_and_overlay():
    mask = np.array([[0, 0], [1, 2]], dtype=np.uint8)
    result = RoadSegmentation(mask=mask, model_loaded=True)

    assert result.class_ratios() == {
        "road": 0.5,
        "shoulder": 0.25,
        "background": 0.25,
    }
    assert result.binary_mask(0).tolist() == [[255, 255], [0, 0]]

    frame = np.full((2, 2, 3), 100, dtype=np.uint8)
    overlay = result.overlay(frame)
    assert overlay.shape == frame.shape
    assert np.array_equal(overlay[1, 1], frame[1, 1])
    assert not np.array_equal(overlay[0, 0], frame[0, 0])


def test_segment_restores_original_resolution():
    segmenter = RoadSegmenter(auto_load=False, device="cpu", input_size=32)
    segmenter._model = _RoadOnlyModel().eval()

    frame = np.zeros((20, 30, 3), dtype=np.uint8)
    result = segmenter.segment(frame)

    assert result.is_valid
    assert result.mask.shape == (20, 30)
    assert result.confidence.shape == (20, 30)
    assert np.all(result.mask == 0)
    assert result.class_ratios()["road"] == 1.0


def test_empty_frame_returns_clear_result():
    segmenter = RoadSegmenter(auto_load=False, device="cpu")
    result = segmenter.segment(np.array([], dtype=np.uint8))

    assert not result.is_valid
    assert result.message == "Empty frame"


def test_invalid_class_id_is_rejected():
    result = RoadSegmentation(mask=np.zeros((2, 2), dtype=np.uint8))
    with pytest.raises(ValueError, match="class_id"):
        result.binary_mask(3)


def test_local_checkpoint_matches_notebook_architecture():
    if not seg_road_model_ready():
        pytest.skip(f"Local ignored checkpoint is absent: {SEG_ROAD_MODEL_PATH}")

    segmenter = RoadSegmenter(device="cpu")
    assert segmenter.is_ready, segmenter._load_error
    assert segmenter.checkpoint_epoch == 22
    assert segmenter.checkpoint_val_acc == pytest.approx(0.9324303932)
