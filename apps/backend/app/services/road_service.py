"""Module 2H service adapter for the Module 2G road pipeline."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone
from threading import RLock
from typing import Any

import numpy as np

MAX_FRAME_BYTES = 10 * 1024 * 1024
DEFAULT_REST_STREAM_ID = "rest-default"


def decode_frame_bytes(image_bytes: bytes) -> np.ndarray:
    """Decode a bounded JPEG/PNG payload into one OpenCV BGR frame."""
    if not image_bytes:
        raise ValueError("Frame payload is empty")
    if len(image_bytes) > MAX_FRAME_BYTES:
        raise ValueError(
            f"Frame payload exceeds {MAX_FRAME_BYTES // (1024 * 1024)} MB limit"
        )

    import cv2

    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if frame is None or frame.size == 0:
        raise ValueError("Could not decode image bytes (expected JPEG/PNG)")
    return frame


def create_pipeline() -> Any:
    """Create one independent tracker/temporal session with shared model weights."""
    from ml.road_understanding.pipeline import RoadUnderstandingPipeline

    with _pipeline_factory_lock:
        return RoadUnderstandingPipeline()


class RoadPipelineSessionRegistry:
    """Bounded LRU registry for REST clients that submit sequential frames."""

    def __init__(self, max_sessions: int = 16) -> None:
        if max_sessions < 1:
            raise ValueError("max_sessions must be positive")
        self.max_sessions = int(max_sessions)
        self._sessions: OrderedDict[str, Any] = OrderedDict()
        self._lock = RLock()

    def get(self, stream_id: str) -> Any:
        key = _validate_stream_id(stream_id)
        with self._lock:
            existing = self._sessions.pop(key, None)
            if existing is not None:
                self._sessions[key] = existing
                return existing

            pipeline = create_pipeline()
            self._sessions[key] = pipeline
            while len(self._sessions) > self.max_sessions:
                _, evicted = self._sessions.popitem(last=False)
                evicted.reset()
            return pipeline

    def remove(self, stream_id: str) -> bool:
        key = _validate_stream_id(stream_id)
        with self._lock:
            pipeline = self._sessions.pop(key, None)
        if pipeline is None:
            return False
        pipeline.reset()
        return True

    def clear(self) -> None:
        with self._lock:
            pipelines = list(self._sessions.values())
            self._sessions.clear()
        for pipeline in pipelines:
            pipeline.reset()

    @property
    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)


def analyze_frame_bytes(
    image_bytes: bytes,
    *,
    stream_id: str = DEFAULT_REST_STREAM_ID,
) -> Any:
    """Decode and process one REST frame while preserving stream state."""
    frame = decode_frame_bytes(image_bytes)
    pipeline = _rest_sessions.get(stream_id)
    return pipeline.process_frame(frame, input_color="bgr")


def analysis_to_api_payload(
    result: Any,
    *,
    stream_id: str | None = None,
) -> dict[str, Any]:
    """Map the ML dataclasses to the stable Pydantic road API contract."""
    from ml.road_understanding.config import (
        PEDESTRIAN_TEMPORAL_CONFIDENCE,
        PEDESTRIAN_TEMPORAL_INPUT_SIZE,
        PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH,
    )

    segmentation = result.segmentation.to_dict()
    depth_map = result.depth.depth_map.to_dict()
    temporal = result.pedestrian_temporal
    tracks = result.tracks
    traffic = result.traffic_lights

    objects = [
        {
            "id": track.id,
            "class": track.class_name,
            "confidence": track.confidence,
            "bbox": list(track.bbox_xyxy),
            "track_id": track.track_id,
            "track_age_frames": track.age_frames,
            "track_hits": track.hits,
            "track_confirmed": track.confirmed,
            "relative_inverse_depth": track.relative_inverse_depth,
            "distance_m": track.distance_m,
            "distance_calibrated": track.distance_calibrated,
            "state": track.state,
            "state_confidence": track.state_confidence,
            "temporal_confidence": track.temporal_confidence,
            "temporal_bbox": track.temporal_bbox_xyxy,
            "temporally_confirmed": track.temporally_confirmed,
        }
        for track in tracks.tracks
    ]

    metric_calibrated = any(
        estimate.metric_calibrated for estimate in result.depth.objects
    )
    traffic_failed = any(
        warning.startswith("traffic_lights:") for warning in result.warnings
    )

    return {
        "objects": objects,
        "segmentation": segmentation,
        "tracking": {
            "tracker_ready": tracks.tracker_ready,
            "frame_index": tracks.frame_index,
            "active_tracks": len(tracks.tracks),
            "confirmed_tracks": len(tracks.confirmed_tracks),
            "message": tracks.message,
        },
        "depth": {
            "model_available": depth_map["model_loaded"],
            "model_loaded": depth_map["model_loaded"],
            "model_type": depth_map["model_type"],
            "device": depth_map["device"],
            "map_shape": depth_map["map_shape"],
            "inference_ms": depth_map["inference_ms"],
            "metric_calibrated": metric_calibrated,
            "message": result.depth.message or depth_map["message"],
        },
        "traffic_lights": {
            "classifier_ready": not traffic_failed,
            "classified_count": len(traffic.classifications),
            "known_count": sum(item.is_known for item in traffic.classifications),
            "message": traffic.message,
        },
        "pedestrian_temporal": {
            "model_loaded": temporal.model_loaded,
            "weights_path": temporal.weights_path,
            "sequence_length": PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH,
            "input_size": PEDESTRIAN_TEMPORAL_INPUT_SIZE,
            "confidence_threshold": PEDESTRIAN_TEMPORAL_CONFIDENCE,
            "buffered_frames": temporal.frames_used,
            "detected": temporal.detected,
            "confidence": temporal.confidence,
            "bbox": temporal.bbox_xyxy,
            "message": temporal.message,
        },
        "pipeline": {
            "processing_ms": result.processing_ms,
            "stage_times_ms": dict(result.stage_times_ms),
            "warnings": list(result.warnings),
        },
        "stream_id": stream_id,
        "frame_id": result.frame_index,
        "timestamp": datetime.now(timezone.utc),
        "phase": "2H",
        "message": result.message or "Road frame processed",
    }


def reset_rest_stream(stream_id: str) -> bool:
    return _rest_sessions.remove(stream_id)


def _validate_stream_id(stream_id: str) -> str:
    key = str(stream_id).strip()
    if not key:
        raise ValueError("stream_id must not be empty")
    if len(key) > 128:
        raise ValueError("stream_id must be at most 128 characters")
    return key


_pipeline_factory_lock = RLock()
_rest_sessions = RoadPipelineSessionRegistry()
