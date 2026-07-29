"""Module 7C — demo mode control via subprocess (avoids in-process HTTP deadlock)."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PHASE = "7C"
ROOT = Path(__file__).resolve().parents[3]
DEMO_VEHICLE = "00000000-0000-4000-8000-000000000003"

_lock = asyncio.Lock()
_proc: asyncio.subprocess.Process | None = None
_meta: dict[str, Any] = {
    "status": "idle",
    "frames_sent": 0,
    "last_error": None,
    "started_at": None,
    "vehicle_id": DEMO_VEHICLE,
}


def _api_base() -> str:
    return os.environ.get("DEMO_API_URL", "http://127.0.0.1:8000").rstrip("/")


def status_demo() -> dict[str, Any]:
    running = _proc is not None and _proc.returncode is None
    if _proc is not None and _proc.returncode is not None and _meta.get("status") == "running":
        _meta["status"] = "stopped"
    return {
        "running": running,
        "phase": PHASE,
        "status": "running" if running else _meta.get("status", "idle"),
        "frames_sent": _meta.get("frames_sent", 0),
        "last_error": _meta.get("last_error"),
        "started_at": _meta.get("started_at"),
        "vehicle_id": _meta.get("vehicle_id", DEMO_VEHICLE),
        "api_url": _api_base(),
        "pid": _proc.pid if running and _proc is not None else None,
    }


async def start_demo(
    *,
    vehicle_id: str = DEMO_VEHICLE,
    fps: float = 4.0,
    synthetic_only: bool = True,
    loop: bool = True,
    max_frames: int | None = None,
) -> dict[str, Any]:
    global _proc, _meta
    async with _lock:
        if _proc is not None and _proc.returncode is None:
            return {"ok": True, "already_running": True, **status_demo()}

        from datetime import datetime, timezone

        cmd = [
            sys.executable,
            "-m",
            "ml.demo.demo_runner",
            "--api",
            _api_base(),
            "--vehicle-id",
            vehicle_id,
            "--fps",
            str(fps),
        ]
        if synthetic_only:
            cmd.append("--synthetic-only")
        if loop and max_frames is None:
            cmd.append("--loop")
        if max_frames is not None:
            cmd.extend(["--max-frames", str(max_frames)])

        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT), str(ROOT / "apps" / "backend"), env.get("PYTHONPATH", "")]
        )

        _proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(ROOT),
            env=env,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _meta = {
            "status": "running",
            "frames_sent": 0,
            "last_error": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "vehicle_id": vehicle_id,
        }
        logger.info("Demo subprocess started pid=%s cmd=%s", _proc.pid, " ".join(cmd))
        return {"ok": True, "already_running": False, **status_demo()}


async def stop_demo() -> dict[str, Any]:
    global _proc, _meta
    async with _lock:
        if _proc is not None and _proc.returncode is None:
            _proc.terminate()
            try:
                await asyncio.wait_for(_proc.wait(), timeout=8.0)
            except asyncio.TimeoutError:
                _proc.kill()
                await _proc.wait()
            # Discard noisy stderr from a clean stop; keep only if process crashed.
            err = None
            if _proc.returncode not in (0, None, -15, 15, 1) and _proc.stderr is not None:
                raw = await _proc.stderr.read()
                if raw:
                    err = raw.decode("utf-8", errors="replace")[-500:]
            _meta["status"] = "stopped"
            _meta["last_error"] = err
        elif _proc is not None and _proc.returncode is not None:
            _meta["status"] = "stopped"
        snap = status_demo()
        _proc = None
        return {"ok": True, **snap}
