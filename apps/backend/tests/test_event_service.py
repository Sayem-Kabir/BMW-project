"""Module 4E event persistence and clip service tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services import event_service
from app.services.video_clip_buffer import VideoClipBuffer
from ml.risk_engine import SafetyEvent as DetectedSafetyEvent


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _detected(event_type: str = "NEAR_COLLISION") -> DetectedSafetyEvent:
    return DetectedSafetyEvent(
        event_type=event_type,
        severity="CRITICAL",
        reason="Near collision: TTC 1.7s (threshold 2.0s)",
        evidence={"ttc_seconds": 1.7, "object_class": "car", "distance_m": 9.8},
        telemetry_snapshot={
            "speed_kmh": 58.0,
            "ttc_seconds": 1.7,
            "object_distance_m": 9.8,
            "driver_ear": 0.22,
            "risk_score_at_event": 94.0,
        },
    )


def test_build_xai_explanation_uses_rule_templates() -> None:
    text = event_service.build_xai_explanation(_detected())

    assert "1.7s" in text
    assert "0.22" in text


def test_row_from_detected_event_maps_snapshot_fields() -> None:
    vehicle_id = uuid4()
    driver_id = uuid4()
    detected = _detected()

    row = event_service.row_from_detected_event(
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        detected=detected,
        evaluated_at=datetime(2026, 7, 20, 7, 0, tzinfo=timezone.utc),
    )

    assert row.vehicle_id == vehicle_id
    assert row.driver_id == driver_id
    assert row.event_type == "NEAR_COLLISION"
    assert row.severity == "CRITICAL"
    assert row.telemetry_snapshot["speed_kmh"] == 58.0
    assert row.xai_explanation
    assert "1.7s" in row.xai_explanation


def test_video_clip_buffer_collects_recent_window() -> None:
    buffer = VideoClipBuffer(duration_seconds=2.0, fps=1.0)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    buffer.append_jpeg(b"a", timestamp=start)
    buffer.append_jpeg(b"b", timestamp=start.replace(second=1))
    buffer.append_jpeg(b"c", timestamp=start.replace(second=3))

    frames = buffer.collect_clip(anchor=start.replace(second=3))

    assert frames == [b"b", b"c"]


@pytest.mark.asyncio
async def test_persist_detected_events_commits_rows_and_uploads_clip():
    vehicle_id = uuid4()
    driver_id = uuid4()
    detection = MagicMock()
    detection.events = (_detected(),)
    detection.timestamp = datetime(2026, 7, 20, 7, 0, tzinfo=timezone.utc)
    detection.warnings = ()
    detection.skipped_detectors = ()

    session = AsyncMock()
    session.refresh = AsyncMock()

    with (
        patch(
            "app.services.event_service.materialize_clip_bytes",
            return_value=b"FAKE_MP4",
        ),
        patch(
            "app.services.event_service.upload_clip_for_event",
            return_value="minio://safety-events/demo.mp4",
        ) as upload,
    ):
        rows = await event_service.persist_detected_events(
            session,
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            detection=detection,
            attach_clips=True,
        )

    assert len(rows) == 1
    session.add.assert_called_once()
    session.commit.assert_called()
    upload.assert_called_once()
    assert rows[0].video_clip_url == "minio://safety-events/demo.mp4"


@pytest.mark.asyncio
async def test_detect_and_persist_runs_detector_and_returns_payload():
    vehicle_id = uuid4()
    driver_id = uuid4()
    detection = MagicMock()
    detection.events = ()
    detection.warnings = ("speed_kmh missing",)
    detection.skipped_detectors = ("hard_braking",)

    with (
        patch(
            "app.services.event_service.detect_events",
            return_value=detection,
        ),
        patch(
            "app.core.database.async_session_maker",
        ) as session_maker,
        patch(
            "app.services.event_service.persist_detected_events",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.__aexit__.return_value = None
        session_maker.return_value = session

        payload = await event_service.detect_and_persist(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            driver_state={"phone_detected": False},
            road_state={"objects": []},
            telemetry={"speed_kmh": 40.0},
        )

    assert payload["vehicle_id"] == str(vehicle_id)
    assert payload["phase"] == "4E"
    assert payload["detected"] == 0
    assert payload["warnings"] == ["speed_kmh missing"]


def test_post_process_event_retries_clip_upload():
    from app.tasks.events import post_process_event

    with patch(
        "app.services.event_service.upload_missing_clip",
        new_callable=AsyncMock,
        return_value="minio://safety-events/retry.mp4",
    ):
        result = post_process_event(str(uuid4()), str(uuid4()))

    assert result["status"] == "ok"
    assert result["video_clip_url"] == "minio://safety-events/retry.mp4"
    assert result["phase"] == "4F"
