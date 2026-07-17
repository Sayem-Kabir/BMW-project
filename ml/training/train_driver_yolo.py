"""
Train YOLOv8n for driver monitoring (Module 1D).

Primary run environment: Kaggle free GPU (P100/T4), ~3–5 hours for 100 epochs.

Usage on Kaggle:
  1. Upload DMD (YOLO-format) as a dataset, OR use a distraction fallback dataset
  2. Add this script / notebook from the repo
  3. Ensure dataset.yaml path matches /kaggle/input/<your-dataset>/
  4. Runtime → Accelerator → GPU
  5. Run; download best.pt from /kaggle/working/runs/.../weights/best.pt
  6. Copy to local: ml/models/driver_monitor_best.pt

Usage locally (optional, needs GPU + prepared dataset):
  python -m ml.training.train_driver_yolo --data path/to/dataset.yaml --epochs 50
"""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_DATA = Path(__file__).resolve().parent / "datasets" / "driver_monitoring_dataset.yaml"


def train(
    data_yaml: str | Path,
    *,
    epochs: int = 100,
    imgsz: int = 640,
    batch: int = 32,
    device: str | int = 0,
    project: str = "runs",
    name: str = "driver_monitor_dmd_v1",
    model: str = "yolov8n.pt",
) -> Path:
    from ultralytics import YOLO

    data_yaml = Path(data_yaml)
    if not data_yaml.is_file():
        raise FileNotFoundError(
            f"Dataset YAML not found: {data_yaml}\n"
            "Prepare YOLO-format images/labels and update "
            "ml/training/datasets/driver_monitoring_dataset.yaml"
        )

    yolo = YOLO(model)
    results = yolo.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=device,
        patience=15,
        save_period=10,
        project=project,
        name=name,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
    )

    # Ultralytics stores best weights under the run directory
    best = Path(results.save_dir) / "weights" / "best.pt"
    metrics = getattr(results, "results_dict", {}) or {}
    map50 = metrics.get("metrics/mAP50(B)")
    map5095 = metrics.get("metrics/mAP50-95(B)")
    if map50 is not None:
        print(f"Best mAP50: {map50:.4f}")
    if map5095 is not None:
        print(f"Best mAP50-95: {map5095:.4f}")
    print(f"Best weights: {best}")
    return best


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train YOLOv8n driver monitoring detector")
    p.add_argument("--data", type=str, default=str(DEFAULT_DATA), help="Path to dataset.yaml")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--device", default="0", help="GPU id or 'cpu'")
    p.add_argument("--project", type=str, default="runs")
    p.add_argument("--name", type=str, default="driver_monitor_dmd_v1")
    p.add_argument("--model", type=str, default="yolov8n.pt")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    device: str | int = args.device
    if isinstance(device, str) and device.isdigit():
        device = int(device)
    train(
        args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=device,
        project=args.project,
        name=args.name,
        model=args.model,
    )


if __name__ == "__main__":
    main()
