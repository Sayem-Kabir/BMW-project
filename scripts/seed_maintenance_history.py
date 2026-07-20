"""Seed demo maintenance history: run N degrading predictions through 3H.

Usage (backend must be running on port 8000, Postgres up, vehicle seeded):

    python scripts/seed_maintenance_history.py
"""

from __future__ import annotations

import json
import time
import urllib.request

VID = "00000000-0000-4000-8000-000000000003"
URL = f"http://localhost:8000/api/v1/maintenance/{VID}/predict"

HEALTHY = {
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

DEGRADED = {
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

STEPS = 8


def main() -> int:
    for i in range(STEPS):
        t = i / (STEPS - 1)
        telemetry = {
            comp: {
                key: round(
                    HEALTHY[comp][key]
                    + t * (DEGRADED[comp][key] - HEALTHY[comp][key]),
                    3,
                )
                for key in HEALTHY[comp]
            }
            for comp in HEALTHY
        }
        body = json.dumps({"telemetry": telemetry}).encode("utf-8")
        request = urllib.request.Request(
            URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read())
        print(
            f"run {i + 1}/{STEPS}: wear={t:.2f} "
            f"status={data['status']} severity={data['overall_severity']} "
            f"persisted={data['persisted']}"
        )
        time.sleep(1.2)
    print("\nDone. Open http://localhost:3000/maintenance and check Health trend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
