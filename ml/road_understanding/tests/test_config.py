"""Tests for Module 2A road understanding foundations."""

from __future__ import annotations

from ml.road_understanding.config import (
    DEPTH_MAX_DISTANCE_M,
    DEPTH_ROI_INSET_RATIO,
    MIDAS_MODEL_TYPE,
    PEDESTRIAN_TEMPORAL_INPUT_SIZE,
    PEDESTRIAN_TEMPORAL_MODEL_PATH,
    PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH,
    ROAD_CLASS_NAMES,
    SEG_ROAD_CLASS_NAMES,
    SEG_ROAD_INPUT_SIZE,
    SEG_ROAD_MODEL_PATH,
    TRAFFIC_LIGHT_STATES,
    YOLO_ROAD_FALLBACK_MODEL,
    YOLO_ROAD_MODEL_PATH,
    ensure_models_dir,
    pedestrian_temporal_model_ready,
    resolve_yolo_road_weights,
    seg_road_model_ready,
    yolo_road_model_ready,
)


def test_segmentation_config_matches_training_notebook():
    assert SEG_ROAD_MODEL_PATH.name == "seg_road.pt"
    assert SEG_ROAD_INPUT_SIZE == 512
    assert SEG_ROAD_CLASS_NAMES == ("road", "shoulder", "background")


def test_segmentation_weights_status_is_accurate():
    expected = SEG_ROAD_MODEL_PATH.is_file() and SEG_ROAD_MODEL_PATH.stat().st_size > 0
    assert seg_road_model_ready() is expected


def test_depth_config_uses_pretrained_midas():
    assert MIDAS_MODEL_TYPE == "MiDaS_small"
    assert 0.0 <= DEPTH_ROI_INSET_RATIO < 0.5
    assert DEPTH_MAX_DISTANCE_M > 0


def test_traffic_light_states_are_complete():
    assert TRAFFIC_LIGHT_STATES == ("RED", "AMBER", "GREEN", "UNKNOWN")


def test_temporal_pedestrian_config_matches_caltech_notebook():
    assert PEDESTRIAN_TEMPORAL_MODEL_PATH.name == "best_pedestrian_yololstm.pt"
    assert PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH == 5
    assert PEDESTRIAN_TEMPORAL_INPUT_SIZE == 224
    expected = (
        PEDESTRIAN_TEMPORAL_MODEL_PATH.is_file()
        and PEDESTRIAN_TEMPORAL_MODEL_PATH.stat().st_size > 0
    )
    assert pedestrian_temporal_model_ready() is expected


def test_road_class_names_nonempty():
    assert len(ROAD_CLASS_NAMES) >= 8
    assert "car" in ROAD_CLASS_NAMES
    assert "pedestrian" in ROAD_CLASS_NAMES
    assert "traffic light" in ROAD_CLASS_NAMES


def test_ensure_models_dir():
    path = ensure_models_dir()
    assert path.is_dir()


def test_resolve_weights_fallback_when_missing():
    # Fine-tuned file is gitignored / usually absent in fresh checkouts
    if not yolo_road_model_ready():
        assert resolve_yolo_road_weights() == YOLO_ROAD_FALLBACK_MODEL
        assert not YOLO_ROAD_MODEL_PATH.is_file() or YOLO_ROAD_MODEL_PATH.stat().st_size == 0
    else:
        assert resolve_yolo_road_weights() == str(YOLO_ROAD_MODEL_PATH)
