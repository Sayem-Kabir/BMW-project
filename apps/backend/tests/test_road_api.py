"""Module 2H road REST/service tests with ML inference mocked."""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import numpy as np
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import road_service
from ml.road_understanding.depth_estimator import (
    DepthMap,
    ObjectDepthEstimate,
    RoadDepthResult,
)
from ml.road_understanding.pedestrian_temporal import (
    PedestrianTemporalLocalization,
)
from ml.road_understanding.pipeline import RoadPipelineResult
from ml.road_understanding.road_segmenter import RoadSegmentation
from ml.road_understanding.tracker import RoadTracks, TrackedRoadObject
from ml.road_understanding.traffic_light import (
    TrafficLightClassification,
    TrafficLightResults,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _fake_result() -> RoadPipelineResult:
    track = TrackedRoadObject(
        track_id=7,
        class_name="pedestrian",
        confidence=0.91,
        bbox_xyxy=[10.0, 20.0, 40.0, 80.0],
        age_frames=4,
        hits=4,
        confirmed=True,
        relative_inverse_depth=2.5,
        distance_m=8.0,
        distance_calibrated=True,
        temporal_confidence=0.88,
        temporal_bbox_xyxy=[11.0, 20.0, 41.0, 80.0],
        temporally_confirmed=True,
    )
    return RoadPipelineResult(
        frame_index=3,
        segmentation=RoadSegmentation(
            mask=np.zeros((20, 30), dtype=np.uint8),
            confidence=np.ones((20, 30), dtype=np.float32),
            model_loaded=True,
            weights_path="seg_road.pt",
            device="cpu",
        ),
        tracks=RoadTracks(
            tracks=[track],
            frame_index=3,
            tracker_ready=True,
            input_detection_count=1,
            detector_model_loaded=True,
        ),
        depth=RoadDepthResult(
            depth_map=DepthMap(
                relative_inverse_depth=np.ones((20, 30), dtype=np.float32),
                model_loaded=True,
                device="cpu",
                inference_ms=4.2,
            ),
            objects=[
                ObjectDepthEstimate(
                    track_id=7,
                    class_name="pedestrian",
                    relative_inverse_depth=2.5,
                    distance_m=8.0,
                    metric_calibrated=True,
                )
            ],
        ),
        traffic_lights=TrafficLightResults(
            classifications=[
                TrafficLightClassification(
                    state="RED",
                    confidence=0.9,
                    track_id=9,
                )
            ]
        ),
        pedestrian_temporal=PedestrianTemporalLocalization(
            detected=True,
            confidence=0.88,
            bbox_xyxy=[11.0, 20.0, 41.0, 80.0],
            frames_used=5,
            model_loaded=True,
            weights_path="best_pedestrian_yololstm.pt",
            device="cpu",
        ),
        processing_ms=25.0,
        stage_times_ms={"segmentation": 5.0, "detection": 7.0},
        warnings=[],
        message="Road frame processed",
    )


@pytest.mark.asyncio
async def test_road_analysis_requires_file():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/road/analysis")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_road_analysis_returns_real_pipeline_contract():
    with patch(
        "app.services.road_service.analyze_frame_bytes",
        return_value=_fake_result(),
    ) as analyze:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/road/analysis",
                params={"stream_id": "camera-front"},
                files={"file": ("frame.jpg", b"fake-jpeg", "image/jpeg")},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "2H"
    assert data["stream_id"] == "camera-front"
    assert data["frame_id"] == 3
    assert data["objects"][0]["id"] == "track_7"
    assert data["objects"][0]["track_age_frames"] == 4
    assert data["objects"][0]["temporally_confirmed"] is True
    assert data["segmentation"]["mask_shape"] == [20, 30]
    assert data["depth"]["metric_calibrated"] is True
    assert data["pipeline"]["processing_ms"] == 25.0
    analyze.assert_called_once()


@pytest.mark.asyncio
async def test_road_analysis_bad_image_returns_400():
    with patch(
        "app.services.road_service.analyze_frame_bytes",
        side_effect=ValueError("Could not decode image bytes (expected JPEG/PNG)"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/road/analysis",
                files={"file": ("bad.jpg", b"not-an-image", "image/jpeg")},
            )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reset_rest_stream_endpoint():
    with patch(
        "app.services.road_service.reset_rest_stream",
        return_value=True,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/api/v1/road/streams/camera-front")
    assert response.status_code == 200
    assert response.json()["reset"] is True


def test_decode_frame_bytes_accepts_jpeg_and_rejects_invalid_data():
    import cv2

    source = np.full((12, 16, 3), 127, dtype=np.uint8)
    ok, encoded = cv2.imencode(".jpg", source)
    assert ok

    decoded = road_service.decode_frame_bytes(encoded.tobytes())
    assert decoded.shape == source.shape

    with pytest.raises(ValueError, match="expected JPEG/PNG"):
        road_service.decode_frame_bytes(b"invalid")


def test_analysis_payload_maps_track_fields_to_schema_names():
    payload = road_service.analysis_to_api_payload(
        _fake_result(),
        stream_id="test-stream",
    )

    assert payload["objects"][0]["track_age_frames"] == 4
    assert payload["objects"][0]["track_confirmed"] is True
    assert "age_frames" not in payload["objects"][0]
    assert payload["traffic_lights"]["known_count"] == 1
    assert payload["pedestrian_temporal"]["buffered_frames"] == 5


class _FakePipeline:
    def __init__(self):
        self.reset_count = 0

    def reset(self):
        self.reset_count += 1


class _FakeStreamPipeline(_FakePipeline):
    def process_frame(self, frame, *, input_color="bgr"):
        return _fake_result()


def test_road_websocket_processes_binary_frames_and_resets():
    vehicle_id = uuid4()
    pipeline = _FakeStreamPipeline()
    with (
        patch("app.services.road_service.create_pipeline", return_value=pipeline),
        patch(
            "app.services.road_service.decode_frame_bytes",
            return_value=np.zeros((20, 30, 3), dtype=np.uint8),
        ),
        TestClient(app) as client,
        client.websocket_connect(
            f"/api/v1/road/stream/{vehicle_id}"
        ) as websocket,
    ):
        ready = websocket.receive_json()
        assert ready["type"] == "ready"
        assert ready["phase"] == "2H"

        websocket.send_bytes(b"fake-jpeg")
        message = websocket.receive_json()
        assert message["type"] == "analysis"
        assert message["payload"]["phase"] == "2H"
        assert message["payload"]["objects"][0]["id"] == "track_7"

        websocket.send_text("reset")
        assert websocket.receive_json()["type"] == "reset"

    assert pipeline.reset_count >= 1


def test_rest_session_registry_is_bounded_and_resets_evicted_pipeline():
    created = [_FakePipeline(), _FakePipeline()]
    registry = road_service.RoadPipelineSessionRegistry(max_sessions=1)

    with patch(
        "app.services.road_service.create_pipeline",
        side_effect=created,
    ):
        first = registry.get("first")
        second = registry.get("second")

    assert first is created[0]
    assert second is created[1]
    assert created[0].reset_count == 1
    assert registry.session_count == 1
