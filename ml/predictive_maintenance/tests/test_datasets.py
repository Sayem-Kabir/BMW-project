"""Integration tests for Module 3A loaders (skip if CSVs missing)."""

from __future__ import annotations

import pytest

from ml.predictive_maintenance.config import datasets_ready
from ml.predictive_maintenance.data_generator import prepare_all_module_frames
from ml.predictive_maintenance.datasets import (
    dataset_inventory,
    prepare_battery_cycle_frame,
    prepare_brake_frame,
    prepare_engine_fault_frame,
    prepare_tire_wear_frame,
)


pytestmark = pytest.mark.skipif(
    not datasets_ready(),
    reason="Local predictive-maintenance CSVs not present under data/",
)


def test_dataset_inventory_all_present():
    inv = dataset_inventory()
    assert inv["exists"].all()


def test_prepare_all_module_frames_shapes():
    frames = prepare_all_module_frames()
    assert set(frames) >= {
        "3B_engine_fault",
        "3C_brake_condition",
        "3D_battery_soh",
        "3E_tire_wear",
    }
    for frame in frames.values():
        assert len(frame.frame) > 0
        assert len(frame.features) >= 3
        assert frame.target in frame.frame.columns


def test_brake_and_fault_targets():
    brake = prepare_brake_frame()
    assert brake.target == "Brake_Condition"
    assert set(brake.y.unique()) <= {0, 1, 2}

    fault = prepare_engine_fault_frame()
    assert set(fault.y.unique()) <= {0, 1, 2, 3}


def test_tire_wear_pct_range():
    tire = prepare_tire_wear_frame()
    assert tire.target == "Tire_Wear_pct"
    assert tire.y.min() >= 0.0
    assert tire.y.max() <= 100.0


def test_battery_cycle_soh_target():
    batt = prepare_battery_cycle_frame()
    assert batt.target == "SOH_pct"
    assert "Capacity_Ah" not in batt.features
    assert batt.y.min() > 50.0
