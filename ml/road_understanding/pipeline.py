"""Unified stateful road-understanding pipeline for Module 2G.

One sequential frame flows through Modules 2B–2F:

    segmentation -> object detection -> tracking -> depth
                 -> traffic-light state -> temporal pedestrian confirmation

Each stage can fail independently. The pipeline returns partial results and
collects warnings instead of discarding successful upstream work.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from threading import RLock
from time import perf_counter
from typing import Any

import numpy as np

from ml.road_understanding.depth_estimator import (
    DepthMap,
    MiDaSDepthEstimator,
    RoadDepthResult,
    get_depth_estimator,
)
from ml.road_understanding.object_detector import (
    RoadDetections,
    YOLORoadDetector,
    get_road_detector,
)
from ml.road_understanding.pedestrian_temporal import (
    PedestrianTemporalLocalization,
    TemporalPedestrianLocalizer,
    get_temporal_pedestrian_localizer,
)
from ml.road_understanding.road_segmenter import (
    RoadSegmentation,
    RoadSegmenter,
    get_road_segmenter,
)
from ml.road_understanding.tracker import (
    RoadObjectTracker,
    RoadTracks,
)
from ml.road_understanding.traffic_light import (
    TrafficLightClassifier,
    TrafficLightResults,
    get_traffic_light_classifier,
)


@dataclass(frozen=True)
class RoadPipelineOptions:
    """Enable/disable expensive stages without changing the result contract."""

    segmentation: bool = True
    detection_tracking: bool = True
    depth: bool = True
    traffic_lights: bool = True
    pedestrian_temporal: bool = True


@dataclass
class RoadPipelineResult:
    """Complete Module 2G result for one frame."""

    frame_index: int = 0
    segmentation: RoadSegmentation = field(default_factory=RoadSegmentation)
    detections: RoadDetections = field(default_factory=RoadDetections)
    tracks: RoadTracks = field(default_factory=RoadTracks)
    depth: RoadDepthResult = field(
        default_factory=lambda: RoadDepthResult(depth_map=DepthMap())
    )
    traffic_lights: TrafficLightResults = field(default_factory=TrafficLightResults)
    pedestrian_temporal: PedestrianTemporalLocalization = field(
        default_factory=PedestrianTemporalLocalization
    )
    processing_ms: float = 0.0
    stage_times_ms: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    message: str | None = None

    @property
    def is_valid(self) -> bool:
        """A valid input frame was processed, even if some stages degraded."""
        return self.frame_index > 0 and self.message != "Invalid frame"

    @property
    def objects(self) -> list[dict[str, Any]]:
        return [track.to_dict() for track in self.tracks.tracks]

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata and objects without full mask/depth arrays."""
        return {
            "phase": "2G",
            "frame_id": self.frame_index,
            "objects": self.objects,
            "segmentation": self.segmentation.to_dict(),
            "detections": self.detections.to_dict(),
            "tracking": self.tracks.to_dict(),
            "depth": self.depth.to_dict(),
            "traffic_lights": self.traffic_lights.to_dict(),
            "pedestrian_temporal": self.pedestrian_temporal.to_dict(),
            "processing_ms": self.processing_ms,
            "stage_times_ms": dict(self.stage_times_ms),
            "warnings": list(self.warnings),
            "message": self.message,
        }


class RoadUnderstandingPipeline:
    """Compose Modules 2B–2F for one ordered video stream.

    Instances are stateful because ByteTrack and the temporal pedestrian model
    retain history. Use one pipeline per camera/vehicle stream and call
    :meth:`reset` before reusing it for a different stream.
    """

    def __init__(
        self,
        *,
        segmenter: RoadSegmenter | Any | None = None,
        detector: YOLORoadDetector | Any | None = None,
        tracker: RoadObjectTracker | Any | None = None,
        depth_estimator: MiDaSDepthEstimator | Any | None = None,
        traffic_light_classifier: TrafficLightClassifier | Any | None = None,
        pedestrian_localizer: TemporalPedestrianLocalizer | Any | None = None,
        options: RoadPipelineOptions | None = None,
    ) -> None:
        self.segmenter = (
            segmenter if segmenter is not None else get_road_segmenter()
        )
        self.detector = detector if detector is not None else get_road_detector()
        # Stateful components must not be shared across camera streams.
        self.tracker = tracker if tracker is not None else RoadObjectTracker()
        self.depth_estimator = (
            depth_estimator
            if depth_estimator is not None
            else get_depth_estimator()
        )
        self.traffic_light_classifier = (
            traffic_light_classifier
            if traffic_light_classifier is not None
            else get_traffic_light_classifier()
        )
        self.pedestrian_localizer = (
            pedestrian_localizer
            if pedestrian_localizer is not None
            else get_temporal_pedestrian_localizer().new_session()
        )
        self.options = options or RoadPipelineOptions()
        self._frame_index = 0
        self._lock = RLock()

    @property
    def frame_index(self) -> int:
        return self._frame_index

    def reset(self) -> None:
        """Clear tracking and temporal history for a new stream."""
        with self._lock:
            if hasattr(self.tracker, "reset"):
                self.tracker.reset()
            if hasattr(self.pedestrian_localizer, "reset"):
                self.pedestrian_localizer.reset()
            self._frame_index = 0

    def process_frame(
        self,
        frame: np.ndarray,
        *,
        input_color: str = "bgr",
    ) -> RoadPipelineResult:
        """Run one frame through all enabled Module 2G stages."""
        started = perf_counter()
        try:
            image = _as_uint8_frame(frame)
            color = input_color.lower()
            if color not in {"bgr", "rgb"}:
                raise ValueError("input_color must be 'bgr' or 'rgb'")
        except Exception as exc:  # noqa: BLE001
            return RoadPipelineResult(
                processing_ms=(perf_counter() - started) * 1000.0,
                warnings=[str(exc)],
                message="Invalid frame",
            )

        with self._lock:
            self._frame_index += 1
            result = RoadPipelineResult(frame_index=self._frame_index)

            if self.options.segmentation:
                result.segmentation = self._timed(
                    result,
                    "segmentation",
                    lambda: self.segmenter.segment(image, input_color=color),
                    fallback=lambda message: RoadSegmentation(message=message),
                )
            else:
                result.segmentation.message = "Segmentation disabled"

            if self.options.detection_tracking:
                result.detections = self._timed(
                    result,
                    "detection",
                    lambda: self.detector.detect(image),
                    fallback=lambda message: RoadDetections(message=message),
                )
                result.tracks = self._timed(
                    result,
                    "tracking",
                    lambda: self.tracker.update(result.detections),
                    fallback=lambda message: RoadTracks(
                        frame_index=self._frame_index,
                        message=message,
                    ),
                )
            else:
                result.detections.message = "Detection/tracking disabled"
                result.tracks = RoadTracks(
                    frame_index=self._frame_index,
                    message="Detection/tracking disabled",
                )

            if self.options.depth:
                result.depth = self._timed(
                    result,
                    "depth",
                    lambda: self.depth_estimator.estimate_tracks(
                        image,
                        result.tracks,
                        input_color=color,
                    ),
                    fallback=lambda message: RoadDepthResult(
                        depth_map=DepthMap(message=message),
                        message=message,
                    ),
                )
                result.tracks = _apply_depth(result.tracks, result.depth)
            else:
                result.depth.message = "Depth disabled"

            if self.options.traffic_lights:
                result.traffic_lights = self._timed(
                    result,
                    "traffic_lights",
                    lambda: self.traffic_light_classifier.classify_tracks(
                        image,
                        result.tracks,
                        input_color=color,
                    ),
                    fallback=lambda message: TrafficLightResults(message=message),
                )
                result.tracks = _apply_traffic_lights(
                    result.tracks,
                    result.traffic_lights,
                )
            else:
                result.traffic_lights.message = "Traffic-light classification disabled"

            if self.options.pedestrian_temporal:
                result.pedestrian_temporal = self._timed(
                    result,
                    "pedestrian_temporal",
                    lambda: self.pedestrian_localizer.update(
                        image,
                        input_color=color,
                    ),
                    fallback=lambda message: PedestrianTemporalLocalization(
                        message=message
                    ),
                )
                try:
                    result.tracks = self.pedestrian_localizer.associate_tracks(
                        result.pedestrian_temporal,
                        result.tracks,
                    )
                except Exception as exc:  # noqa: BLE001
                    result.warnings.append(
                        f"pedestrian_temporal_association: {exc}"
                    )
            else:
                result.pedestrian_temporal.message = (
                    "Temporal pedestrian localization disabled"
                )

            result.warnings.extend(_component_warnings(result))
            result.warnings = _deduplicate(result.warnings)
            result.processing_ms = (perf_counter() - started) * 1000.0
            result.message = (
                "Road frame processed"
                if not result.warnings
                else "Road frame processed with degraded stages"
            )
            return result

    @staticmethod
    def _timed(
        result: RoadPipelineResult,
        stage: str,
        operation: Any,
        *,
        fallback: Any,
    ) -> Any:
        started = perf_counter()
        try:
            return operation()
        except Exception as exc:  # noqa: BLE001
            message = f"{stage}: {exc}"
            result.warnings.append(message)
            return fallback(message)
        finally:
            result.stage_times_ms[stage] = (perf_counter() - started) * 1000.0


def _apply_depth(tracks: RoadTracks, depth: RoadDepthResult) -> RoadTracks:
    by_id = {estimate.track_id: estimate for estimate in depth.objects}
    annotated = []
    for track in tracks.tracks:
        estimate = by_id.get(track.track_id)
        if estimate is None:
            annotated.append(track)
            continue
        annotated.append(
            replace(
                track,
                relative_inverse_depth=estimate.relative_inverse_depth,
                distance_m=estimate.distance_m,
                distance_calibrated=estimate.metric_calibrated,
            )
        )
    return replace(tracks, tracks=annotated)


def _apply_traffic_lights(
    tracks: RoadTracks,
    traffic_lights: TrafficLightResults,
) -> RoadTracks:
    by_id = {
        classification.track_id: classification
        for classification in traffic_lights.classifications
        if classification.track_id is not None
    }
    annotated = []
    for track in tracks.tracks:
        classification = by_id.get(track.track_id)
        if classification is None:
            annotated.append(track)
            continue
        annotated.append(
            replace(
                track,
                state=classification.state,
                state_confidence=classification.confidence,
            )
        )
    return replace(tracks, tracks=annotated)


def _component_warnings(result: RoadPipelineResult) -> list[str]:
    messages = [
        result.segmentation.message,
        result.detections.message,
        result.tracks.message,
        result.depth.message,
        result.depth.depth_map.message,
        result.traffic_lights.message,
        result.pedestrian_temporal.message,
    ]
    return [message for message in messages if message]


def _deduplicate(messages: list[str]) -> list[str]:
    return list(dict.fromkeys(messages))


def _as_uint8_frame(frame: np.ndarray) -> np.ndarray:
    if frame is None or getattr(frame, "size", 0) == 0:
        raise ValueError("Frame is empty")
    image = np.asarray(frame)
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Expected an HxWx3 color frame")
    if image.dtype == np.uint8:
        return image
    if np.issubdtype(image.dtype, np.floating) and image.size and image.max() <= 1.0:
        image = image * 255.0
    return np.clip(image, 0, 255).astype(np.uint8)


_pipeline: RoadUnderstandingPipeline | None = None


def get_road_pipeline() -> RoadUnderstandingPipeline:
    """Return the process-wide single-stream convenience pipeline."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RoadUnderstandingPipeline()
    return _pipeline


def process_road_frame(
    frame: np.ndarray,
    *,
    input_color: str = "bgr",
) -> RoadPipelineResult:
    """Process one frame using the process-wide single-stream pipeline."""
    return get_road_pipeline().process_frame(frame, input_color=input_color)
