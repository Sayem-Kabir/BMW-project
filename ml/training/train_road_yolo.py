"""
Train the optional YOLOv8m road-object detector on BDD100K.

Module 2B uses semantic segmentation; train it with
``notebooks/train_road_seg.ipynb``.

Preferred: notebooks/train_road_yolo_colab.ipynb (Kaggle/Colab GPU)

Local / scripted:
  python -m ml.training.train_road_yolo --data path/to/bdd100k.yaml --epochs 50
"""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_DATA = Path(__file__).resolve().parent / "datasets" / "bdd100k_road_dataset.yaml"


def train(
    data_yaml: str | Path,
    *,
    epochs: int = 50,
    imgsz: int = 640,
    batch: int = 16,
    device: str | int | None = None,
    project: str = "runs",
    name: str = "road_yolov8m_bdd100k_v1",
    model: str = "yolov8m.pt",
) -> Path:
    from ultralytics import YOLO

    from ml.common.gpu_detector import get_inference_device

    data_yaml = Path(data_yaml)
    if not data_yaml.is_file():
        raise FileNotFoundError(
            f"Dataset YAML not found: {data_yaml}\n"
            "Convert BDD100K to YOLO format (see ml/training/README.md) "
            "or use notebooks/train_road_yolo_colab.ipynb on Kaggle."
        )

    resolved_device = get_inference_device(device)
    yolo = YOLO(model)
    results = yolo.train(
        data=str(data_yaml),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=resolved_device,
        patience=10,
        save_period=5,
        project=project,
        name=name,
        rect=True,
        # cache can be True on machines with enough RAM (Kaggle P100)
        flipud=0.0,
        fliplr=0.5,
        mosaic=1.0,
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
    print("Copy best.pt → ml/models/road_yolov8m_best.pt")
    return best


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train YOLOv8m road detector (BDD100K)")
    p.add_argument("--data", type=str, default=str(DEFAULT_DATA), help="Path to data.yaml")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument(
        "--device",
        default=None,
        help="GPU id / 'cuda:0' / 'cpu' (default: auto-detect)",
    )
    p.add_argument("--project", type=str, default="runs")
    p.add_argument("--name", type=str, default="road_yolov8m_bdd100k_v1")
    p.add_argument("--model", type=str, default="yolov8m.pt")
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
