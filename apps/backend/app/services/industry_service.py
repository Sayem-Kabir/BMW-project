"""Spec Section 19 — industry-level feature services (OTA, insurance, twin, chaos…)."""

from __future__ import annotations

import logging
import math
import secrets
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score import DriverScore
from app.models.telemetry import VehicleTelemetry
from app.models.vehicle import Vehicle

logger = logging.getLogger(__name__)
PHASE = "19"

_CANARY: dict[str, Any] = {
    "active": False,
    "model_name": None,
    "version": None,
    "fleet_percent": 0.0,
    "error_rate": 0.0,
    "started_at": None,
}


def ota_status() -> dict[str, Any]:
    return {**_CANARY, "phase": PHASE}


def start_canary(
    *,
    model_name: str,
    version: str,
    fleet_percent: float,
    started_by: str,
) -> dict[str, Any]:
    _CANARY.update(
        {
            "active": True,
            "model_name": model_name,
            "version": version,
            "fleet_percent": fleet_percent,
            "error_rate": 0.0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "started_by": started_by,
        }
    )
    return ota_status()


def rollback_canary(*, rolled_back_by: str) -> dict[str, Any]:
    _CANARY.update(
        {
            "active": False,
            "fleet_percent": 0.0,
            "rolled_back_at": datetime.now(timezone.utc).isoformat(),
            "rolled_back_by": rolled_back_by,
        }
    )
    return ota_status()


def edge_cloud_route(risk_score: float) -> dict[str, Any]:
    """Lightweight on-device path unless risk exceeds threshold → escalate to cloud."""
    threshold = 65.0
    if risk_score >= threshold:
        return {
            "route": "cloud",
            "reason": "risk_above_threshold",
            "risk_score": risk_score,
            "threshold": threshold,
            "actions": ["llm_xai", "full_rag"],
            "phase": PHASE,
        }
    return {
        "route": "edge",
        "reason": "risk_within_budget",
        "risk_score": risk_score,
        "threshold": threshold,
        "actions": ["onnx_inference", "local_rules"],
        "phase": PHASE,
    }


def replay_drive(vehicle_id: str, frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Re-run historical frames through risk overrides (debug / regression)."""
    from ml.risk_engine.rules import compute_risk_with_overrides

    decisions = []
    for i, frame in enumerate(frames[:200]):
        decision = compute_risk_with_overrides(
            vehicle_id,
            frame.get("driver") or {},
            frame.get("road") or {},
            frame.get("telemetry") or {},
        )
        decisions.append(
            {
                "i": i,
                "score": decision.score,
                "level": decision.level,
                "method": decision.method,
                "overrides": [o.rule_id for o in decision.overrides],
            }
        )
    levels = [d["level"] for d in decisions]
    return {
        "vehicle_id": vehicle_id,
        "frames": len(decisions),
        "max_score": max((d["score"] for d in decisions), default=0),
        "critical_count": sum(1 for lv in levels if lv == "CRITICAL"),
        "decisions": decisions[-50:],
        "phase": PHASE,
    }


async def insurance_premium(session: AsyncSession, driver_id: UUID) -> dict[str, Any]:
    rows = list(
        (
            await session.execute(
                select(DriverScore)
                .where(DriverScore.driver_id == driver_id)
                .order_by(DriverScore.date.desc())
                .limit(30)
            )
        ).scalars().all()
    )
    if not rows:
        base = 120.0
        score = 80.0
    else:
        score = sum(r.safety_score for r in rows) / len(rows)
        base = 120.0
    # Higher safety → lower premium multiplier
    multiplier = max(0.55, min(1.45, 1.4 - (score / 100.0) * 0.7))
    monthly = round(base * multiplier, 2)
    return {
        "driver_id": str(driver_id),
        "avg_safety_score": round(score, 1),
        "base_premium_usd": base,
        "multiplier": round(multiplier, 3),
        "monthly_premium_usd": monthly,
        "product": "usage_based_insurance_demo",
        "phase": PHASE,
    }


async def carbon_efficiency(session: AsyncSession, vehicle_id: UUID) -> dict[str, Any]:
    rows = list(
        (
            await session.execute(
                select(VehicleTelemetry)
                .where(VehicleTelemetry.vehicle_id == vehicle_id)
                .order_by(VehicleTelemetry.time.desc())
                .limit(100)
            )
        ).scalars().all()
    )
    if not rows:
        return {
            "vehicle_id": str(vehicle_id),
            "efficiency_score": 72.0,
            "source": "demo",
            "kwh_per_100km_est": 18.5,
            "co2_g_per_km_est": 0.0,
            "phase": PHASE,
            "message": "No telemetry — demo EV efficiency",
        }
    speeds = [float(r.speed_kmh or 0) for r in rows]
    socs = [float(r.battery_soc_pct or 0) for r in rows if r.battery_soc_pct is not None]
    avg_speed = sum(speeds) / max(len(speeds), 1)
    # Rough efficiency: moderate speed + high SOC health → better score
    score = 100.0 - abs(avg_speed - 55.0) * 0.4
    if socs:
        score += (sum(socs) / len(socs) - 50) * 0.1
    score = max(0.0, min(100.0, score))
    kwh = round(14.0 + abs(avg_speed - 50) * 0.08, 2)
    return {
        "vehicle_id": str(vehicle_id),
        "efficiency_score": round(score, 1),
        "avg_speed_kmh": round(avg_speed, 1),
        "kwh_per_100km_est": kwh,
        "co2_g_per_km_est": 0.0,
        "source": "telemetry",
        "phase": PHASE,
    }


def stripe_checkout_session(*, org_id: str | None, tier: str, seats: int) -> dict[str, Any]:
    """Stripe Checkout — real test-mode when STRIPE_SECRET_KEY set, else demo stub."""
    from app.core.config import settings

    prices = {"starter": 2900, "fleet_pro": 9900, "enterprise": 29900}  # cents
    unit_cents = prices.get(tier, 9900)
    if settings.stripe_secret_key:
        try:
            import stripe

            stripe.api_key = settings.stripe_secret_key
            session = stripe.checkout.Session.create(
                mode="subscription" if False else "payment",
                success_url=settings.stripe_success_url,
                cancel_url=settings.stripe_cancel_url,
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"BMW AI {tier}",
                                "metadata": {"org_id": org_id or "", "seats": str(seats)},
                            },
                            "unit_amount": unit_cents * seats,
                        },
                        "quantity": 1,
                    }
                ],
                metadata={"org_id": org_id or "", "tier": tier, "seats": str(seats)},
            )
            return {
                "id": session.id,
                "object": "checkout.session",
                "status": session.status,
                "url": session.url,
                "org_id": org_id,
                "tier": tier,
                "seats": seats,
                "amount_total_usd": (unit_cents * seats) / 100.0,
                "currency": "usd",
                "livemode": bool(session.livemode),
                "mode": "stripe_sdk",
                "phase": PHASE,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Stripe SDK checkout failed (%s) — stub fallback", exc)

    session_id = f"cs_test_{secrets.token_hex(12)}"
    return {
        "id": session_id,
        "object": "checkout.session",
        "mode": "subscription",
        "status": "open",
        "org_id": org_id,
        "tier": tier,
        "seats": seats,
        "amount_total_usd": (unit_cents * seats) / 100.0,
        "currency": "usd",
        "url": f"https://checkout.stripe.com/c/pay/{session_id}#demo",
        "livemode": False,
        "mode": "stub",
        "phase": PHASE,
    }


async def digital_twin_state(session: AsyncSession, vehicle_id: UUID) -> dict[str, Any]:
    vehicle = (
        await session.execute(select(Vehicle).where(Vehicle.id == vehicle_id))
    ).scalar_one_or_none()
    row = (
        await session.execute(
            select(VehicleTelemetry)
            .where(VehicleTelemetry.vehicle_id == vehicle_id)
            .order_by(VehicleTelemetry.time.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    telem = {
        "speed_kmh": float(row.speed_kmh) if row and row.speed_kmh is not None else 0.0,
        "battery_soc_pct": float(row.battery_soc_pct)
        if row and row.battery_soc_pct is not None
        else 64.0,
        "latitude": float(row.latitude) if row and row.latitude is not None else 48.1351,
        "longitude": float(row.longitude) if row and row.longitude is not None else 11.5820,
        "heading_deg": 90.0,
    }
    # Simple 2D twin pose
    return {
        "vehicle_id": str(vehicle_id),
        "name": vehicle.name if vehicle else "Unknown",
        "model": vehicle.model if vehicle else "BMW",
        "pose": {
            "x": telem["longitude"],
            "y": telem["latitude"],
            "heading_deg": telem["heading_deg"],
        },
        "telemetry": telem,
        "mesh": "bmw_i4_bbox_v1",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "phase": PHASE,
    }


async def chaos_probe(target: str) -> dict[str, Any]:
    results: dict[str, Any] = {"target": target, "phase": PHASE, "probes": {}}
    if target in {"redis", "both"}:
        try:
            from app.core.redis import get_redis

            redis = await get_redis()
            pong = await redis.ping()
            results["probes"]["redis"] = {"ok": bool(pong), "degraded": False}
        except Exception as exc:  # noqa: BLE001
            results["probes"]["redis"] = {
                "ok": False,
                "degraded": True,
                "error": str(exc),
                "fail_safe": "continue_without_cache",
            }
    if target in {"postgres", "both"}:
        try:
            from sqlalchemy import text

            from app.core.database import async_session_maker

            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
            results["probes"]["postgres"] = {"ok": True, "degraded": False}
        except Exception as exc:  # noqa: BLE001
            results["probes"]["postgres"] = {
                "ok": False,
                "degraded": True,
                "error": str(exc),
                "fail_safe": "serve_cached_or_demo",
            }
    results["graceful"] = True
    return results


def sensor_fusion_demo() -> dict[str, Any]:
    """1D Kalman fuse of camera distance + simulated radar."""
    # Prior
    x, p = 25.0, 4.0
    measurements = [
        ("camera", 24.5, 2.0),
        ("radar", 25.2, 0.8),
        ("camera", 23.8, 2.2),
        ("lidar", 24.9, 0.5),
    ]
    steps = []
    for sensor, z, r in measurements:
        # Predict (constant)
        # Update
        k = p / (p + r)
        x = x + k * (z - x)
        p = (1 - k) * p
        steps.append(
            {
                "sensor": sensor,
                "z": z,
                "estimate_m": round(x, 3),
                "variance": round(p, 4),
            }
        )
    return {
        "method": "kalman_1d",
        "final_distance_m": round(x, 3),
        "steps": steps,
        "phase": PHASE,
    }


def federated_avg_round() -> dict[str, Any]:
    """FedAvg simulation across 3 vehicle clients (toy weights)."""
    clients = [
        [0.10, 0.20, 0.30],
        [0.12, 0.18, 0.28],
        [0.11, 0.22, 0.31],
    ]
    n = len(clients[0])
    avg = [sum(c[i] for c in clients) / len(clients) for i in range(n)]
    return {
        "algorithm": "FedAvg",
        "clients": len(clients),
        "global_weights": [round(v, 4) for v in avg],
        "delta_l2": round(
            math.sqrt(sum((clients[0][i] - avg[i]) ** 2 for i in range(n))), 5
        ),
        "phase": PHASE,
        "timestamp": time.time(),
    }
