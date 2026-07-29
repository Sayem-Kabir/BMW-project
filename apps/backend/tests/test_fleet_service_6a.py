"""Module 6A fleet service unit tests (no DB required)."""

from __future__ import annotations

from app.services.fleet_service import (
    DEMO_ORG_ID,
    PHASE,
    demo_location,
    status_from_risk_and_health,
)


def test_phase_and_demo_org() -> None:
    assert PHASE == "6A"
    assert str(DEMO_ORG_ID).endswith("0010")


def test_demo_location_known_vehicle() -> None:
    loc = demo_location("00000000-0000-4000-8000-000000000003")
    assert loc is not None
    assert "latitude" in loc and "longitude" in loc


def test_status_from_risk_and_health() -> None:
    assert status_from_risk_and_health(risk_level="LOW", worst_health=0.9) == "operational"
    assert status_from_risk_and_health(risk_level="MEDIUM", worst_health=0.8) == "maintenance"
    assert status_from_risk_and_health(risk_level="HIGH", worst_health=0.9) == "critical"
    assert status_from_risk_and_health(risk_level="LOW", worst_health=0.2) == "critical"
