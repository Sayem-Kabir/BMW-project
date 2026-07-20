"""Phase 4 demo — compute risk + detect events without the UI.

Usage (backend must be on http://localhost:8000 with latest code):

    python scripts/demo_safety_phase4.py

If you see 404 on /compute, restart the backend:

    cd apps/backend
    set PYTHONPATH=F:\\BMW;F:\\BMW\\apps\\backend
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

API = "http://localhost:8000"
VEHICLE_ID = "00000000-0000-4000-8000-000000000003"
DRIVER_ID = "00000000-0000-4000-8000-000000000001"


def _seed_demo_rows() -> None:
    """Ensure org/driver/vehicle exist for event persistence."""
    import subprocess
    from pathlib import Path

    script = Path(__file__).resolve().parent / "seed_safety_demo.py"
    subprocess.run([sys.executable, str(script)], check=False)

DRIVER_STATE = {
    "is_drowsy": True,
    "ear_value": 0.22,
    "phone_detected": False,
    "seatbelt_worn": False,
}

ROAD_STATE = {
    "objects": [
        {
            "class": "car",
            "distance_m": 9.8,
            "relative_speed_kmh": 58.0,
            "track_id": 1,
            "confirmed": True,
        }
    ]
}

TELEMETRY = {
    "speed_kmh": 72.0,
    "latitude": 48.1351,
    "longitude": 11.5820,
}


def _post(path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{API}{path}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _check_backend() -> None:
    try:
        health = _get("/health")
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"Backend not reachable at {API}. Start it first.\n  Error: {exc}"
        ) from exc
    print(f"Backend OK ({health.get('status', '?')})")


def _check_risk_routes() -> None:
    try:
        openapi = _get("/openapi.json")
    except Exception:
        return
    paths = openapi.get("paths", {})
    compute = "/api/v1/risk/{vehicle_id}/compute"
    if compute not in paths:
        raise SystemExit(
            "Risk compute route is missing on the running backend (404 likely).\n"
            "You are probably running an OLD uvicorn process.\n\n"
            "Restart backend from repo root:\n"
            "  $env:PYTHONPATH='F:\\BMW;F:\\BMW\\apps\\backend'\n"
            "  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload\n"
        )


def main() -> int:
    print("=" * 68)
    print("Phase 4 demo — risk scoring + safety event detection")
    print("=" * 68)

    _check_backend()
    _check_risk_routes()
    _seed_demo_rows()

    print("\n--- 1) Compute composite risk (4A/4B/4F) ---")
    try:
        risk = _post(
            f"/api/v1/risk/{VEHICLE_ID}/compute",
            {
                "driver_state": DRIVER_STATE,
                "road_state": {},
                "telemetry": TELEMETRY,
                "publish": True,
                "persist": True,
            },
        )
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode()}")
        return 1

    print(f"  score      : {risk.get('score')} / 100")
    print(f"  level      : {risk.get('level')}")
    print(f"  base_score : {risk.get('base_score')} ({risk.get('base_level')})")
    print("  reasons    :")
    for reason in risk.get("reasons") or []:
        print(f"    - {reason}")

    print("\n--- 2) Detect safety events (4D/4E) — near collision scenario ---")
    try:
        events = _post(
            f"/api/v1/events/{VEHICLE_ID}/detect",
            {
                "driver_id": DRIVER_ID,
                "driver_state": DRIVER_STATE,
                "road_state": ROAD_STATE,
                "telemetry": {"speed_kmh": 58.0},
                "risk_score": risk.get("score"),
                "attach_clips": False,
            },
        )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        print(f"HTTP {exc.code}: {body}")
        if exc.code in {500, 503} and "foreign key" in body.lower():
            print(
                "\nTip: seed vehicle + driver in Postgres (see README / safety UI docs)."
            )
        return 1

    print(f"  detected   : {events.get('detected')}")
    print(f"  persisted  : {events.get('persisted')}")
    for item in events.get("events") or []:
        print(f"\n  Event: {item.get('event_type')} ({item.get('severity')})")
        print(f"    {item.get('xai_explanation', '')}")

    print("\n--- 3) Current cached risk (4C) ---")
    try:
        current = _get(f"/api/v1/risk/current/{VEHICLE_ID}")
        print(f"  score: {current.get('score')}  level: {current.get('level')}")
        if current.get("message"):
            print(f"  note: {current.get('message')}")
    except urllib.error.HTTPError as exc:
        print(f"  (cache read failed: {exc.code})")

    print("\nDone. Open http://localhost:3000/safety for the live UI.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
