"""One-shot Module 6G SHAP seed — persist a degraded maintenance prediction.

Usage (backend must be running):

    python scripts/seed_xai_shap_6g.py
"""

from __future__ import annotations

import json
import sys
import urllib.request

VID = "00000000-0000-4000-8000-000000000003"
URL = f"http://localhost:8000/api/v1/maintenance/{VID}/predict"

TELEMETRY = {
    "engine": {
        "Voltage (V)": 355.0,
        "Current (A)": 140.0,
        "Motor Speed (RPM)": 5200.0,
        "Temperature (°C)": 96.0,
        "Vibration (g)": 3.8,
        "Ambient Temp (°C)": 33.0,
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
        "Oil_Quality": 42.0,
        "Failure_History": 3.0,
        "Anomalies_Detected": 4.0,
        "Diagnostic_Trouble_Code_Count": 5.0,
        "CAN_Message_Rate_Hz": 380.0,
        "Sensor_Packet_Loss_Rate": 4.5,
        "Days_Since_Last_Maintenance": 280.0,
    },
    "battery": {
        "Cycle": 420.0,
        "Voltage_V": 3.55,
        "Current_A": 8.5,
        "Temperature_C": 41.0,
        "Time_s": 1800.0,
    },
    "tire": {
        "Tire_Pressure": 24.0,
        "Vibration_Levels": 5.5,
        "Actual_Load": 5400.0,
        "Usage_Hours": 9000.0,
        "Days_Since_Last_Maintenance": 410.0,
        "Road_Conditions_code": 2.0,
        "Weather_Conditions_code": 2.0,
        "tire_pressure_deviation": 6.0,
        "load_ratio": 0.95,
    },
}


def main() -> int:
    body = json.dumps({"telemetry": TELEMETRY}).encode("utf-8")
    request = urllib.request.Request(
        URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.loads(response.read())
    print(json.dumps(data, indent=2)[:2000])
    print(
        f"\nSeeded vehicle {VID}: status={data.get('status')} "
        f"persisted={data.get('persisted')} severity={data.get('overall_severity')}"
    )
    print("Explain via: POST /api/v1/xai/explain {vehicle_id, component: engine|brake|battery|tire}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"seed failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
