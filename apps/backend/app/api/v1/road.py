"""Road understanding API — Module 2H real frame inference."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)

from app.schemas.common import (
    RoadAnalysisResponse,
    RoadDepthSummary,
    RoadPedestrianTemporalSummary,
    RoadSegmentationSummary,
    RoadTrafficLightSummary,
    RoadTrackingSummary,
)
from app.services import road_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/road", tags=["Road Understanding"])


def _segmentation_status() -> RoadSegmentationSummary:
    """Report Module 2B weight readiness without loading the full model on every request."""
    try:
        from ml.road_understanding.config import (
            SEG_ROAD_CLASS_NAMES,
            SEG_ROAD_MODEL_PATH,
            seg_road_model_ready,
        )

        ready = seg_road_model_ready()
        return RoadSegmentationSummary(
            model_loaded=ready,
            weights_path=str(SEG_ROAD_MODEL_PATH),
            class_names=list(SEG_ROAD_CLASS_NAMES),
            message=None if ready else f"Place DeepLabV3+ checkpoint at {SEG_ROAD_MODEL_PATH}",
        )
    except Exception as exc:  # noqa: BLE001
        return RoadSegmentationSummary(model_loaded=False, message=str(exc))


def _tracking_status() -> RoadTrackingSummary:
    """Report Module 2C ByteTrack readiness without running object detection."""
    try:
        from ml.road_understanding.config import TRACK_MIN_HITS
        from ml.road_understanding.tracker import get_road_tracker

        tracker = get_road_tracker()
        return RoadTrackingSummary(
            tracker_ready=tracker.is_ready,
            frame_index=tracker.frame_index,
            min_hits=TRACK_MIN_HITS,
            message=None if tracker.is_ready else "ByteTrack failed to initialize",
        )
    except Exception as exc:  # noqa: BLE001
        return RoadTrackingSummary(tracker_ready=False, message=str(exc))


def _depth_status() -> RoadDepthSummary:
    """Report Module 2D availability without loading MiDaS on a status request."""
    try:
        import timm  # noqa: F401
        import torch  # noqa: F401

        from ml.common.gpu_detector import get_inference_device
        from ml.road_understanding.config import MIDAS_MODEL_TYPE
        from ml.road_understanding.depth_estimator import depth_estimator_loaded

        loaded = depth_estimator_loaded()
        return RoadDepthSummary(
            model_available=True,
            model_loaded=loaded,
            model_type=MIDAS_MODEL_TYPE,
            device=get_inference_device(),
            metric_calibrated=False,
            message=(
                None
                if loaded
                else "Pretrained MiDaS loads from the torch hub cache on first inference"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return RoadDepthSummary(model_available=False, message=str(exc))


def _traffic_light_status() -> RoadTrafficLightSummary:
    """Report Module 2E HSV classifier availability."""
    try:
        import cv2  # noqa: F401

        from ml.road_understanding.config import TRAFFIC_LIGHT_STATES
        from ml.road_understanding.traffic_light import (
            get_traffic_light_classifier,
        )

        get_traffic_light_classifier()
        return RoadTrafficLightSummary(
            classifier_ready=True,
            states=list(TRAFFIC_LIGHT_STATES),
        )
    except Exception as exc:  # noqa: BLE001
        return RoadTrafficLightSummary(classifier_ready=False, message=str(exc))


def _pedestrian_temporal_status() -> RoadPedestrianTemporalSummary:
    """Report Module 2F checkpoint readiness without loading the model."""
    try:
        from ml.road_understanding.config import (
            PEDESTRIAN_TEMPORAL_CONFIDENCE,
            PEDESTRIAN_TEMPORAL_INPUT_SIZE,
            PEDESTRIAN_TEMPORAL_MODEL_PATH,
            PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH,
            pedestrian_temporal_model_ready,
        )

        ready = pedestrian_temporal_model_ready()
        return RoadPedestrianTemporalSummary(
            model_loaded=ready,
            weights_path=str(PEDESTRIAN_TEMPORAL_MODEL_PATH),
            sequence_length=PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH,
            input_size=PEDESTRIAN_TEMPORAL_INPUT_SIZE,
            confidence_threshold=PEDESTRIAN_TEMPORAL_CONFIDENCE,
            message=(
                None
                if ready
                else f"Place Caltech YOLO-LSTM checkpoint at {PEDESTRIAN_TEMPORAL_MODEL_PATH}"
            ),
        )
    except Exception as exc:  # noqa: BLE001
        return RoadPedestrianTemporalSummary(model_loaded=False, message=str(exc))


@router.get("/status", response_model=RoadAnalysisResponse)
async def road_status():
    """Cheap readiness metadata without running frame inference."""
    segmentation = _segmentation_status()
    tracking = _tracking_status()
    depth = _depth_status()
    traffic_lights = _traffic_light_status()
    pedestrian_temporal = _pedestrian_temporal_status()
    return RoadAnalysisResponse(
        objects=[],
        segmentation=segmentation,
        tracking=tracking,
        depth=depth,
        traffic_lights=traffic_lights,
        pedestrian_temporal=pedestrian_temporal,
        frame_id=0,
        timestamp=datetime.now(timezone.utc),
        phase="2H",
        message=(
            "Modules 2B–2H ready"
            if (
                segmentation.model_loaded
                and tracking.tracker_ready
                and depth.model_available
                and traffic_lights.classifier_ready
                and pedestrian_temporal.model_loaded
            )
            else "Road understanding setup is incomplete"
        ),
    )


@router.post("/analysis", response_model=RoadAnalysisResponse)
async def analyze_road_frame(
    file: UploadFile = File(...),
    stream_id: str = road_service.DEFAULT_REST_STREAM_ID,
):
    """Analyze one JPEG/PNG while retaining state for the supplied stream ID."""
    image_bytes = await file.read()
    try:
        result = await asyncio.to_thread(
            road_service.analyze_frame_bytes,
            image_bytes,
            stream_id=stream_id,
        )
        payload = road_service.analysis_to_api_payload(
            result,
            stream_id=stream_id,
        )
        return RoadAnalysisResponse(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Road analysis failed")
        raise HTTPException(
            status_code=503,
            detail=f"Road pipeline unavailable: {exc}",
        ) from exc


@router.delete("/streams/{stream_id}")
async def reset_road_stream(stream_id: str):
    """Reset and remove one REST pipeline session."""
    try:
        removed = await asyncio.to_thread(
            road_service.reset_rest_stream,
            stream_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "stream_id": stream_id,
        "reset": removed,
        "message": "Stream reset" if removed else "Stream was not active",
    }


@router.websocket("/stream/{vehicle_id}")
async def road_stream(websocket: WebSocket, vehicle_id: UUID):
    """Client sends binary JPEG/PNG frames; server returns Module 2H JSON."""
    await websocket.accept()
    pipeline = None
    try:
        pipeline = await asyncio.to_thread(road_service.create_pipeline)
        await websocket.send_json(
            {
                "type": "ready",
                "vehicle_id": str(vehicle_id),
                "message": "Send JPEG/PNG frames as binary WebSocket messages.",
                "phase": "2H",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            frame_bytes: bytes | None = message.get("bytes")
            text = message.get("text")
            if frame_bytes is None:
                if text and text.strip().lower() == "reset":
                    await asyncio.to_thread(pipeline.reset)
                    await websocket.send_json(
                        {"type": "reset", "vehicle_id": str(vehicle_id)}
                    )
                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "detail": "Expected binary JPEG/PNG frame bytes",
                        }
                    )
                continue
            if not frame_bytes:
                await websocket.send_json(
                    {"type": "error", "detail": "Frame payload is empty"}
                )
                continue

            try:
                frame = await asyncio.to_thread(
                    road_service.decode_frame_bytes,
                    frame_bytes,
                )
                result = await asyncio.to_thread(
                    pipeline.process_frame,
                    frame,
                    input_color="bgr",
                )
                payload = road_service.analysis_to_api_payload(
                    result,
                    stream_id=str(vehicle_id),
                )
                response = RoadAnalysisResponse(**payload)
            except ValueError as exc:
                await websocket.send_json({"type": "error", "detail": str(exc)})
                continue
            except Exception as exc:  # noqa: BLE001
                logger.exception("Road stream analysis failed")
                await websocket.send_json(
                    {
                        "type": "error",
                        "detail": f"Road pipeline unavailable: {exc}",
                    }
                )
                continue

            await websocket.send_json(
                {
                    "type": "analysis",
                    "vehicle_id": str(vehicle_id),
                    "payload": response.model_dump(mode="json", by_alias=True),
                }
            )
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Road stream initialization failed")
        try:
            await websocket.send_json(
                {
                    "type": "error",
                    "detail": f"Road pipeline unavailable: {exc}",
                }
            )
        except Exception:  # noqa: BLE001
            pass
    finally:
        if pipeline is not None:
            await asyncio.to_thread(pipeline.reset)
