"""Shared ML utilities (GPU detection, etc.)."""

from ml.common.gpu_detector import (
    GPUDetector,
    get_gpu_info,
    get_inference_device,
    gpu_detector,
)

__all__ = [
    "GPUDetector",
    "gpu_detector",
    "get_inference_device",
    "get_gpu_info",
]
