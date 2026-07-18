"""HSV traffic-light state classification for Module 2E.

The classifier consumes YOLO/ByteTrack traffic-light crops and labels each as
RED, AMBER, GREEN, or UNKNOWN. It uses no trained model and preserves all
segmentation, tracking, and depth fields when annotating tracks.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np

from ml.road_understanding.config import (
    TRAFFIC_LIGHT_AMBER_HUE_RANGE,
    TRAFFIC_LIGHT_GREEN_HUE_RANGE,
    TRAFFIC_LIGHT_MIN_ACTIVE_PIXELS,
    TRAFFIC_LIGHT_MIN_ACTIVE_RATIO,
    TRAFFIC_LIGHT_MIN_COLOR_CONFIDENCE,
    TRAFFIC_LIGHT_MIN_CROP_PX,
    TRAFFIC_LIGHT_MIN_DOMINANCE_MARGIN,
    TRAFFIC_LIGHT_MIN_SATURATION,
    TRAFFIC_LIGHT_MIN_VALUE,
    TRAFFIC_LIGHT_RED_HUE_RANGES,
    TRAFFIC_LIGHT_STATES,
)
from ml.road_understanding.tracker import RoadTracks, TrackedRoadObject, format_track_id


@dataclass
class TrafficLightClassification:
    """HSV result for one crop or one tracked traffic light."""

    state: str = "UNKNOWN"
    confidence: float = 0.0
    color_scores: dict[str, float] = field(default_factory=dict)
    track_id: int | None = None
    bbox_xyxy: list[float] = field(default_factory=list)
    active_pixels: int = 0
    crop_size: tuple[int, int] | None = None
    message: str | None = None

    @property
    def id(self) -> str | None:
        return format_track_id(self.track_id) if self.track_id is not None else None

    @property
    def is_known(self) -> bool:
        return self.state != "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "track_id": self.track_id,
            "state": self.state,
            "confidence": self.confidence,
            "color_scores": self.color_scores,
            "bbox": self.bbox_xyxy,
            "active_pixels": self.active_pixels,
            "crop_size": list(self.crop_size) if self.crop_size else None,
            "message": self.message,
        }


@dataclass
class TrafficLightResults:
    """Module 2E classifications for one frame."""

    classifications: list[TrafficLightClassification] = field(default_factory=list)
    input_track_count: int = 0
    skipped_non_traffic_lights: int = 0
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "classifications": [
                classification.to_dict()
                for classification in self.classifications
            ],
            "count": len(self.classifications),
            "known_count": sum(
                classification.is_known
                for classification in self.classifications
            ),
            "input_track_count": self.input_track_count,
            "skipped_non_traffic_lights": self.skipped_non_traffic_lights,
            "message": self.message,
        }


class TrafficLightClassifier:
    """Classify active traffic-light colors with OpenCV HSV masks."""

    def __init__(
        self,
        *,
        min_crop_px: int = TRAFFIC_LIGHT_MIN_CROP_PX,
        min_saturation: int = TRAFFIC_LIGHT_MIN_SATURATION,
        min_value: int = TRAFFIC_LIGHT_MIN_VALUE,
        min_active_pixels: int = TRAFFIC_LIGHT_MIN_ACTIVE_PIXELS,
        min_active_ratio: float = TRAFFIC_LIGHT_MIN_ACTIVE_RATIO,
        min_color_confidence: float = TRAFFIC_LIGHT_MIN_COLOR_CONFIDENCE,
        min_dominance_margin: float = TRAFFIC_LIGHT_MIN_DOMINANCE_MARGIN,
    ) -> None:
        self.min_crop_px = int(min_crop_px)
        self.min_saturation = int(min_saturation)
        self.min_value = int(min_value)
        self.min_active_pixels = int(min_active_pixels)
        self.min_active_ratio = float(min_active_ratio)
        self.min_color_confidence = float(min_color_confidence)
        self.min_dominance_margin = float(min_dominance_margin)

        if self.min_crop_px < 1 or self.min_active_pixels < 1:
            raise ValueError("Pixel thresholds must be positive")
        if not 0.0 <= self.min_active_ratio <= 1.0:
            raise ValueError("min_active_ratio must be between 0 and 1")
        if not 0.0 <= self.min_color_confidence <= 1.0:
            raise ValueError("min_color_confidence must be between 0 and 1")
        if not 0.0 <= self.min_dominance_margin <= 1.0:
            raise ValueError("min_dominance_margin must be between 0 and 1")

    def classify_crop(
        self,
        crop: np.ndarray,
        *,
        input_color: str = "bgr",
        track_id: int | None = None,
        bbox_xyxy: list[float] | None = None,
    ) -> TrafficLightClassification:
        """Classify one tightly cropped traffic-light image."""
        if crop is None or getattr(crop, "size", 0) == 0:
            return self._unknown("Empty traffic-light crop", track_id, bbox_xyxy)

        try:
            import cv2

            image = _as_uint8_image(crop)
            height, width = image.shape[:2]
            if height < self.min_crop_px or width < self.min_crop_px:
                return self._unknown(
                    f"Traffic-light crop must be at least {self.min_crop_px}px per side",
                    track_id,
                    bbox_xyxy,
                    crop_size=(height, width),
                )

            color = input_color.lower()
            if color == "bgr":
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            elif color == "rgb":
                hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
            else:
                raise ValueError("input_color must be 'bgr' or 'rgb'")

            hue = hsv[..., 0]
            saturated_bright = (
                (hsv[..., 1] >= self.min_saturation)
                & (hsv[..., 2] >= self.min_value)
            )
            red = saturated_bright & (
                _hue_mask(hue, TRAFFIC_LIGHT_RED_HUE_RANGES[0])
                | _hue_mask(hue, TRAFFIC_LIGHT_RED_HUE_RANGES[1])
            )
            amber = saturated_bright & _hue_mask(
                hue,
                TRAFFIC_LIGHT_AMBER_HUE_RANGE,
            )
            green = saturated_bright & _hue_mask(
                hue,
                TRAFFIC_LIGHT_GREEN_HUE_RANGE,
            )

            counts = {
                "RED": int(np.count_nonzero(red)),
                "AMBER": int(np.count_nonzero(amber)),
                "GREEN": int(np.count_nonzero(green)),
            }
            active_pixels = sum(counts.values())
            scores = {
                state: count / active_pixels if active_pixels else 0.0
                for state, count in counts.items()
            }
            ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
            best_state, confidence = ordered[0]
            second_score = ordered[1][1]
            required_pixels = max(
                self.min_active_pixels,
                int(np.ceil(height * width * self.min_active_ratio)),
            )

            state = best_state
            message = None
            if active_pixels < required_pixels:
                state = "UNKNOWN"
                message = "Insufficient saturated color pixels"
            elif confidence < self.min_color_confidence:
                state = "UNKNOWN"
                message = "No traffic-light color reached confidence threshold"
            elif confidence - second_score < self.min_dominance_margin:
                state = "UNKNOWN"
                message = "Traffic-light colors are ambiguous"

            return TrafficLightClassification(
                state=state,
                confidence=float(confidence),
                color_scores=scores,
                track_id=track_id,
                bbox_xyxy=list(bbox_xyxy or []),
                active_pixels=active_pixels,
                crop_size=(height, width),
                message=message,
            )
        except Exception as exc:  # noqa: BLE001
            return self._unknown(
                f"Traffic-light classification failed: {exc}",
                track_id,
                bbox_xyxy,
            )

    def classify_track(
        self,
        frame: np.ndarray,
        track: TrackedRoadObject,
        *,
        input_color: str = "bgr",
    ) -> TrafficLightClassification | None:
        """Classify one track, or return None when it is not a traffic light."""
        if _normalize_class(track.class_name) != "traffic light":
            return None
        try:
            image = _as_uint8_image(frame)
        except Exception as exc:  # noqa: BLE001
            return self._unknown(
                f"Invalid frame: {exc}",
                track.track_id,
                track.bbox_xyxy,
            )

        clipped = _clip_bbox(track.bbox_xyxy, image.shape[:2])
        if clipped is None:
            return self._unknown(
                "Invalid or out-of-frame traffic-light box",
                track.track_id,
                track.bbox_xyxy,
            )
        x1, y1, x2, y2 = clipped
        crop = image[y1:y2, x1:x2]
        return self.classify_crop(
            crop,
            input_color=input_color,
            track_id=track.track_id,
            bbox_xyxy=[float(x1), float(y1), float(x2), float(y2)],
        )

    def classify_tracks(
        self,
        frame: np.ndarray,
        tracks: RoadTracks,
        *,
        input_color: str = "bgr",
    ) -> TrafficLightResults:
        classifications = []
        for track in tracks.tracks:
            result = self.classify_track(frame, track, input_color=input_color)
            if result is not None:
                classifications.append(result)
        return TrafficLightResults(
            classifications=classifications,
            input_track_count=len(tracks.tracks),
            skipped_non_traffic_lights=len(tracks.tracks) - len(classifications),
        )

    def annotate_tracks(
        self,
        frame: np.ndarray,
        tracks: RoadTracks,
        *,
        input_color: str = "bgr",
    ) -> RoadTracks:
        """Return tracks with RED/AMBER/GREEN/UNKNOWN state fields attached."""
        results = self.classify_tracks(frame, tracks, input_color=input_color)
        by_id = {
            classification.track_id: classification
            for classification in results.classifications
            if classification.track_id is not None
        }
        annotated = []
        for track in tracks.tracks:
            classification = by_id.get(track.track_id)
            if classification is None:
                annotated.append(track)
            else:
                annotated.append(
                    replace(
                        track,
                        state=classification.state,
                        state_confidence=classification.confidence,
                    )
                )
        return replace(tracks, tracks=annotated)

    @staticmethod
    def _unknown(
        message: str,
        track_id: int | None,
        bbox_xyxy: list[float] | None,
        *,
        crop_size: tuple[int, int] | None = None,
    ) -> TrafficLightClassification:
        return TrafficLightClassification(
            state="UNKNOWN",
            color_scores={"RED": 0.0, "AMBER": 0.0, "GREEN": 0.0},
            track_id=track_id,
            bbox_xyxy=list(bbox_xyxy or []),
            crop_size=crop_size,
            message=message,
        )


def _hue_mask(hue: np.ndarray, bounds: tuple[int, int]) -> np.ndarray:
    return (hue >= bounds[0]) & (hue <= bounds[1])


def _normalize_class(name: str) -> str:
    return " ".join(name.lower().replace("_", " ").replace("-", " ").split())


def _clip_bbox(
    bbox_xyxy: list[float],
    frame_shape: tuple[int, int],
) -> tuple[int, int, int, int] | None:
    bbox = np.asarray(bbox_xyxy, dtype=np.float64)
    if bbox.shape != (4,) or not np.all(np.isfinite(bbox)):
        return None
    height, width = frame_shape
    x1 = int(np.floor(np.clip(bbox[0], 0, width)))
    y1 = int(np.floor(np.clip(bbox[1], 0, height)))
    x2 = int(np.ceil(np.clip(bbox[2], 0, width)))
    y2 = int(np.ceil(np.clip(bbox[3], 0, height)))
    if x2 <= x1 or y2 <= y1:
        return None
    return x1, y1, x2, y2


def _as_uint8_image(image: np.ndarray) -> np.ndarray:
    array = np.asarray(image)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("Expected an HxWx3 color image")
    if array.dtype == np.uint8:
        return array
    if np.issubdtype(array.dtype, np.floating) and array.size and array.max() <= 1.0:
        array = array * 255.0
    return np.clip(array, 0, 255).astype(np.uint8)


_classifier: TrafficLightClassifier | None = None


def get_traffic_light_classifier() -> TrafficLightClassifier:
    global _classifier
    if _classifier is None:
        _classifier = TrafficLightClassifier()
    return _classifier


def classify_traffic_lights(
    frame: np.ndarray,
    tracks: RoadTracks,
    *,
    input_color: str = "bgr",
) -> TrafficLightResults:
    """Classify traffic-light states for Module 2C tracks."""
    return get_traffic_light_classifier().classify_tracks(
        frame,
        tracks,
        input_color=input_color,
    )


def annotate_traffic_light_states(
    frame: np.ndarray,
    tracks: RoadTracks,
    *,
    input_color: str = "bgr",
) -> RoadTracks:
    """Attach Module 2E states to traffic-light tracks."""
    return get_traffic_light_classifier().annotate_tracks(
        frame,
        tracks,
        input_color=input_color,
    )
