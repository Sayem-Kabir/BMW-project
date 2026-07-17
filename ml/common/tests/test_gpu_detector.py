"""Tests for shared GPU detection / device resolution."""

from __future__ import annotations

from ml.common.gpu_detector import GPUDetector, get_inference_device


def test_normalize_preferred_cpu():
    assert get_inference_device("cpu") == "cpu"
    assert get_inference_device("CPU") == "cpu"


def test_normalize_preferred_cuda_index():
    assert get_inference_device(0) == "cuda:0"
    assert get_inference_device("1") == "cuda:1"
    assert get_inference_device("cuda:0") == "cuda:0"


def test_ml_device_env_override(monkeypatch):
    monkeypatch.setenv("ML_DEVICE", "cpu")
    det = GPUDetector()
    assert det.get_inference_device() == "cpu"


def test_bmw_ml_device_env_override(monkeypatch):
    monkeypatch.delenv("ML_DEVICE", raising=False)
    monkeypatch.setenv("BMW_ML_DEVICE", "cuda:0")
    det = GPUDetector()
    assert det.get_inference_device() == "cuda:0"


def test_detect_gpu_returns_dict():
    info = GPUDetector().detect_gpu(force=True)
    assert "available" in info
    assert "methods_tried" in info
    assert isinstance(info["methods_tried"], list)
