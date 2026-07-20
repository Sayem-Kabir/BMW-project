"""Module 3 demo — run the maintenance pipeline on example vehicles.

Usage (from repo root F:/BMW):

    python -m ml.predictive_maintenance.demo

It runs two ready-made vehicles (one healthy, one degraded) through the same
3G pipeline the API uses, then prints a plain-language report so you can see
what each model decided and why.
"""

from __future__ import annotations

from typing import Any, Mapping

from ml.predictive_maintenance import MaintenancePipeline

# ── Example telemetry ───────────────────────────────────────────────
# Each vehicle is a nested payload: one feature map per component. These are
# exactly the fields each trained model expects (see config.py contracts).

HEALTHY_VEHICLE: dict[str, dict[str, float]] = {
    "engine": {
        "Voltage (V)": 400.0,
        "Current (A)": 55.0,
        "Motor Speed (RPM)": 3200.0,
        "Temperature (\u00b0C)": 42.0,
        "Vibration (g)": 0.35,
        "Ambient Temp (\u00b0C)": 24.0,
        "Humidity (%)": 45.0,
    },
    "brake": {
        "Usage_Hours": 1200.0,
        "Actual_Load": 3200.0,
        "Engine_Temperature": 82.0,
        "Tire_Pressure": 34.0,
        "Fuel_Consumption": 8.5,
        "Battery_Status": 92.0,
        "Vibration_Levels": 1.2,
        "Oil_Quality": 88.0,
        "Failure_History": 0.0,
        "Anomalies_Detected": 0.0,
        "Diagnostic_Trouble_Code_Count": 0.0,
        "CAN_Message_Rate_Hz": 500.0,
        "Sensor_Packet_Loss_Rate": 0.5,
        "Days_Since_Last_Maintenance": 30.0,
    },
    # Battery values sit in the low-cycle / high-voltage healthy region the
    # cycle-aging model was trained on (see feature_ranges in the bundle).
    "battery": {
        "Cycle": 60.0,
        "Voltage_V": 4.19,
        "Current_A": 1.5,
        "Temperature_C": 25.0,
        "Time_s": 5300.0,
    },
    "tire": {
        "Tire_Pressure": 34.0,
        "Vibration_Levels": 1.2,
        "Actual_Load": 3200.0,
        "Usage_Hours": 1200.0,
        "Days_Since_Last_Maintenance": 30.0,
        "Road_Conditions_code": 0.0,
        "Weather_Conditions_code": 0.0,
        "tire_pressure_deviation": 0.5,
        "load_ratio": 0.55,
    },
}

DEGRADED_VEHICLE: dict[str, dict[str, float]] = {
    "engine": {
        "Voltage (V)": 355.0,
        "Current (A)": 140.0,
        "Motor Speed (RPM)": 5200.0,
        "Temperature (\u00b0C)": 96.0,
        "Vibration (g)": 3.8,
        "Ambient Temp (\u00b0C)": 33.0,
        "Humidity (%)": 78.0,
    },
    "brake": {
        "Usage_Hours": 9800.0,
        "Actual_Load": 5600.0,
        "Engine_Temperature": 112.0,
        "Tire_Pressure": 26.0,
        "Fuel_Consumption": 15.5,
        "Battery_Status": 58.0,
        "Vibration_Levels": 6.4,
        "Oil_Quality": 34.0,
        "Failure_History": 3.0,
        "Anomalies_Detected": 4.0,
        "Diagnostic_Trouble_Code_Count": 5.0,
        "CAN_Message_Rate_Hz": 220.0,
        "Sensor_Packet_Loss_Rate": 7.5,
        "Days_Since_Last_Maintenance": 410.0,
    },
    # Aged battery: high cycle count, sagging voltage, short discharge time.
    "battery": {
        "Cycle": 1450.0,
        "Voltage_V": 3.97,
        "Current_A": 1.66,
        "Temperature_C": 33.0,
        "Time_s": 3600.0,
    },
    "tire": {
        "Tire_Pressure": 24.0,
        "Vibration_Levels": 6.4,
        "Actual_Load": 5600.0,
        "Usage_Hours": 9800.0,
        "Days_Since_Last_Maintenance": 410.0,
        "Road_Conditions_code": 2.0,
        "Weather_Conditions_code": 2.0,
        "tire_pressure_deviation": 6.0,
        "load_ratio": 0.95,
    },
}

_SEVERITY_ICON = {
    "normal": "[ OK ]",
    "warning": "[WARN]",
    "critical": "[CRIT]",
    "unknown": "[ ?? ]",
}


def _print_component(name: str, prediction: Any) -> None:
    if prediction.status != "ok":
        print(f"  {name:<8} UNAVAILABLE — {prediction.error}")
        if prediction.missing_features:
            print(f"           missing: {', '.join(prediction.missing_features)}")
        return

    icon = _SEVERITY_ICON.get(prediction.severity, "[ ?? ]")
    health = (
        f"{round(prediction.health_score * 100)}%"
        if prediction.health_score is not None
        else "n/a"
    )
    needs = "YES" if prediction.maintenance_required else "no"
    print(
        f"  {name:<8} {icon} health={health:<5} "
        f"maintenance={needs:<3} severity={prediction.severity}"
    )

    result = prediction.result or {}
    detail_keys = (
        "class_name",
        "condition",
        "soh_pct",
        "wear_pct",
        "confidence",
    )
    details = {k: result[k] for k in detail_keys if k in result}
    if details:
        rendered = ", ".join(
            f"{k}={round(v, 3) if isinstance(v, float) else v}"
            for k, v in details.items()
        )
        print(f"           model output: {rendered}")

    explanation = prediction.explanation
    if explanation and explanation.get("top_features"):
        print("           top reasons (SHAP):")
        for feature in explanation["top_features"]:
            arrow = "^" if feature["direction"] == "increases_risk" else "v"
            print(
                f"             {arrow} {feature['feature']} "
                f"(value={round(feature['value'], 2)}, "
                f"impact={round(feature['contribution'], 3)})"
            )


def run_scenario(label: str, telemetry: Mapping[str, Any]) -> None:
    pipeline = MaintenancePipeline()
    result = pipeline.predict(telemetry)

    print("=" * 68)
    print(f"VEHICLE: {label}")
    print(
        f"  overall status = {result.status} | "
        f"overall severity = {result.overall_severity}"
    )
    print("-" * 68)
    for name in ("engine", "brake", "battery", "tire"):
        _print_component(name, result.components[name])

    if result.alerts:
        print("-" * 68)
        print("  ALERTS:")
        for alert in result.alerts:
            print(f"    - [{alert.severity.upper()}] {alert.component}: {alert.message}")
    print()


def main() -> int:
    print(
        "\nPredictive maintenance demo — same pipeline the REST API and UI use.\n"
        "Health is 0-100% (higher is better). maintenance=YES means service it.\n"
    )
    run_scenario("HEALTHY fleet vehicle", HEALTHY_VEHICLE)
    run_scenario("DEGRADED fleet vehicle", DEGRADED_VEHICLE)
    print(
        "How to read this:\n"
        "  - health%   : model confidence the part is in good shape.\n"
        "  - severity  : normal / warning / critical rollup per part.\n"
        "  - SHAP      : the inputs that pushed the score up (^ = worse).\n"
        "\n"
        "Note: engine, brake, and tire behave intuitively (healthy vs degraded).\n"
        "The battery SoH model (3D) has poor test R2 on its dataset, so its\n"
        "absolute % is unreliable and reads low even for a fresh battery. It is\n"
        "flagged here for honesty; treat battery % as a known-weak signal.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
