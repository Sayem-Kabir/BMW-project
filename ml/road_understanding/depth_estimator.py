"""Pretrained MiDaS monocular depth inference for Module 2D.

MiDaS predicts relative inverse depth: larger values are generally closer, but
the raw values are not meters. Per-object metric estimates use an explicit
camera calibration (scale/offset); the repository defaults remain a clearly
marked demo heuristic until calibrated with known-distance samples.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import Any

import numpy as np

from ml.common.gpu_detector import get_inference_device
from ml.road_understanding.config import (
    DEPTH_MAX_DISTANCE_M,
    DEPTH_METERS_OFFSET,
    DEPTH_METERS_SCALE,
    DEPTH_ROI_INSET_RATIO,
    MIDAS_MODEL_TYPE,
    MIDAS_REPOSITORY,
)
from ml.road_understanding.tracker import RoadTracks, TrackedRoadObject, format_track_id


@dataclass(frozen=True)
class DepthCalibration:
    """Inverse-depth conversion: meters = scale / (inverse_depth + offset)."""

    scale: float = DEPTH_METERS_SCALE
    offset: float = DEPTH_METERS_OFFSET
    calibrated: bool = False
    max_distance_m: float = DEPTH_MAX_DISTANCE_M

    def __post_init__(self) -> None:
        if not np.isfinite(self.scale) or self.scale <= 0:
            raise ValueError("Depth calibration scale must be positive")
        if not np.isfinite(self.offset):
            raise ValueError("Depth calibration offset must be finite")
        if not np.isfinite(self.max_distance_m) or self.max_distance_m <= 0:
            raise ValueError("max_distance_m must be positive")

    def to_meters(self, inverse_depth: float) -> float | None:
        denominator = float(inverse_depth) + self.offset
        if not np.isfinite(denominator) or denominator <= 1e-6:
            return None
        return min(self.scale / denominator, self.max_distance_m)


@dataclass
class DepthMap:
    """Frame-sized MiDaS relative inverse-depth output."""

    relative_inverse_depth: np.ndarray | None = None
    model_loaded: bool = False
    model_type: str = MIDAS_MODEL_TYPE
    device: str | None = None
    inference_ms: float | None = None
    message: str | None = None

    @property
    def is_valid(self) -> bool:
        return (
            self.model_loaded
            and self.relative_inverse_depth is not None
            and self.relative_inverse_depth.size > 0
        )

    def normalized_nearness(self) -> np.ndarray:
        """Return a robust uint8 map where 255 means relatively nearer."""
        if self.relative_inverse_depth is None:
            raise RuntimeError("No depth map is available")
        depth = self.relative_inverse_depth.astype(np.float32, copy=False)
        valid = depth[np.isfinite(depth)]
        if valid.size == 0:
            return np.zeros(depth.shape, dtype=np.uint8)
        low, high = np.percentile(valid, (2.0, 98.0))
        if high <= low:
            return np.zeros(depth.shape, dtype=np.uint8)
        normalized = np.clip((depth - low) / (high - low), 0.0, 1.0)
        normalized[~np.isfinite(normalized)] = 0.0
        return (normalized * 255.0).astype(np.uint8)

    def to_dict(self) -> dict[str, Any]:
        shape = (
            list(self.relative_inverse_depth.shape)
            if self.relative_inverse_depth is not None
            else None
        )
        return {
            "model_loaded": self.model_loaded,
            "model_type": self.model_type,
            "device": self.device,
            "map_shape": shape,
            "inference_ms": self.inference_ms,
            "message": self.message,
        }


@dataclass
class ObjectDepthEstimate:
    """Depth sampled from the inner region of one tracked bounding box."""

    track_id: int
    class_name: str
    bbox_xyxy: list[float] = field(default_factory=list)
    relative_inverse_depth: float | None = None
    distance_m: float | None = None
    metric_calibrated: bool = False

    @property
    def id(self) -> str:
        return format_track_id(self.track_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "track_id": self.track_id,
            "class": self.class_name,
            "bbox": self.bbox_xyxy,
            "relative_inverse_depth": self.relative_inverse_depth,
            "distance_m": self.distance_m,
            "metric_calibrated": self.metric_calibrated,
        }


@dataclass
class RoadDepthResult:
    """Module 2D frame depth plus track-associated distance estimates."""

    depth_map: DepthMap
    objects: list[ObjectDepthEstimate] = field(default_factory=list)
    message: str | None = None

    @property
    def is_valid(self) -> bool:
        return self.depth_map.is_valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth": self.depth_map.to_dict(),
            "objects": [obj.to_dict() for obj in self.objects],
            "count": len(self.objects),
            "message": self.message,
        }


class MiDaSDepthEstimator:
    """Lazy pretrained MiDaS loader and per-track distance estimator."""

    def __init__(
        self,
        *,
        model_type: str = MIDAS_MODEL_TYPE,
        device: str | int | None = None,
        calibration: DepthCalibration | None = None,
        roi_inset_ratio: float = DEPTH_ROI_INSET_RATIO,
        auto_load: bool = True,
        model: Any | None = None,
        transform: Any | None = None,
    ) -> None:
        self.model_type = model_type
        self.device = get_inference_device(device)
        self.calibration = calibration or DepthCalibration()
        self.roi_inset_ratio = float(roi_inset_ratio)
        self._model = model
        self._transform = transform
        self._load_error: str | None = None

        if not 0.0 <= self.roi_inset_ratio < 0.5:
            raise ValueError("roi_inset_ratio must be in [0, 0.5)")
        if (self._model is None) != (self._transform is None):
            raise ValueError("model and transform must be provided together")
        if self._model is not None:
            self._prepare_model()
        elif auto_load:
            self._load_model()

    def _prepare_model(self) -> None:
        self._model.to(self.device)
        self._model.eval()
        self._load_error = None

    def _load_model(self) -> None:
        try:
            import torch

            self._model = torch.hub.load(
                MIDAS_REPOSITORY,
                self.model_type,
                trust_repo=True,
                skip_validation=True,
            )
            transforms = torch.hub.load(
                MIDAS_REPOSITORY,
                "transforms",
                trust_repo=True,
                skip_validation=True,
            )
            if self.model_type in {"DPT_Large", "DPT_Hybrid", "DPT_BEiT_L_512"}:
                self._transform = transforms.dpt_transform
            else:
                self._transform = transforms.small_transform
            self._prepare_model()
        except Exception as exc:  # noqa: BLE001
            self._model = None
            self._transform = None
            self._load_error = str(exc)

    @property
    def is_ready(self) -> bool:
        return self._model is not None and self._transform is not None

    def estimate(self, frame: np.ndarray, *, input_color: str = "bgr") -> DepthMap:
        """Infer a frame-sized relative inverse-depth map."""
        if frame is None or getattr(frame, "size", 0) == 0:
            return self._empty_result("Empty frame")
        if not self.is_ready:
            return self._empty_result(self._load_error or "MiDaS model is not loaded")

        started = perf_counter()
        try:
            import torch
            import torch.nn.functional as functional

            image = _as_uint8_image(frame)
            color = input_color.lower()
            if color == "bgr":
                image = image[..., ::-1]
            elif color != "rgb":
                raise ValueError("input_color must be 'bgr' or 'rgb'")

            model_input = self._transform(np.ascontiguousarray(image))
            if isinstance(model_input, dict):
                model_input = model_input.get("image")
            if model_input is None:
                raise ValueError("MiDaS transform did not return an image tensor")
            if model_input.ndim == 3:
                model_input = model_input.unsqueeze(0)
            model_input = model_input.to(self.device)

            with torch.inference_mode():
                prediction = self._model(model_input)
                if isinstance(prediction, dict):
                    prediction = prediction.get("out")
                if isinstance(prediction, (tuple, list)):
                    prediction = prediction[0]
                if prediction is None:
                    raise ValueError("MiDaS model returned no prediction")
                if prediction.ndim == 2:
                    prediction = prediction.unsqueeze(0).unsqueeze(0)
                elif prediction.ndim == 3:
                    prediction = prediction.unsqueeze(1)
                prediction = functional.interpolate(
                    prediction,
                    size=image.shape[:2],
                    mode="bicubic",
                    align_corners=False,
                ).squeeze()

            depth = prediction.to("cpu", dtype=torch.float32).numpy()
            return DepthMap(
                relative_inverse_depth=depth,
                model_loaded=True,
                model_type=self.model_type,
                device=self.device,
                inference_ms=(perf_counter() - started) * 1000.0,
            )
        except Exception as exc:  # noqa: BLE001
            result = self._empty_result(f"Depth estimation failed: {exc}")
            result.inference_ms = (perf_counter() - started) * 1000.0
            return result

    def estimate_tracks(
        self,
        frame: np.ndarray,
        tracks: RoadTracks,
        *,
        input_color: str = "bgr",
    ) -> RoadDepthResult:
        """Infer frame depth and sample it inside each tracked object box."""
        depth_map = self.estimate(frame, input_color=input_color)
        if not depth_map.is_valid or depth_map.relative_inverse_depth is None:
            return RoadDepthResult(depth_map=depth_map, message=depth_map.message)

        objects = [
            self._estimate_object(depth_map.relative_inverse_depth, track)
            for track in tracks.tracks
        ]
        message = None
        if not self.calibration.calibrated:
            message = (
                "relative_inverse_depth is available; distance_m stays null until "
                "MiDaS scale/offset are calibrated for this camera"
            )
        return RoadDepthResult(depth_map=depth_map, objects=objects, message=message)

    def annotate_tracks(
        self,
        frame: np.ndarray,
        tracks: RoadTracks,
        *,
        input_color: str = "bgr",
    ) -> RoadTracks:
        """Return a copy of ``tracks`` with Module 2D depth fields filled in."""
        depth_result = self.estimate_tracks(frame, tracks, input_color=input_color)
        by_id = {obj.track_id: obj for obj in depth_result.objects}
        annotated = []
        for track in tracks.tracks:
            estimate = by_id.get(track.track_id)
            annotated.append(
                replace(
                    track,
                    relative_inverse_depth=(
                        estimate.relative_inverse_depth if estimate else None
                    ),
                    distance_m=estimate.distance_m if estimate else None,
                    distance_calibrated=(
                        estimate.metric_calibrated if estimate else False
                    ),
                )
            )

        message = depth_result.message or tracks.message
        return RoadTracks(
            tracks=annotated,
            frame_index=tracks.frame_index,
            tracker_ready=tracks.tracker_ready,
            input_detection_count=tracks.input_detection_count,
            dropped_detection_count=tracks.dropped_detection_count,
            detector_model_loaded=tracks.detector_model_loaded,
            detector_using_fallback=tracks.detector_using_fallback,
            message=message,
        )

    def _estimate_object(
        self,
        inverse_depth_map: np.ndarray,
        track: TrackedRoadObject,
    ) -> ObjectDepthEstimate:
        relative = sample_bbox_inverse_depth(
            inverse_depth_map,
            track.bbox_xyxy,
            inset_ratio=self.roi_inset_ratio,
        )
        distance = None
        if self.calibration.calibrated and relative is not None:
            distance = self.calibration.to_meters(relative)
        return ObjectDepthEstimate(
            track_id=track.track_id,
            class_name=track.class_name,
            bbox_xyxy=list(track.bbox_xyxy),
            relative_inverse_depth=relative,
            distance_m=distance,
            metric_calibrated=self.calibration.calibrated,
        )

    def _empty_result(self, message: str) -> DepthMap:
        return DepthMap(
            model_loaded=self.is_ready,
            model_type=self.model_type,
            device=self.device,
            message=message,
        )


def sample_bbox_inverse_depth(
    inverse_depth_map: np.ndarray,
    bbox_xyxy: list[float],
    *,
    inset_ratio: float = DEPTH_ROI_INSET_RATIO,
) -> float | None:
    """Robustly sample median inverse depth from a clipped inner box region."""
    depth = np.asarray(inverse_depth_map)
    if depth.ndim != 2 or depth.size == 0:
        raise ValueError("inverse_depth_map must be a non-empty HxW array")
    if not 0.0 <= inset_ratio < 0.5:
        raise ValueError("inset_ratio must be in [0, 0.5)")

    bbox = np.asarray(bbox_xyxy, dtype=np.float64)
    if bbox.shape != (4,) or not np.all(np.isfinite(bbox)):
        return None

    height, width = depth.shape
    x1 = int(np.floor(np.clip(bbox[0], 0, width)))
    y1 = int(np.floor(np.clip(bbox[1], 0, height)))
    x2 = int(np.ceil(np.clip(bbox[2], 0, width)))
    y2 = int(np.ceil(np.clip(bbox[3], 0, height)))
    if x2 <= x1 or y2 <= y1:
        return None

    inset_x = int((x2 - x1) * inset_ratio)
    inset_y = int((y2 - y1) * inset_ratio)
    inner_x1, inner_x2 = x1 + inset_x, x2 - inset_x
    inner_y1, inner_y2 = y1 + inset_y, y2 - inset_y
    if inner_x2 <= inner_x1 or inner_y2 <= inner_y1:
        return None

    values = depth[inner_y1:inner_y2, inner_x1:inner_x2]
    valid = values[np.isfinite(values) & (values > 0)]
    if valid.size == 0:
        return None
    return float(np.median(valid))


def _as_uint8_image(frame: np.ndarray) -> np.ndarray:
    image = np.asarray(frame)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Expected an HxWx3 color frame")
    if image.dtype == np.uint8:
        return image
    if np.issubdtype(image.dtype, np.floating) and image.size and image.max() <= 1.0:
        image = image * 255.0
    return np.clip(image, 0, 255).astype(np.uint8)


_depth_estimator: MiDaSDepthEstimator | None = None


def depth_estimator_loaded() -> bool:
    """Return whether the process-wide pretrained model is already in memory."""
    return _depth_estimator is not None and _depth_estimator.is_ready


def get_depth_estimator() -> MiDaSDepthEstimator:
    global _depth_estimator
    if _depth_estimator is None:
        _depth_estimator = MiDaSDepthEstimator()
    return _depth_estimator


def estimate_depth(frame: np.ndarray, *, input_color: str = "bgr") -> DepthMap:
    """Estimate relative inverse depth with the process-wide Module 2D model."""
    return get_depth_estimator().estimate(frame, input_color=input_color)


def estimate_track_depths(
    frame: np.ndarray,
    tracks: RoadTracks,
    *,
    input_color: str = "bgr",
) -> RoadDepthResult:
    """Estimate depth and associate distances with Module 2C tracks."""
    return get_depth_estimator().estimate_tracks(
        frame,
        tracks,
        input_color=input_color,
    )


def annotate_track_depths(
    frame: np.ndarray,
    tracks: RoadTracks,
    *,
    input_color: str = "bgr",
) -> RoadTracks:
    """Attach Module 2D depth fields onto Module 2C tracks."""
    return get_depth_estimator().annotate_tracks(
        frame,
        tracks,
        input_color=input_color,
    )
