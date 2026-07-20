"""Module 5F context builder tests."""

from __future__ import annotations

from ml.assistant.context import (
    demo_maintenance_snapshot,
    format_maintenance_context,
    format_telemetry_context,
    should_inject_maintenance,
    should_inject_telemetry,
)


def test_format_telemetry_and_maintenance() -> None:
    telem = format_telemetry_context(
        {"speed_kmh": 40, "tire_rl": 22, "tire_fl": 32, "tire_fr": 34, "tire_rr": 33, "battery_soc": 70}
    )
    assert "RL=22" in telem

    maint = format_maintenance_context(demo_maintenance_snapshot("v1"))
    assert "tire" in maint
    assert "health=0.62" in maint


def test_injection_rules() -> None:
    assert should_inject_telemetry("vehicle_warning", "rag_with_telemetry")
    assert should_inject_maintenance("maintenance_question", "rag_only")
    assert not should_inject_telemetry("general_question", "direct_response")
