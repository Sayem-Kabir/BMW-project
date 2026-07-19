"""Phase 3A — shared paths, filenames, and thresholds for predictive maintenance."""

from __future__ import annotations

from pathlib import Path

# ── Repo / data / model paths ───────────────────────────────────────
ML_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ML_ROOT.parent
MODELS_DIR = ML_ROOT / "models"
DATA_DIR = REPO_ROOT / "data" / "predictive_maintenance"

# Local CSVs (git-ignored under data/). Place downloads here before training.
EVIOT_FILENAME = "EV_Predictive_Maintenance_Dataset_15min.csv"
EVIOT_PATH = DATA_DIR / EVIOT_FILENAME

BATTERY_SOH_FILENAME = "EV_Battery_Dataset_1.csv"
BATTERY_SOH_PATH = DATA_DIR / BATTERY_SOH_FILENAME

NEV_FAULT_FILENAME = "NEV_fault_dataset.csv"
NEV_FAULT_PATH = DATA_DIR / NEV_FAULT_FILENAME

LOGISTICS_TIRE_FILENAME = "logistics_predictive_maintenanceV2.csv"
LOGISTICS_TIRE_PATH = DATA_DIR / LOGISTICS_TIRE_FILENAME

# Optional reference only (not used for training — metadata without cycle samples)
NASA_PCOE_METADATA_FILENAME = "nasa_pcoe_metadata.csv"
NASA_PCOE_METADATA_PATH = DATA_DIR / NASA_PCOE_METADATA_FILENAME

# Artifacts written by later training notebooks (3B–3E)
ENGINE_FAULT_MODEL_FILENAME = "engine_fault_clf.joblib"
ENGINE_FAULT_MODEL_PATH = MODELS_DIR / ENGINE_FAULT_MODEL_FILENAME
BRAKE_CONDITION_MODEL_FILENAME = "brake_condition_xgb.joblib"
BRAKE_CONDITION_MODEL_PATH = MODELS_DIR / BRAKE_CONDITION_MODEL_FILENAME
BATTERY_SOH_MODEL_FILENAME = "battery_soh_xgb.joblib"
BATTERY_SOH_MODEL_PATH = MODELS_DIR / BATTERY_SOH_MODEL_FILENAME
TIRE_WEAR_MODEL_FILENAME = "tire_wear_model.joblib"
TIRE_WEAR_MODEL_PATH = MODELS_DIR / TIRE_WEAR_MODEL_FILENAME

# ── Alert thresholds (Module 06) ────────────────────────────────────
ENGINE_ANOMALY_WARN = 0.60
ENGINE_ANOMALY_CRITICAL = 0.80
BATTERY_SOH_WARN_PCT = 80.0
BATTERY_SOH_CRITICAL_PCT = 65.0
TIRE_WEAR_WARN_PCT = 70.0
TIRE_WEAR_CRITICAL_PCT = 90.0

# ── Feature / target contracts used by 3B–3E notebooks ──────────────
LOGISTICS_BRAKE_FEATURES = (
    "Usage_Hours",
    "Actual_Load",
    "Engine_Temperature",
    "Tire_Pressure",
    "Fuel_Consumption",
    "Battery_Status",
    "Vibration_Levels",
    "Oil_Quality",
    "Failure_History",
    "Anomalies_Detected",
    "Diagnostic_Trouble_Code_Count",
    "CAN_Message_Rate_Hz",
    "Sensor_Packet_Loss_Rate",
    "Days_Since_Last_Maintenance",
)
LOGISTICS_BRAKE_TARGET = "Brake_Condition"
LOGISTICS_BRAKE_CLASS_NAMES = ("Good", "Fair", "Poor")

EVIOT_BATTERY_FEATURES = (
    "SoC",
    "Battery_Voltage",
    "Battery_Current",
    "Battery_Temperature",
    "Charge_Cycles",
    "Ambient_Temperature",
    "Power_Consumption",
)
EVIOT_BATTERY_TARGET = "SoH"

BATTERY_SOH_FEATURES = (
    "Cycle",
    "Voltage_V",
    "Current_A",
    "Temperature_C",
    "Time_s",
)
BATTERY_CYCLE_TARGET = "SOH_pct"

NEV_FAULT_FEATURES = (
    "Voltage (V)",
    "Current (A)",
    "Motor Speed (RPM)",
    "Temperature (°C)",
    "Vibration (g)",
    "Ambient Temp (°C)",
    "Humidity (%)",
)
NEV_FAULT_TARGET = "Fault Label"
NEV_FAULT_CLASS_NAMES = (
    "normal",
    "motor_fault",
    "inverter_fault",
    "battery_fault",
)

LOGISTICS_TIRE_FEATURES = (
    "Tire_Pressure",
    "Vibration_Levels",
    "Actual_Load",
    "Usage_Hours",
    "Days_Since_Last_Maintenance",
    "Road_Conditions",
    "Weather_Conditions",
)
LOGISTICS_TIRE_TARGET_RAW = "TPI"
LOGISTICS_TIRE_TARGET = "Tire_Wear_pct"
LOGISTICS_TIRE_MODEL_FEATURES = (
    "Tire_Pressure",
    "Vibration_Levels",
    "Actual_Load",
    "Usage_Hours",
    "Days_Since_Last_Maintenance",
    "Road_Conditions_code",
    "Weather_Conditions_code",
    "tire_pressure_deviation",
    "load_ratio",
)

DEFAULT_TEST_SIZE = 0.20
DEFAULT_RANDOM_STATE = 42


def required_dataset_paths() -> dict[str, Path]:
    """Paths that must exist before local 3B–3E training notebooks run."""
    return {
        "eviot": EVIOT_PATH,
        "battery_soh": BATTERY_SOH_PATH,
        "nev_fault": NEV_FAULT_PATH,
        "logistics_tire": LOGISTICS_TIRE_PATH,
    }


def datasets_ready() -> bool:
    return all(path.is_file() for path in required_dataset_paths().values())
