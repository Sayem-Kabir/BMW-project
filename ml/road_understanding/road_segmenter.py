"""DeepLabV3+ road segmentation inference for Module 2B.

The architecture and preprocessing mirror ``notebooks/train_road_seg.ipynb``:
ResNet50 encoder, three output classes, 512x512 input, and ImageNet
normalization. OpenCV-style BGR frames are accepted by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ml.common.gpu_detector import get_inference_device
from ml.road_understanding.config import (
    SEG_ROAD_BACKGROUND_CLASS_ID,
    SEG_ROAD_CLASS_COLORS_BGR,
    SEG_ROAD_CLASS_NAMES,
    SEG_ROAD_INPUT_SIZE,
    SEG_ROAD_MODEL_PATH,
    SEG_ROAD_OVERLAY_ALPHA,
)


@dataclass
class RoadSegmentation:
    """Pixel-level Module 2B result in the original frame resolution."""

    mask: np.ndarray | None = None
    confidence: np.ndarray | None = None
    model_loaded: bool = False
    weights_path: str | None = None
    device: str | None = None
    checkpoint_epoch: int | None = None
    checkpoint_val_acc: float | None = None
    message: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.model_loaded and self.mask is not None

    def class_ratios(self) -> dict[str, float]:
        if self.mask is None or self.mask.size == 0:
            return {name: 0.0 for name in SEG_ROAD_CLASS_NAMES}
        total = float(self.mask.size)
        return {
            name: float(np.count_nonzero(self.mask == class_id)) / total
            for class_id, name in enumerate(SEG_ROAD_CLASS_NAMES)
        }

    def binary_mask(self, class_id: int) -> np.ndarray:
        if class_id < 0 or class_id >= len(SEG_ROAD_CLASS_NAMES):
            raise ValueError(f"class_id must be between 0 and {len(SEG_ROAD_CLASS_NAMES) - 1}")
        if self.mask is None:
            raise RuntimeError("No segmentation mask is available")
        return (self.mask == class_id).astype(np.uint8) * 255

    def color_mask(self) -> np.ndarray:
        if self.mask is None:
            raise RuntimeError("No segmentation mask is available")
        palette = np.asarray(SEG_ROAD_CLASS_COLORS_BGR, dtype=np.uint8)
        return palette[self.mask]

    def overlay(
        self,
        frame: np.ndarray,
        *,
        alpha: float = SEG_ROAD_OVERLAY_ALPHA,
    ) -> np.ndarray:
        """Blend road/shoulder colors onto an original BGR frame."""
        if self.mask is None:
            raise RuntimeError("No segmentation mask is available")
        if frame.shape[:2] != self.mask.shape:
            raise ValueError("Frame and segmentation mask dimensions must match")
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be between 0 and 1")

        base = _as_uint8_image(frame)
        colors = self.color_mask()
        blended = (
            base.astype(np.float32) * (1.0 - alpha)
            + colors.astype(np.float32) * alpha
        ).astype(np.uint8)
        foreground = self.mask != SEG_ROAD_BACKGROUND_CLASS_ID
        result = base.copy()
        result[foreground] = blended[foreground]
        return result

    def to_dict(self) -> dict[str, Any]:
        """Return API-friendly metadata without serializing full-resolution arrays."""
        shape = list(self.mask.shape) if self.mask is not None else None
        mean_confidence = (
            float(self.confidence.mean())
            if self.confidence is not None and self.confidence.size
            else None
        )
        return {
            "model_loaded": self.model_loaded,
            "weights_path": self.weights_path,
            "device": self.device,
            "mask_shape": shape,
            "class_names": list(SEG_ROAD_CLASS_NAMES),
            "class_ratios": self.class_ratios(),
            "mean_confidence": mean_confidence,
            "checkpoint_epoch": self.checkpoint_epoch,
            "checkpoint_val_acc": self.checkpoint_val_acc,
            "message": self.message,
        }


def _as_uint8_image(frame: np.ndarray) -> np.ndarray:
    array = np.asarray(frame)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("Expected an HxWx3 color frame")
    if array.dtype == np.uint8:
        return array
    if np.issubdtype(array.dtype, np.floating) and array.size and array.max() <= 1.0:
        array = array * 255.0
    return np.clip(array, 0, 255).astype(np.uint8)


class RoadSegmenter:
    """Load ``seg_road.pt`` and produce road/shoulder/background masks."""

    def __init__(
        self,
        model_path: str | Path = SEG_ROAD_MODEL_PATH,
        *,
        device: str | int | None = None,
        input_size: int = SEG_ROAD_INPUT_SIZE,
        auto_load: bool = True,
    ) -> None:
        self.model_path = Path(model_path)
        self.device = get_inference_device(device)
        self.input_size = int(input_size)
        self._model: Any | None = None
        self._load_error: str | None = None
        self.checkpoint_epoch: int | None = None
        self.checkpoint_val_acc: float | None = None

        if self.input_size <= 0:
            raise ValueError("input_size must be positive")
        if auto_load:
            self._load_model()

    def _load_model(self) -> None:
        if not self.model_path.is_file() or self.model_path.stat().st_size == 0:
            self._model = None
            self._load_error = f"Segmentation weights not found: {self.model_path}"
            return

        try:
            import segmentation_models_pytorch as smp
            import torch

            model = smp.DeepLabV3Plus(
                encoder_name="resnet50",
                encoder_weights=None,
                in_channels=3,
                classes=len(SEG_ROAD_CLASS_NAMES),
            )
            try:
                checkpoint = torch.load(
                    self.model_path,
                    map_location=self.device,
                    weights_only=True,
                )
            except TypeError:
                checkpoint = torch.load(self.model_path, map_location=self.device)

            if not isinstance(checkpoint, dict):
                raise ValueError("Checkpoint must be a dictionary")
            state_dict = checkpoint.get("model_state_dict", checkpoint)
            if not isinstance(state_dict, dict):
                raise ValueError("Checkpoint does not contain a model_state_dict")
            if any(str(key).startswith("module.") for key in state_dict):
                state_dict = {
                    str(key).removeprefix("module."): value
                    for key, value in state_dict.items()
                }

            model.load_state_dict(state_dict, strict=True)
            model.to(self.device)
            model.eval()
            self._model = model
            self.checkpoint_epoch = _optional_int(checkpoint.get("epoch"))
            self.checkpoint_val_acc = _optional_float(checkpoint.get("val_acc"))
            self._load_error = None
        except Exception as exc:  # noqa: BLE001
            self._model = None
            self._load_error = str(exc)

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def segment(
        self,
        frame: np.ndarray,
        *,
        input_color: str = "bgr",
    ) -> RoadSegmentation:
        if frame is None or getattr(frame, "size", 0) == 0:
            return self._result(message="Empty frame")
        if not self.is_ready:
            return self._result(message=self._load_error or "Segmentation model is not loaded")

        try:
            import torch
            import torch.nn.functional as functional

            image = _as_uint8_image(frame)
            if input_color.lower() == "bgr":
                image = image[..., ::-1]
            elif input_color.lower() != "rgb":
                raise ValueError("input_color must be 'bgr' or 'rgb'")

            tensor = torch.from_numpy(np.ascontiguousarray(image))
            tensor = tensor.permute(2, 0, 1).unsqueeze(0).float().div_(255.0)
            tensor = functional.interpolate(
                tensor,
                size=(self.input_size, self.input_size),
                mode="bilinear",
                align_corners=False,
            )
            mean = tensor.new_tensor((0.485, 0.456, 0.406)).view(1, 3, 1, 1)
            std = tensor.new_tensor((0.229, 0.224, 0.225)).view(1, 3, 1, 1)
            tensor = ((tensor - mean) / std).to(self.device)

            with torch.inference_mode():
                logits = self._model(tensor)
                logits = functional.interpolate(
                    logits,
                    size=image.shape[:2],
                    mode="bilinear",
                    align_corners=False,
                )
                probabilities = torch.softmax(logits, dim=1)
                confidence, mask = probabilities.max(dim=1)

            return RoadSegmentation(
                mask=mask[0].to("cpu", dtype=torch.uint8).numpy(),
                confidence=confidence[0].to("cpu", dtype=torch.float32).numpy(),
                model_loaded=True,
                weights_path=str(self.model_path),
                device=self.device,
                checkpoint_epoch=self.checkpoint_epoch,
                checkpoint_val_acc=self.checkpoint_val_acc,
            )
        except Exception as exc:  # noqa: BLE001
            return self._result(message=f"Segmentation failed: {exc}")

    def _result(self, *, message: str) -> RoadSegmentation:
        return RoadSegmentation(
            model_loaded=self.is_ready,
            weights_path=str(self.model_path),
            device=self.device,
            checkpoint_epoch=self.checkpoint_epoch,
            checkpoint_val_acc=self.checkpoint_val_acc,
            message=message,
        )


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


_segmenter: RoadSegmenter | None = None


def get_road_segmenter() -> RoadSegmenter:
    global _segmenter
    if _segmenter is None:
        _segmenter = RoadSegmenter()
    return _segmenter


def segment_road(frame: np.ndarray, *, input_color: str = "bgr") -> RoadSegmentation:
    """Segment one frame with the process-wide lazy Module 2B model."""
    return get_road_segmenter().segment(frame, input_color=input_color)
