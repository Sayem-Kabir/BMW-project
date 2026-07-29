"""One-shot Phase 10 live demos against ASGI app (no DB login required)."""
from __future__ import annotations

import asyncio
import json

from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import _buckets, check_rate_limit
from app.main import app


async def main() -> None:
    results: dict = {}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
        results["health"] = {"status": r.status_code, "body": r.json()}

        r = await c.get("/api/v1/admin/health")
        results["error_envelope"] = {"status": r.status_code, "body": r.json()}

        r = await c.get("/metrics")
        lines = [ln for ln in r.text.splitlines() if ln and not ln.startswith("#")]
        interesting = [
            ln
            for ln in lines
            if any(k in ln for k in ("http_request", "bmw_", "process_resident"))
        ][:14]
        results["metrics"] = {
            "status": r.status_code,
            "sample_lines": interesting,
            "line_count": len(lines),
        }

        r = await c.post(
            "/api/v1/models/driver_monitor/promote",
            json={"target_stage": "production", "eval_metric_value": 0.95},
        )
        results["models_promote"] = {"status": r.status_code, "body": r.json()}

        r = await c.post(
            "/api/v1/driver/analysis",
            files={"file": ("x.txt", b"not-an-image", "text/plain")},
        )
        results["upload_reject"] = {"status": r.status_code, "body": r.json()}

    # Rate limit unit path (same limiter login uses) — avoids DB schema drift
    _buckets.clear()
    statuses = []
    for i in range(6):
        try:
            check_rate_limit("demo-ip", limit=5, window_sec=60)
            statuses.append({"attempt": i + 1, "status": 200, "note": "allowed"})
        except Exception as exc:  # noqa: BLE001
            statuses.append(
                {
                    "attempt": i + 1,
                    "status": getattr(exc, "status_code", 500),
                    "detail": getattr(exc, "detail", str(exc)),
                }
            )
    results["login_rate_limit"] = statuses
    _buckets.clear()

    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
