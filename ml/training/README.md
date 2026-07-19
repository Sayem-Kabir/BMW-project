# ML training guides

## Module 1D ? Driver monitoring YOLO
#
# Primary dataset (used in Colab notebook):
#   https://www.kaggle.com/datasets/habbas11/dms-driver-monitoring-system
#
# Classes (5):
#   0 Open Eye | 1 Closed Eye | 2 Cigarette | 3 Phone | 4 Seatbelt
#
# Workflow:
#   1. Open notebooks/train_driver_yolo_colab.ipynb in Google Colab (GPU)
#   2. Download DMS via opendatasets (needs Kaggle API token)
#   3. Train YOLOv8n (~100 epochs)
#   4. Download best.pt ? ml/models/driver_monitor_best.pt
#   5. Inference:
#        from ml.driver_monitoring import YOLODriverDetector
#
# Local train (optional):
#   pip install ultralytics
#   python -m ml.training.train_driver_yolo --data path/to/data.yaml --epochs 50

## Module 2B ? Road semantic segmentation (BDD100K)
#
# Dataset: BDD100K semantic segmentation images + train-ID masks
#
# Model: DeepLabV3Plus, ResNet50 encoder, 512x512 input
# Output classes:
#   0 road | 1 shoulder | 2 background
#
# Workflow:
#   1. Open notebooks/train_road_seg.ipynb in Colab
#   2. Download the BDD100K segmentation dataset used by the notebook
#   3. Train the three-class model
#   4. Download deeplabv3_road.pt ? ml/models/seg_road.pt
#   5. Inference:
#        from ml.road_understanding import segment_road
#
# `train_road_yolo.py` and `prepare_bdd100k_yolo.py` are optional utilities
# for a separate bounding-box detector needed by tracking/object modules.

## Module 2F ? Temporal pedestrian localization (Caltech Pedestrian YOLO)
#
# Dataset:
#   https://www.kaggle.com/datasets/abhinavsasikumar/caltech-pedestrian-yolo/data
#
# Model: YOLOv8n backbone + 256-unit LSTM, 224x224 input, five-frame window
# Output: one primary normalized pedestrian bbox + confidence
#
# Workflow:
#   1. Open notebooks/train_pedestrian_temporal.ipynb in Colab or Kaggle
#   2. Attach/download the Caltech Pedestrian YOLO dataset
#   3. Train and evaluate with sequence-group-level splits
#   4. Download best_pedestrian_yololstm.pt ? ml/models/
#   5. Inference:
#        from ml.road_understanding import TemporalPedestrianLocalizer
#
# Local checkpoint check:
#   python -m ml.training.train_pedestrian_temporal --verify-weights ml/models/best_pedestrian_yololstm.pt
#
# This module performs temporal localization and short-occlusion confirmation.
# It does not classify pedestrian crossing intent because Caltech has no intent
# labels.

## Phase 3 ? Predictive maintenance (local notebooks)

Datasets (copy into `data/predictive_maintenance/`, git-ignored):

- `EV_Predictive_Maintenance_Dataset_15min.csv` ? 3C brakes, 3D battery, 3G
- `EV_Battery_Dataset_1.csv` ? 3D battery SoH cycles
- `NEV_fault_dataset.csv` ? 3B fault labels
- `logistics_predictive_maintenanceV2.csv` ? 3E tire wear (`TPI` ? `Tire_Wear_pct`)

Module 3A (feature engineering):

1. Open `notebooks/03_maintenance_feature_engineering.ipynb` locally
2. Or run: `python -m ml.predictive_maintenance.verify_setup`
3. Frames for later notebooks:
   `from ml.predictive_maintenance import prepare_brake_frame, prepare_engine_fault_frame, ...`

Module 3B local training:

1. Install: `pip install -r apps/backend/requirements-phase3.txt`
2. Open `notebooks/train_engine_fault_3b.ipynb`
3. Run every cell to train/evaluate the four-class XGBoost classifier
4. The final cells save and reload `ml/models/engine_fault_clf.joblib`

Module 3C local training:

1. Open `notebooks/train_brake_wear_3c.ipynb`
2. Train the logistics `Brake_Condition` XGBoost classifier
3. Evaluate Good / Fair / Poor condition on the held-out test set
4. Save and reload `ml/models/brake_condition_xgb.joblib`

Module 3C was redefined from EVIoT pad-wear regression because that target was
statistically disconnected from its predictors. The logistics model excludes
maintenance outputs, severity, costs, and predictive indexes to avoid leakage.

Module 3D local training:

1. Open `notebooks/train_battery_soh_3d.ipynb`
2. Train chronologically on `EV_Battery_Dataset_1.csv`
3. Exclude `Capacity_Ah`, which directly defines `SOH_pct`
4. Compare against the last-known-SOH baseline on future cycles
5. Save and reload `ml/models/battery_soh_xgb.joblib` if the quality gate passes

EVIoT SoH is excluded from 3D training because its target is statistically
disconnected from its battery telemetry.

Module 3E local training:

1. Open `notebooks/train_tire_wear_3e.ipynb`
2. Train the XGBoost regressor on the logistics dataset's predefined splits
3. Predict `Tire_Wear_pct`, a 0–100 proxy derived from `TPI`
4. Exclude raw `TPI` and downstream maintenance/predictive outputs
5. Save and reload `ml/models/tire_wear_model.joblib` if the quality gate passes

The 3E output is a dataset-derived wear-risk proxy, not a direct tread-depth
measurement. The bundle records this target meaning, feature ranges, category
encodings, dependency versions, and held-out metrics.

Module 3G unified inference:

```python
from ml.predictive_maintenance import MaintenancePipeline

result = MaintenancePipeline().predict({
    "engine": engine_feature_map,
    "brake": brake_feature_map,
    "battery": battery_feature_map,
    "tire": tire_feature_map,
})
```

The pipeline runs 3B–3E independently, preserves successful predictions when
another component is unavailable, emits warning/critical alerts, and returns
the top three native XGBoost SHAP contributions for each successful model.
Inputs may be nested by component as above or supplied as one flat enriched
feature map.

The four training datasets use different feature contracts. A raw 3F VSS
snapshot does not contain all required fields (for example battery cycle and
logistics maintenance history), so 3G reports those components as unavailable
instead of inventing values. A later telemetry-enrichment layer can populate
the component maps from live signals and stored history.

Training modules 3B?3E use dedicated local notebooks (CPU-friendly; no Colab required).
Save model artifacts to `ml/models/*.joblib`.
