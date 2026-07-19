"""Predictive maintenance package — Phase 3 (starts at Module 3A)."""

from ml.predictive_maintenance.battery_model import (
    BatterySoHPredictor,
    BatterySoHResult,
    battery_soh_model_ready,
)
from ml.predictive_maintenance.brake_model import (
    BrakeConditionClassifier,
    BrakeConditionResult,
    brake_condition_model_ready,
)
from ml.predictive_maintenance.config import (
    BATTERY_SOH_PATH,
    DATA_DIR,
    EVIOT_PATH,
    LOGISTICS_TIRE_PATH,
    NEV_FAULT_PATH,
    datasets_ready,
    required_dataset_paths,
)
from ml.predictive_maintenance.data_generator import (
    prepare_all_module_frames,
    summarize_frames,
)
from ml.predictive_maintenance.datasets import (
    TrainReadyFrame,
    dataset_inventory,
    load_battery_soh_cycles,
    load_eviot,
    load_logistics_tire,
    load_nev_fault,
    prepare_battery_cycle_frame,
    prepare_battery_eviot_frame,
    prepare_brake_frame,
    prepare_engine_fault_frame,
    prepare_tire_wear_frame,
)
from ml.predictive_maintenance.engine_model import (
    EngineFaultClassifier,
    EngineFaultResult,
    engine_fault_model_ready,
)
from ml.predictive_maintenance.pipeline import (
    COMPONENT_FEATURES,
    ComponentPrediction,
    MaintenanceAlert,
    MaintenancePipeline,
    MaintenancePipelineResult,
)
from ml.predictive_maintenance.tire_model import (
    TireWearPredictor,
    TireWearResult,
    tire_wear_model_ready,
)

__all__ = [
    "BATTERY_SOH_PATH",
    "BatterySoHPredictor",
    "BatterySoHResult",
    "BrakeConditionClassifier",
    "BrakeConditionResult",
    "COMPONENT_FEATURES",
    "ComponentPrediction",
    "DATA_DIR",
    "EVIOT_PATH",
    "EngineFaultClassifier",
    "EngineFaultResult",
    "LOGISTICS_TIRE_PATH",
    "MaintenanceAlert",
    "MaintenancePipeline",
    "MaintenancePipelineResult",
    "NEV_FAULT_PATH",
    "TireWearPredictor",
    "TireWearResult",
    "TrainReadyFrame",
    "dataset_inventory",
    "datasets_ready",
    "brake_condition_model_ready",
    "battery_soh_model_ready",
    "engine_fault_model_ready",
    "load_battery_soh_cycles",
    "load_eviot",
    "load_logistics_tire",
    "load_nev_fault",
    "prepare_all_module_frames",
    "prepare_battery_cycle_frame",
    "prepare_battery_eviot_frame",
    "prepare_brake_frame",
    "prepare_engine_fault_frame",
    "prepare_tire_wear_frame",
    "required_dataset_paths",
    "summarize_frames",
    "tire_wear_model_ready",
]
