# === COLAB / KAGGLE: YOLOv8 Driver Monitoring Training (Module 1D) ===
# Dataset: https://www.kaggle.com/datasets/habbas11/dms-driver-monitoring-system
# Prefer notebooks/train_driver_yolo_colab.ipynb for the full interactive flow.
#
# Classes: Open Eye, Closed Eye, Cigarette, Phone, Seatbelt

from pathlib import Path

from ultralytics import YOLO

DATASET_YAML = "/content/dms-driver-monitoring-system/data.yaml"
# On Kaggle after adding the dataset, this may instead be:
# DATASET_YAML = "/kaggle/input/dms-driver-monitoring-system/data.yaml"

assert Path(DATASET_YAML).is_file(), (
    f"Missing {DATASET_YAML}. Download the DMS dataset first "
    "(see notebooks/train_driver_yolo_colab.ipynb)."
)

model = YOLO("yolov8n.pt")

results = model.train(
    data=DATASET_YAML,
    epochs=100,
    imgsz=640,
    batch=32,
    device=0,
    patience=15,
    save_period=10,
    project="/content/runs",
    name="driver_monitor_dms_v1",
    flipud=0.0,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.1,
)

print(f"Best mAP50: {results.results_dict['metrics/mAP50(B)']:.4f}")
print(f"Best mAP50-95: {results.results_dict['metrics/mAP50-95(B)']:.4f}")
print("Download best.pt → ml/models/driver_monitor_best.pt")
