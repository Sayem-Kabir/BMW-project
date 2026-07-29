"""Module 7B — offline demo runner (video replay + synthetic telemetry).

Usage:

    python -m ml.demo.demo_runner
    python -m ml.demo.demo_runner --api http://127.0.0.1:8000 --loop --fps 5
    python -m ml.demo.demo_runner --synthetic-only   # no video required

Place an optional dashcam clip at ml/demo/assets/demo_drive.mp4
(or set DEMO_VIDEO_PATH). When missing, synthetic frames are used.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import httpx
import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDEO = Path(__file__).resolve().parent / "assets" / "demo_drive.mp4"
DEFAULT_API = os.environ.get("DEMO_API_URL", "http://127.0.0.1:8000")
DEMO_VEHICLE = "00000000-0000-4000-8000-000000000003"
DEMO_DRIVER = "00000000-0000-4000-8000-000000000001"
DEMO_SESSION = "00000000-0000-4000-8000-000000000002"
PHASE = "7B"


def _synthetic_frame(frame_idx: int, width: int = 640, height: int = 360) -> np.ndarray:
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (28 + (frame_idx % 20), 32, 40)
    # Fake face / eyes region for driver analysis + Grad-CAM demos
    cx = width // 2 + int(20 * np.sin(frame_idx / 8.0))
    cy = height // 2
    cv2.ellipse(frame, (cx, cy), (90, 110), 0, 0, 360, (70, 70, 90), -1)
    ear_open = 0.18 if (frame_idx // 15) % 4 == 0 else 0.28
    eye_h = max(4, int(18 * ear_open / 0.3))
    cv2.ellipse(frame, (cx - 35, cy - 20), (18, eye_h), 0, 0, 360, (200, 200, 220), -1)
    cv2.ellipse(frame, (cx + 35, cy - 20), (18, eye_h), 0, 0, 360, (200, 200, 220), -1)
    cv2.putText(
        frame,
        f"DEMO {frame_idx}",
        (16, 32),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (180, 180, 200),
        2,
    )
    return frame


def _encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Failed to encode JPEG frame")
    return buf.tobytes()


def _telemetry_for_frame(frame_idx: int) -> dict[str, Any]:
    # Oscillate speed / GPS around Munich demo coords
    t = frame_idx / 30.0
    return {
        "speed_kmh": round(45 + 25 * abs(np.sin(t)), 1),
        "latitude": 48.1351 + 0.001 * np.sin(t),
        "longitude": 11.5820 + 0.001 * np.cos(t),
        "battery_soc_pct": round(72 - (frame_idx % 100) * 0.05, 1),
        "tire_rl": 32.0 if frame_idx % 40 else 22.0,
    }


def _driver_state_for_frame(frame_idx: int) -> dict[str, Any]:
    drowsy_burst = (frame_idx // 20) % 5 == 0
    return {
        "is_drowsy": drowsy_burst,
        "ear_value": 0.18 if drowsy_burst else 0.28,
        "consecutive_drowsy_frames": 65 if drowsy_burst else frame_idx % 10,
        "phone_detected": False,
        "seatbelt_worn": True,
    }


def _road_state_for_frame(frame_idx: int) -> dict[str, Any]:
    close = (frame_idx // 25) % 6 == 0
    return {
        "objects": [
            {
                "class": "car",
                "distance_m": 8.5 if close else 28.0,
                "relative_speed_kmh": 55.0 if close else 5.0,
                "track_id": 1,
                "confirmed": True,
            }
        ]
    }


class DemoRunner:
    def __init__(
        self,
        *,
        api_url: str = DEFAULT_API,
        video_path: Path | None = None,
        vehicle_id: str = DEMO_VEHICLE,
        fps: float = 5.0,
        synthetic_only: bool = False,
        max_frames: int | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.video_path = video_path or Path(os.environ.get("DEMO_VIDEO_PATH", DEFAULT_VIDEO))
        self.vehicle_id = vehicle_id
        self.fps = max(0.5, float(fps))
        self.synthetic_only = synthetic_only
        self.max_frames = max_frames
        self._stop = asyncio.Event()
        self.frames_sent = 0
        self.last_error: str | None = None
        self.started_at: str | None = None
        self.status = "idle"

    def request_stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "frames_sent": self.frames_sent,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "api_url": self.api_url,
            "vehicle_id": self.vehicle_id,
            "video_path": str(self.video_path),
            "synthetic_only": self.synthetic_only or not self.video_path.is_file(),
            "phase": PHASE,
        }

    async def run(self, *, loop: bool = False) -> None:
        self._stop.clear()
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.last_error = None
        use_video = (not self.synthetic_only) and self.video_path.is_file()
        cap = cv2.VideoCapture(str(self.video_path)) if use_video else None
        if use_video and cap is not None and not cap.isOpened():
            logger.warning("Could not open %s — falling back to synthetic frames", self.video_path)
            cap = None
            use_video = False

        logger.info(
            "Demo runner starting (video=%s fps=%.1f api=%s)",
            "yes" if use_video else "synthetic",
            self.fps,
            self.api_url,
        )

        frame_idx = 0
        try:
            async with httpx.AsyncClient(base_url=self.api_url, timeout=60.0) as client:
                while not self._stop.is_set():
                    if self.max_frames is not None and frame_idx >= self.max_frames:
                        break

                    if use_video and cap is not None:
                        ok, frame = cap.read()
                        if not ok:
                            if loop:
                                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                                continue
                            break
                    else:
                        frame = _synthetic_frame(frame_idx)

                    await self._process_frame(client, frame, frame_idx)
                    frame_idx += 1
                    self.frames_sent = frame_idx
                    await asyncio.sleep(1.0 / self.fps)
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            logger.exception("Demo runner failed")
        finally:
            if cap is not None:
                cap.release()
            self.status = "stopped"
            logger.info("Demo runner stopped after %s frames", self.frames_sent)

    async def _process_frame(
        self,
        client: httpx.AsyncClient,
        frame: np.ndarray,
        frame_idx: int,
    ) -> None:
        jpeg = _encode_jpeg(frame)
        telemetry = _telemetry_for_frame(frame_idx)
        driver_state = _driver_state_for_frame(frame_idx)
        road_state = _road_state_for_frame(frame_idx)

        # Driver analysis every frame (pipeline heart)
        try:
            files = {"file": ("frame.jpg", jpeg, "image/jpeg")}
            data = {
                "vehicle_id": self.vehicle_id,
                "session_id": DEMO_SESSION,
                "persist": "false",
            }
            resp = await client.post("/api/v1/driver/analysis", files=files, data=data)
            if resp.status_code == 200:
                body = resp.json()
                logger.info(
                    "frame=%s risk=%s alertness=%s ear=%s",
                    frame_idx,
                    body.get("risk_level"),
                    body.get("alertness_score"),
                    body.get("ear_value"),
                )
            else:
                logger.warning("driver/analysis %s: %s", resp.status_code, resp.text[:200])
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            logger.warning("driver analysis error: %s", exc)

        # Risk + events every few frames to keep dashboard lively
        if frame_idx % 3 == 0:
            try:
                await client.post(
                    f"/api/v1/risk/{self.vehicle_id}/compute",
                    json={
                        "driver_state": driver_state,
                        "road_state": road_state,
                        "telemetry": telemetry,
                        "persist": True,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("risk compute skipped: %s", exc)

        if frame_idx % 5 == 0:
            try:
                await client.post(
                    f"/api/v1/events/{self.vehicle_id}/detect",
                    json={
                        "driver_id": DEMO_DRIVER,
                        "session_id": DEMO_SESSION,
                        "driver_state": driver_state,
                        "road_state": road_state,
                        "telemetry": telemetry,
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("event detect skipped: %s", exc)


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 7B BMW demo runner")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--video", type=Path, default=None)
    parser.add_argument("--vehicle-id", default=DEMO_VEHICLE)
    parser.add_argument("--fps", type=float, default=5.0)
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    runner = DemoRunner(
        api_url=args.api,
        video_path=args.video,
        vehicle_id=args.vehicle_id,
        fps=args.fps,
        synthetic_only=args.synthetic_only,
        max_frames=args.max_frames,
    )
    await runner.run(loop=args.loop)
    return 0 if runner.last_error is None else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
