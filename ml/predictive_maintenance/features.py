"""Phase 3A — feature engineering for local maintenance datasets."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.predictive_maintenance.config import (
    LOGISTICS_TIRE_MODEL_FEATURES,
    LOGISTICS_TIRE_TARGET,
    LOGISTICS_TIRE_TARGET_RAW,
)


def engineer_eviot_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive EVIoT ratios used by brake / battery notebooks."""
    out = df.copy()

    # Battery stress proxies
    if {"Battery_Voltage", "Battery_Current"}.issubset(out.columns):
        out["battery_power_kw"] = (
            out["Battery_Voltage"].astype(float)
            * out["Battery_Current"].astype(float)
            / 1000.0
        )
    if {"Battery_Temperature", "Ambient_Temperature"}.issubset(out.columns):
        out["battery_temp_delta"] = (
            out["Battery_Temperature"].astype(float)
            - out["Ambient_Temperature"].astype(float)
        )
    if {"SoH", "Charge_Cycles"}.issubset(out.columns):
        out["soh_per_100_cycles"] = (
            out["SoH"].astype(float)
            / (out["Charge_Cycles"].astype(float) / 100.0).clip(lower=1e-3)
        )

    # Brake / usage proxies
    if {"Brake_Pressure", "Driving_Speed"}.issubset(out.columns):
        out["brake_energy_proxy"] = (
            out["Brake_Pressure"].astype(float)
            * out["Driving_Speed"].astype(float)
        )
    if {"Distance_Traveled", "Idle_Time"}.issubset(out.columns):
        out["active_distance_ratio"] = out["Distance_Traveled"].astype(float) / (
            out["Distance_Traveled"].astype(float)
            + out["Idle_Time"].astype(float)
            + 1e-3
        )

    # Convenient percent scale for battery SoH when notebooks want 0–100
    if "SoH" in out.columns and "SoH_pct" not in out.columns:
        out["SoH_pct"] = out["SoH"].astype(float) * 100.0

    return out


def engineer_battery_cycle_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cycle-level battery aging features for 3D."""
    out = df.copy()
    if {"Capacity_Ah", "SOH_pct"}.issubset(out.columns):
        # Nominal capacity implied by first-cycle SoH if available
        first = out.iloc[0]
        if float(first["SOH_pct"]) > 0:
            out["capacity_nominal_ah"] = float(first["Capacity_Ah"]) / (
                float(first["SOH_pct"]) / 100.0
            )
        out["capacity_fade_ah"] = (
            out["capacity_nominal_ah"] - out["Capacity_Ah"].astype(float)
            if "capacity_nominal_ah" in out.columns
            else np.nan
        )
    if {"Voltage_V", "Current_A"}.issubset(out.columns):
        out["cycle_power_w"] = (
            out["Voltage_V"].astype(float) * out["Current_A"].astype(float)
        )
    if "Cycle" in out.columns:
        out["log_cycle"] = np.log1p(out["Cycle"].astype(float))
    return out


def engineer_nev_fault_features(df: pd.DataFrame) -> pd.DataFrame:
    """NEV fault set is already scaled to [0, 1]; add light interaction terms."""
    out = df.copy()
    voltage = "Voltage (V)"
    current = "Current (A)"
    temp = "Temperature (°C)"
    vib = "Vibration (g)"
    if {voltage, current}.issubset(out.columns):
        out["electrical_load"] = out[voltage].astype(float) * out[current].astype(float)
    if {temp, vib}.issubset(out.columns):
        out["thermal_vibration"] = out[temp].astype(float) * out[vib].astype(float)
    if "Fault Label" in out.columns:
        out["Fault Label"] = (
            pd.to_numeric(out["Fault Label"], errors="coerce").round().astype("Int64")
        )
    return out


def _minmax_to_pct(series: pd.Series, *, invert: bool = False) -> pd.Series:
    values = series.astype(float)
    lo = float(values.min())
    hi = float(values.max())
    if hi <= lo:
        return pd.Series(np.zeros(len(values)), index=values.index)
    scaled = (values - lo) / (hi - lo)
    if invert:
        scaled = 1.0 - scaled
    return (scaled * 100.0).clip(0.0, 100.0)


def engineer_logistics_tire_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive Tire_Wear_pct from TPI for Module 3E.

    Higher TPI correlates with lower tire pressure and higher vibration /
    days-since-service, so we map TPI min→max onto wear 0→100%.
    """
    out = df.copy()
    if LOGISTICS_TIRE_TARGET_RAW not in out.columns:
        raise ValueError(f"Expected column {LOGISTICS_TIRE_TARGET_RAW} for tire wear")

    out[LOGISTICS_TIRE_TARGET] = _minmax_to_pct(out[LOGISTICS_TIRE_TARGET_RAW])

    if "Tire_Pressure" in out.columns:
        # Deviation from fleet median pressure (under-inflation → wear risk)
        median_psi = float(out["Tire_Pressure"].median())
        out["tire_pressure_deviation"] = (
            out["Tire_Pressure"].astype(float) - median_psi
        ).abs()

    if {"Actual_Load", "Load_Capacity"}.issubset(out.columns):
        out["load_ratio"] = (
            out["Actual_Load"].astype(float)
            / out["Load_Capacity"].astype(float).clip(lower=1e-3)
        )

    # Encode categoricals used as tire features. Factorization is sorted so the
    # same labels receive stable IDs in local training and inference adapters.
    for col in ("Road_Conditions", "Weather_Conditions"):
        if col not in out.columns:
            continue
        codes, _ = pd.factorize(out[col].astype(str), sort=True)
        code_name = f"{col}_code"
        out[code_name] = codes.astype(np.int32)

    if set(LOGISTICS_TIRE_MODEL_FEATURES).issubset(out.columns):
        out.attrs["tire_feature_set"] = list(LOGISTICS_TIRE_MODEL_FEATURES)
    return out
