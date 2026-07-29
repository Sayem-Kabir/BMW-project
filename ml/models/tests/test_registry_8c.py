"""Module 8C registry unit test (no network downloads)."""

from __future__ import annotations

from ml.models.download_registry import load_registry, status_report


def test_registry_loads():
    reg = load_registry()
    assert reg["phase"] == "8C"
    assert any(e["id"] == "driver_monitor" for e in reg["entries"])


def test_status_report_shape():
    rows = status_report()
    assert isinstance(rows, list)
    assert all("present" in r and "filename" in r for r in rows)
