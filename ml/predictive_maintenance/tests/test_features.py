"""Unit tests for Module 3A feature engineering (no large CSV required)."""

from __future__ import annotations

import pandas as pd

from ml.predictive_maintenance.features import (
    engineer_battery_cycle_features,
    engineer_eviot_features,
    engineer_logistics_tire_features,
    engineer_nev_fault_features,
)


def test_eviot_feature_engineering_adds_proxies():
    df = pd.DataFrame(
        {
            "Battery_Voltage": [400.0, 380.0],
            "Battery_Current": [-10.0, 20.0],
            "Battery_Temperature": [35.0, 40.0],
            "Ambient_Temperature": [20.0, 22.0],
            "SoH": [0.9, 0.8],
            "Charge_Cycles": [100.0, 200.0],
            "Brake_Pressure": [40.0, 50.0],
            "Driving_Speed": [60.0, 80.0],
            "Distance_Traveled": [10.0, 5.0],
            "Idle_Time": [1.0, 2.0],
        }
    )
    out = engineer_eviot_features(df)
    assert "battery_power_kw" in out.columns
    assert "battery_temp_delta" in out.columns
    assert "SoH_pct" in out.columns
    assert out["SoH_pct"].iloc[0] == 90.0


def test_battery_cycle_features_add_log_cycle():
    df = pd.DataFrame(
        {
            "Cycle": [1, 2, 3],
            "Voltage_V": [4.2, 4.1, 4.0],
            "Current_A": [1.5, 1.5, 1.5],
            "Temperature_C": [25.0, 26.0, 27.0],
            "Capacity_Ah": [2.0, 1.9, 1.8],
            "Time_s": [5000.0, 4800.0, 4600.0],
            "SOH_pct": [100.0, 95.0, 90.0],
        }
    )
    out = engineer_battery_cycle_features(df)
    assert "log_cycle" in out.columns
    assert "cycle_power_w" in out.columns


def test_nev_fault_features_cast_label():
    df = pd.DataFrame(
        {
            "Voltage (V)": [0.5, 0.6],
            "Current (A)": [0.4, 0.3],
            "Motor Speed (RPM)": [0.2, 0.1],
            "Temperature (°C)": [0.3, 0.4],
            "Vibration (g)": [0.1, 0.2],
            "Ambient Temp (°C)": [0.5, 0.5],
            "Humidity (%)": [0.5, 0.4],
            "Fault Label": [0.0, 1.0],
        }
    )
    out = engineer_nev_fault_features(df)
    assert "electrical_load" in out.columns
    assert out["Fault Label"].dtype.kind in "iu"


def test_logistics_tire_derives_wear_pct_and_feature_set():
    df = pd.DataFrame(
        {
            "TPI": [2.0, 3.0, 4.0, 5.0],
            "Tire_Pressure": [35.0, 32.0, 28.0, 24.0],
            "Vibration_Levels": [0.5, 1.0, 2.0, 3.0],
            "Actual_Load": [5000.0, 6000.0, 7000.0, 8000.0],
            "Load_Capacity": [10000.0, 10000.0, 10000.0, 10000.0],
            "Usage_Hours": [1000.0, 2000.0, 3000.0, 4000.0],
            "Days_Since_Last_Maintenance": [30, 60, 90, 120],
            "Road_Conditions": ["Smooth", "Rough", "Smooth", "Rough"],
            "Weather_Conditions": ["Clear", "Rainy", "Clear", "Hot"],
        }
    )
    out = engineer_logistics_tire_features(df)
    assert "Tire_Wear_pct" in out.columns
    assert out["Tire_Wear_pct"].min() == 0.0
    assert out["Tire_Wear_pct"].max() == 100.0
    assert "tire_feature_set" in out.attrs
    assert "Tire_Pressure" in out.attrs["tire_feature_set"]
    assert "Road_Conditions_code" in out.attrs["tire_feature_set"]
