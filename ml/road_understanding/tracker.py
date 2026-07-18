"""ByteTrack object tracking for Module 2C.

Module 2B semantic segmentation produces pixel masks and cannot be tracked by
ByteTrack. Module 2C therefore consumes the separate road-object detections
from ``object_detector.py`` and assigns persistent IDs across video frames.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from ml.road_understanding.config import (
    TRACK_ACTIVATION_THRESHOLD,
    TRACK_FRAME_RATE,
    TRACK_MAX_AGE,
    TRACK_MIN_HITS,
    TRACK_MINIMUM_MATCHING_THRESHOLD,
)
from ml.road_understanding.object_detector import (
    RoadDetection,
    RoadDetections,
    YOLORoadDetector,
    get_road_detector,
)


def format_track_id(track_id: int) -> str:
    """Spec-shaped track ID used by the road API (`track_12`)."""
    return f"track_{int(track_id)}"


@dataclass
class TrackedRoadObject:
    """One detection associated with a persistent ByteTrack ID."""

    track_id: int
    class_name: str
    confidence: float
    bbox_xyxy: list[float] = field(default_factory=list)
    class_id: int | None = None
    age_frames: int = 1
    hits: int = 1
    confirmed: bool = False
    relative_inverse_depth: float | None = None
    distance_m: float | None = None
    distance_calibrated: bool = False
    state: str | None = None
    state_confidence: float | None = None
    temporal_confidence: float | None = None
    temporal_bbox_xyxy: list[float] | None = None
    temporally_confirmed: bool = False

    @property
    def id(self) -> str:
        return format_track_id(self.track_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "track_id": self.track_id,
            "class": self.class_name,
            "confidence": self.confidence,
            "bbox": self.bbox_xyxy,
            "class_id": self.class_id,
            "age_frames": self.age_frames,
            "hits": self.hits,
            "confirmed": self.confirmed,
            "relative_inverse_depth": self.relative_inverse_depth,
            "distance_m": self.distance_m,
            "distance_calibrated": self.distance_calibrated,
            "state": self.state,
            "state_confidence": self.state_confidence,
            "temporal_confidence": self.temporal_confidence,
            "temporal_bbox": self.temporal_bbox_xyxy,
            "temporally_confirmed": self.temporally_confirmed,
        }


@dataclass
class RoadTracks:
    """Tracked objects returned for one frame."""

    tracks: list[TrackedRoadObject] = field(default_factory=list)
    frame_index: int = 0
    tracker_ready: bool = False
    input_detection_count: int = 0
    dropped_detection_count: int = 0
    detector_model_loaded: bool | None = None
    detector_using_fallback: bool | None = None
    message: str | None = None

    @property
    def confirmed_tracks(self) -> list[TrackedRoadObject]:
        return [track for track in self.tracks if track.confirmed]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tracks": [track.to_dict() for track in self.tracks],
            "count": len(self.tracks),
            "confirmed_count": len(self.confirmed_tracks),
            "frame_index": self.frame_index,
            "tracker_ready": self.tracker_ready,
            "input_detection_count": self.input_detection_count,
            "dropped_detection_count": self.dropped_detection_count,
            "detector_model_loaded": self.detector_model_loaded,
            "detector_using_fallback": self.detector_using_fallback,
            "message": self.message,
        }


@dataclass
class _TrackState:
    first_seen: int
    last_seen: int
    hits: int = 0


class RoadObjectTracker:
    """Stateful ByteTrack adapter for sequential road-camera frames.

    Matching uses ``TRACK_MINIMUM_MATCHING_THRESHOLD`` (0.80), not the looser
    ``TRACK_IOU_THRESHOLD`` reserved for downstream overlap checks. Confirmation
    uses application-level ``min_hits`` while ByteTrack itself emits IDs from
    the first matched frame so short clips remain usable.
    """

    def __init__(
        self,
        *,
        track_activation_threshold: float = TRACK_ACTIVATION_THRESHOLD,
        lost_track_buffer: int = TRACK_MAX_AGE,
        minimum_matching_threshold: float = TRACK_MINIMUM_MATCHING_THRESHOLD,
        frame_rate: int = TRACK_FRAME_RATE,
        min_hits: int = TRACK_MIN_HITS,
        tracker_backend: Any | None = None,
    ) -> None:
        self.track_activation_threshold = float(track_activation_threshold)
        self.lost_track_buffer = int(lost_track_buffer)
        self.minimum_matching_threshold = float(minimum_matching_threshold)
        self.frame_rate = int(frame_rate)
        self.min_hits = int(min_hits)
        self._tracker: Any | None = tracker_backend
        self._load_error: str | None = None
        self._frame_index = 0
        self._states: dict[int, _TrackState] = {}

        if self.lost_track_buffer < 1:
            raise ValueError("lost_track_buffer must be positive")
        if self.frame_rate < 1:
            raise ValueError("frame_rate must be positive")
        if self.min_hits < 1:
            raise ValueError("min_hits must be positive")
        if not 0.0 <= self.track_activation_threshold <= 1.0:
            raise ValueError("track_activation_threshold must be between 0 and 1")
        if not 0.0 <= self.minimum_matching_threshold <= 1.0:
            raise ValueError("minimum_matching_threshold must be between 0 and 1")

        if self._tracker is None:
            self._load_tracker()

    def _load_tracker(self) -> None:
        try:
            import supervision as sv

            self._tracker = sv.ByteTrack(
                track_activation_threshold=self.track_activation_threshold,
                lost_track_buffer=self.lost_track_buffer,
                minimum_matching_threshold=self.minimum_matching_threshold,
                frame_rate=self.frame_rate,
                # Expose IDs immediately; `confirmed` applies our min_hits rule.
                minimum_consecutive_frames=1,
            )
            self._load_error = None
        except Exception as exc:  # noqa: BLE001
            self._tracker = None
            self._load_error = str(exc)

    @property
    def is_ready(self) -> bool:
        return self._tracker is not None

    @property
    def frame_index(self) -> int:
        return self._frame_index

    def reset(self) -> None:
        """Clear all active tracks before starting a new video/session."""
        if self._tracker is not None and hasattr(self._tracker, "reset"):
            self._tracker.reset()
        else:
            self._load_tracker()
        self._frame_index = 0
        self._states.clear()

    def update(self, detections: RoadDetections) -> RoadTracks:
        """Update tracks from one frame's object detections."""
        self._frame_index += 1
        input_count = len(detections.detections)

        if not self.is_ready:
            return self._result(
                detections,
                input_count=input_count,
                message=self._load_error or "ByteTrack is not available",
            )

        valid, dropped = _validated_detections(detections.detections)

        try:
            sv_detections = _to_supervision_detections(valid)
            tracked = self._tracker.update_with_detections(sv_detections)
            tracks = self._from_supervision_detections(tracked)
            self._prune_states()
            message = detections.message if detections.message else None
            return self._result(
                detections,
                tracks=tracks,
                input_count=input_count,
                dropped_count=dropped,
                message=message,
            )
        except Exception as exc:  # noqa: BLE001
            return self._result(
                detections,
                input_count=input_count,
                dropped_count=dropped,
                message=f"Tracking failed: {exc}",
            )

    def track_frame(
        self,
        frame: np.ndarray,
        *,
        detector: YOLORoadDetector | None = None,
    ) -> RoadTracks:
        """Run object detection and tracking for one sequential frame."""
        road_detector = detector or get_road_detector()
        return self.update(road_detector.detect(frame))

    def _from_supervision_detections(self, detections: Any) -> list[TrackedRoadObject]:
        tracker_ids = getattr(detections, "tracker_id", None)
        if tracker_ids is None:
            return []

        names = getattr(detections, "data", {}).get("class_name")
        tracks: list[TrackedRoadObject] = []
        for index, raw_track_id in enumerate(tracker_ids):
            if raw_track_id is None:
                continue
            track_id = int(raw_track_id)
            state = self._states.get(track_id)
            if state is None:
                state = _TrackState(
                    first_seen=self._frame_index,
                    last_seen=self._frame_index,
                )
                self._states[track_id] = state
            state.last_seen = self._frame_index
            state.hits += 1

            class_id = _array_value(getattr(detections, "class_id", None), index)
            confidence = _array_value(getattr(detections, "confidence", None), index)
            class_name = str(names[index]) if names is not None else str(class_id)
            tracks.append(
                TrackedRoadObject(
                    track_id=track_id,
                    class_name=class_name,
                    confidence=float(confidence if confidence is not None else 0.0),
                    bbox_xyxy=[
                        float(value) for value in detections.xyxy[index].tolist()
                    ],
                    class_id=(
                        int(class_id)
                        if class_id is not None and int(class_id) >= 0
                        else None
                    ),
                    age_frames=self._frame_index - state.first_seen + 1,
                    hits=state.hits,
                    confirmed=state.hits >= self.min_hits,
                )
            )
        return tracks

    def _prune_states(self) -> None:
        oldest_frame = self._frame_index - self.lost_track_buffer
        self._states = {
            track_id: state
            for track_id, state in self._states.items()
            if state.last_seen > oldest_frame
        }

    def _result(
        self,
        detections: RoadDetections,
        *,
        tracks: list[TrackedRoadObject] | None = None,
        input_count: int,
        dropped_count: int = 0,
        message: str | None = None,
    ) -> RoadTracks:
        return RoadTracks(
            tracks=tracks or [],
            frame_index=self._frame_index,
            tracker_ready=self.is_ready,
            input_detection_count=input_count,
            dropped_detection_count=dropped_count,
            detector_model_loaded=detections.model_loaded,
            detector_using_fallback=detections.using_fallback,
            message=message,
        )


def _validated_detections(
    detections: list[RoadDetection],
) -> tuple[list[RoadDetection], int]:
    valid: list[RoadDetection] = []
    for detection in detections:
        bbox = np.asarray(detection.bbox_xyxy, dtype=np.float32)
        if (
            bbox.shape != (4,)
            or not np.all(np.isfinite(bbox))
            or bbox[2] <= bbox[0]
            or bbox[3] <= bbox[1]
            or not np.isfinite(detection.confidence)
        ):
            continue
        valid.append(detection)
    return valid, len(detections) - len(valid)


def _to_supervision_detections(detections: list[RoadDetection]) -> Any:
    import supervision as sv

    if not detections:
        return sv.Detections.empty()
    return sv.Detections(
        xyxy=np.asarray([detection.bbox_xyxy for detection in detections], dtype=np.float32),
        confidence=np.asarray(
            [detection.confidence for detection in detections],
            dtype=np.float32,
        ),
        class_id=np.asarray(
            [
                detection.class_id if detection.class_id is not None else -1
                for detection in detections
            ],
            dtype=int,
        ),
        data={
            "class_name": np.asarray(
                [detection.class_name for detection in detections],
                dtype=str,
            )
        },
    )


def _array_value(array: Any, index: int) -> Any | None:
    if array is None or len(array) <= index:
        return None
    return array[index]


_tracker: RoadObjectTracker | None = None


def get_road_tracker() -> RoadObjectTracker:
    global _tracker
    if _tracker is None:
        _tracker = RoadObjectTracker()
    return _tracker


def track_road_objects(detections: RoadDetections) -> RoadTracks:
    """Update the process-wide Module 2C tracker."""
    return get_road_tracker().update(detections)


def detect_and_track_road_objects(frame: np.ndarray) -> RoadTracks:
    """Detect and track one frame with process-wide detector/tracker instances."""
    return get_road_tracker().track_frame(frame)
