"""
Train YOLOv8n for driver monitoring (Module 1D).

Primary dataset (Colab):
  https://www.kaggle.com/datasets/habbas11/dms-driver-monitoring-system
  Classes: Open Eye, Closed Eye, Cigarette, Phone, Seatbelt

Preferred: notebooks/train_driver_yolo_colab.ipynb

Local / scripted:
  python -m ml.training.train_driver_yolo --data path/to/data.yaml --epochs 50
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
    device: str | int | None = None,
    project: str = "runs",
    name: str = "driver_monitor_dms_v1",
    model: str = "yolov8n.pt",
) -> Path:
    from ultralytics import YOLO

    from ml.common.gpu_detector import get_inference_device

    data_yaml = Path(data_yaml)
    if not data_yaml.is_file():
        raise FileNotFoundError(
            f"Dataset YAML not found: {data_yaml}\n"
            "Use notebooks/train_driver_yolo_colab.ipynb or download the Kaggle DMS dataset."
        )

    resolved_device = get_inference_device(device)
    yolo = YOLO(model)
    results = yolo.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=resolved_device,
        patience=15,
        save_period=10,
        project=project,
        name=name,
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
    )

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
    p.add_argument("--data", type=str, default=str(DEFAULT_DATA), help="Path to data.yaml")
    p.add_argument("--epochs", type=int, default=100)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument(
        "--device",
        default=None,
        help="GPU id / 'cuda:0' / 'cpu' (default: auto-detect via ml.common.gpu_detector)",
    )
    p.add_argument("--project", type=str, default="runs")
    p.add_argument("--name", type=str, default="driver_monitor_dms_v1")
    p.add_argument("--model", type=str, default="yolov8n.pt")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    device = args.device
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
