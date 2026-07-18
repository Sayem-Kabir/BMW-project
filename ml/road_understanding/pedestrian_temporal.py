"""Caltech-trained temporal pedestrian localization for Module 2F.

This model is not a crossing-intent classifier. It uses a YOLOv8n backbone and
an LSTM over consecutive full frames to predict one primary pedestrian
bounding box plus confidence. The output can confirm/reacquire a ByteTrack
pedestrian through short detector dropouts, but it makes no behavioral claim.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from ml.common.gpu_detector import get_inference_device
from ml.road_understanding.config import (
    PEDESTRIAN_TEMPORAL_CONFIDENCE,
    PEDESTRIAN_TEMPORAL_HIDDEN_SIZE,
    PEDESTRIAN_TEMPORAL_INPUT_SIZE,
    PEDESTRIAN_TEMPORAL_MODEL_PATH,
    PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH,
)
from ml.road_understanding.tracker import RoadTracks, TrackedRoadObject


def _build_backbone() -> Any:
    """Build the exact YOLOv8n feature extractor used by the checkpoint."""
    import torch.nn as nn
    from ultralytics import YOLO

    yolo = YOLO("yolov8n.yaml")
    return nn.Sequential(*list(yolo.model.model.children())[:10])


def build_temporal_model(
    *,
    input_size: int = PEDESTRIAN_TEMPORAL_INPUT_SIZE,
    hidden_size: int = PEDESTRIAN_TEMPORAL_HIDDEN_SIZE,
) -> Any:
    """Construct the checkpoint-compatible YOLOv8n-backbone + LSTM network."""
    import torch
    import torch.nn as nn

    if input_size != 224:
        raise ValueError(
            "The current checkpoint architecture requires input_size=224 "
            "(256 x 7 x 7 flattened backbone features)"
        )

    class TemporalPedestrianYOLOLSTM(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.backbone = _build_backbone()
            self.lstm = nn.LSTM(
                input_size=256 * 7 * 7,
                hidden_size=hidden_size,
                num_layers=1,
                batch_first=True,
            )
            self.fc_bbox = nn.Linear(hidden_size, 4)
            self.fc_conf = nn.Linear(hidden_size, 1)

        def forward(self, frames: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            batch, steps, channels, height, width = frames.shape
            features = self.backbone(
                frames.reshape(batch * steps, channels, height, width)
            )
            features = features.flatten(1).reshape(batch, steps, -1)
            _, (hidden, _) = self.lstm(features)
            temporal = hidden[-1]
            bbox_xywh = torch.sigmoid(self.fc_bbox(temporal))
            confidence = torch.sigmoid(self.fc_conf(temporal)).squeeze(-1)
            return bbox_xywh, confidence

    return TemporalPedestrianYOLOLSTM()


@dataclass
class PedestrianTemporalLocalization:
    """Primary-pedestrian prediction from one frame sequence."""

    detected: bool = False
    confidence: float = 0.0
    bbox_xyxy: list[float] | None = None
    normalized_bbox_xywh: list[float] | None = None
    frames_used: int = 0
    model_loaded: bool = False
    weights_path: str | None = None
    device: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "detected": self.detected,
            "confidence": self.confidence,
            "bbox": self.bbox_xyxy,
            "normalized_bbox_xywh": self.normalized_bbox_xywh,
            "frames_used": self.frames_used,
            "model_loaded": self.model_loaded,
            "weights_path": self.weights_path,
            "device": self.device,
            "message": self.message,
        }


class TemporalPedestrianLocalizer:
    """Stateful sequence buffer and inference wrapper for Module 2F."""

    def __init__(
        self,
        model_path: str | Path = PEDESTRIAN_TEMPORAL_MODEL_PATH,
        *,
        sequence_length: int = PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH,
        input_size: int = PEDESTRIAN_TEMPORAL_INPUT_SIZE,
        confidence_threshold: float = PEDESTRIAN_TEMPORAL_CONFIDENCE,
        device: str | int | None = None,
        auto_load: bool = True,
        model: Any | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.sequence_length = int(sequence_length)
        self.input_size = int(input_size)
        self.confidence_threshold = float(confidence_threshold)
        self.device = get_inference_device(device)
        self._model = model
        self._load_error: str | None = None
        self._frames: deque[np.ndarray] = deque(maxlen=self.sequence_length)

        if self.sequence_length < 1:
            raise ValueError("sequence_length must be positive")
        if self.input_size < 1:
            raise ValueError("input_size must be positive")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")

        if self._model is not None:
            self._prepare_model()
        elif auto_load:
            self._load_model()

    def _prepare_model(self) -> None:
        self._model.to(self.device)
        self._model.eval()
        self._load_error = None

    def _load_model(self) -> None:
        if not self.model_path.is_file() or self.model_path.stat().st_size == 0:
            self._model = None
            self._load_error = f"Temporal pedestrian weights not found: {self.model_path}"
            return
        try:
            import torch

            model = build_temporal_model(
                input_size=self.input_size,
                hidden_size=PEDESTRIAN_TEMPORAL_HIDDEN_SIZE,
            )
            try:
                checkpoint = torch.load(
                    self.model_path,
                    map_location=self.device,
                    weights_only=True,
                )
            except TypeError:
                checkpoint = torch.load(self.model_path, map_location=self.device)
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                checkpoint = checkpoint["model_state_dict"]
            if not isinstance(checkpoint, dict):
                raise ValueError("Checkpoint must contain a state_dict")
            model.load_state_dict(checkpoint, strict=True)
            self._model = model
            self._prepare_model()
        except Exception as exc:  # noqa: BLE001
            self._model = None
            self._load_error = str(exc)

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def buffered_frames(self) -> int:
        return len(self._frames)

    def reset(self) -> None:
        self._frames.clear()

    def new_session(self) -> TemporalPedestrianLocalizer:
        """Create an independent frame buffer while sharing loaded weights."""
        if self._model is None:
            return TemporalPedestrianLocalizer(
                model_path=self.model_path,
                sequence_length=self.sequence_length,
                input_size=self.input_size,
                confidence_threshold=self.confidence_threshold,
                device=self.device,
            )
        return TemporalPedestrianLocalizer(
            model_path=self.model_path,
            sequence_length=self.sequence_length,
            input_size=self.input_size,
            confidence_threshold=self.confidence_threshold,
            device=self.device,
            auto_load=False,
            model=self._model,
        )

    def update(
        self,
        frame: np.ndarray,
        *,
        input_color: str = "bgr",
    ) -> PedestrianTemporalLocalization:
        """Add one video frame and infer once the temporal window is full."""
        if frame is None or getattr(frame, "size", 0) == 0:
            return self._result(message="Empty frame")
        try:
            self._frames.append(_as_uint8_image(frame).copy())
        except Exception as exc:  # noqa: BLE001
            return self._result(message=f"Invalid frame: {exc}")

        if len(self._frames) < self.sequence_length:
            return self._result(
                message=(
                    f"Warming temporal buffer: {len(self._frames)}/"
                    f"{self.sequence_length} frames"
                )
            )
        return self.localize(self._frames, input_color=input_color)

    def localize(
        self,
        frames: Iterable[np.ndarray],
        *,
        input_color: str = "bgr",
    ) -> PedestrianTemporalLocalization:
        """Predict the primary pedestrian box from the latest frame sequence."""
        sequence = list(frames)
        if len(sequence) < self.sequence_length:
            return self._result(
                message=(
                    f"Need {self.sequence_length} frames, received {len(sequence)}"
                )
            )
        if not self.is_ready:
            return self._result(
                message=self._load_error or "Temporal pedestrian model is not loaded"
            )

        sequence = sequence[-self.sequence_length :]
        try:
            import cv2
            import torch

            tensors = []
            for frame in sequence:
                image = _as_uint8_image(frame)
                color = input_color.lower()
                if color == "bgr":
                    image = image[..., ::-1]
                elif color != "rgb":
                    raise ValueError("input_color must be 'bgr' or 'rgb'")
                resized = cv2.resize(
                    np.ascontiguousarray(image),
                    (self.input_size, self.input_size),
                    interpolation=cv2.INTER_LINEAR,
                )
                tensor = (
                    torch.from_numpy(resized)
                    .permute(2, 0, 1)
                    .float()
                    .div_(255.0)
                )
                tensors.append(tensor)

            batch = torch.stack(tensors).unsqueeze(0).to(self.device)
            with torch.inference_mode():
                bbox_xywh, confidence = self._model(batch)

            normalized = (
                bbox_xywh[0].detach().to("cpu", dtype=torch.float32).numpy()
            )
            normalized = np.clip(normalized, 0.0, 1.0)
            score = float(confidence[0].detach().to("cpu"))
            last_height, last_width = _as_uint8_image(sequence[-1]).shape[:2]
            bbox_xyxy = _normalized_xywh_to_xyxy(
                normalized,
                width=last_width,
                height=last_height,
            )
            detected = score >= self.confidence_threshold and _box_area(bbox_xyxy) > 0
            return PedestrianTemporalLocalization(
                detected=detected,
                confidence=score,
                bbox_xyxy=bbox_xyxy if detected else None,
                normalized_bbox_xywh=[float(value) for value in normalized],
                frames_used=self.sequence_length,
                model_loaded=True,
                weights_path=str(self.model_path),
                device=self.device,
                message=None if detected else "Primary pedestrian confidence below threshold",
            )
        except Exception as exc:  # noqa: BLE001
            return self._result(message=f"Temporal pedestrian inference failed: {exc}")

    def associate_tracks(
        self,
        localization: PedestrianTemporalLocalization,
        tracks: RoadTracks,
        *,
        minimum_iou: float = 0.30,
    ) -> RoadTracks:
        """Attach temporal confirmation to the best-overlapping pedestrian track."""
        if not 0.0 <= minimum_iou <= 1.0:
            raise ValueError("minimum_iou must be between 0 and 1")
        if not localization.detected or localization.bbox_xyxy is None:
            return tracks

        candidates = [
            track
            for track in tracks.tracks
            if _normalize_class(track.class_name) == "pedestrian"
        ]
        if not candidates:
            return tracks
        best = max(
            candidates,
            key=lambda track: _bbox_iou(
                localization.bbox_xyxy or [],
                track.bbox_xyxy,
            ),
        )
        overlap = _bbox_iou(localization.bbox_xyxy, best.bbox_xyxy)
        if overlap < minimum_iou:
            return tracks

        annotated = [
            (
                replace(
                    track,
                    temporal_confidence=localization.confidence,
                    temporal_bbox_xyxy=list(localization.bbox_xyxy),
                    temporally_confirmed=True,
                )
                if track.track_id == best.track_id
                else track
            )
            for track in tracks.tracks
        ]
        return replace(tracks, tracks=annotated)

    def _result(self, *, message: str) -> PedestrianTemporalLocalization:
        return PedestrianTemporalLocalization(
            frames_used=len(self._frames),
            model_loaded=self.is_ready,
            weights_path=str(self.model_path),
            device=self.device,
            message=message,
        )


def _normalized_xywh_to_xyxy(
    bbox_xywh: np.ndarray,
    *,
    width: int,
    height: int,
) -> list[float]:
    center_x, center_y, box_width, box_height = map(float, bbox_xywh)
    x1 = np.clip(center_x - box_width / 2.0, 0.0, 1.0) * width
    y1 = np.clip(center_y - box_height / 2.0, 0.0, 1.0) * height
    x2 = np.clip(center_x + box_width / 2.0, 0.0, 1.0) * width
    y2 = np.clip(center_y + box_height / 2.0, 0.0, 1.0) * height
    return [float(x1), float(y1), float(x2), float(y2)]


def _bbox_iou(first: list[float], second: list[float]) -> float:
    if len(first) != 4 or len(second) != 4:
        return 0.0
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = _box_area(first) + _box_area(second) - intersection
    return intersection / union if union > 0 else 0.0


def _box_area(box: list[float]) -> float:
    if len(box) != 4:
        return 0.0
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _normalize_class(name: str) -> str:
    return " ".join(name.lower().replace("_", " ").replace("-", " ").split())


def _as_uint8_image(frame: np.ndarray) -> np.ndarray:
    image = np.asarray(frame)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Expected an HxWx3 color frame")
    if image.dtype == np.uint8:
        return image
    if np.issubdtype(image.dtype, np.floating) and image.size and image.max() <= 1.0:
        image = image * 255.0
    return np.clip(image, 0, 255).astype(np.uint8)


_localizer: TemporalPedestrianLocalizer | None = None


def get_temporal_pedestrian_localizer() -> TemporalPedestrianLocalizer:
    global _localizer
    if _localizer is None:
        _localizer = TemporalPedestrianLocalizer()
    return _localizer


def localize_primary_pedestrian(
    frames: Iterable[np.ndarray],
    *,
    input_color: str = "bgr",
) -> PedestrianTemporalLocalization:
    """Run Module 2F on an explicit frame sequence."""
    return get_temporal_pedestrian_localizer().localize(
        frames,
        input_color=input_color,
    )
