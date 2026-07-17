# === KAGGLE NOTEBOOK: YOLOv8 Driver Monitoring Training (Module 1D) ===
# Runtime: GPU T4 / P100 | Estimated time: 3–5 hours @ 100 epochs
#
# Setup:
#   1. Request DMD: https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset
#   2. Convert RGB annotations to YOLO format (3 classes: phone, smoking, no_seatbelt)
#   3. Upload as Kaggle dataset (suggested name: dmd-driver-monitoring)
#   4. Create a new Notebook → Accelerator = GPU → Add Data → select your dataset
#   5. Paste this cell (or upload from repo notebooks/)
#
# Output:
#   /kaggle/working/runs/detect/driver_monitor_dmd_v1/weights/best.pt
#   Download → save locally as ml/models/driver_monitor_best.pt

from pathlib import Path

from ultralytics import YOLO

DATASET_YAML = "/kaggle/input/dmd-driver-monitoring/dataset.yaml"
# If your Kaggle dataset slug differs, update DATASET_YAML accordingly.

assert Path(DATASET_YAML).is_file(), (
    f"Missing {DATASET_YAML}. Add your YOLO-format DMD dataset to this notebook."
)

model = YOLO("yolov8n.pt")  # COCO pretrained backbone

results = model.train(
    data=DATASET_YAML,
    epochs=100,
    imgsz=640,
    batch=32,
    device=0,
    patience=15,
    save_period=10,
    project="/kaggle/working/runs",
    name="driver_monitor_dmd_v1",
    flipud=0.0,
    fliplr=0.5,
    mosaic=1.0,
    mixup=0.1,
)

print(f"Best mAP50: {results.results_dict['metrics/mAP50(B)']:.4f}")
print(f"Best mAP50-95: {results.results_dict['metrics/mAP50-95(B)']:.4f}")
print("Download best.pt from the Output panel → ml/models/driver_monitor_best.pt")
