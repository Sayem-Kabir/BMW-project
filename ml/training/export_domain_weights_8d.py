"""Module 8D — export domain YOLO best.pt into ml/models/ (training companion).

This is the **only** Phase 8 module that runs model training (when --train is set).

Examples:
  # Copy an existing Ultralytics run into the registry filenames
  python -m ml.training.export_domain_weights_8d \\
      --driver-best runs/driver_monitor_dms_v1/weights/best.pt

  # Train driver YOLO then export (needs dataset YAML + GPU/CPU)
  python -m ml.training.export_domain_weights_8d --train-driver \\
      --data ml/training/datasets/driver_monitoring_dataset.yaml --epochs 3

  # Train road YOLO then export
  python -m ml.training.export_domain_weights_8d --train-road \\
      --data ml/training/datasets/bdd100k_road_dataset.yaml --epochs 3
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
DRIVER_DEST = MODELS_DIR / "driver_monitor_best.pt"
ROAD_DEST = MODELS_DIR / "road_yolov8m_best.pt"


def export_weight(src: Path, dest: Path) -> Path:
    if not src.is_file():
        raise FileNotFoundError(f"Weight file not found: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() == dest.resolve():
        print(f"Already at registry path: {dest} ({dest.stat().st_size} bytes)")
        return dest
    shutil.copy2(src, dest)
    print(f"Exported {src} → {dest} ({dest.stat().st_size} bytes)")
    return dest


def train_driver(data: str, epochs: int, batch: int) -> Path:
    from ml.training.train_driver_yolo import train

    return train(data, epochs=epochs, batch=batch, name="driver_monitor_8d")


def train_road(data: str, epochs: int, batch: int) -> Path:
    from ml.training.train_road_yolo import train

    return train(data, epochs=epochs, batch=batch, name="road_yolo_8d")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Module 8D domain YOLO export / train")
    p.add_argument("--driver-best", type=str, default="", help="Path to driver best.pt")
    p.add_argument("--road-best", type=str, default="", help="Path to road best.pt")
    p.add_argument("--train-driver", action="store_true", help="Run driver YOLO training")
    p.add_argument("--train-road", action="store_true", help="Run road YOLO training")
    p.add_argument("--data", type=str, default="", help="Ultralytics data.yaml for training")
    p.add_argument("--epochs", type=int, default=50)
    p.add_argument("--batch", type=int, default=8)
    args = p.parse_args(argv)

    if args.train_driver:
        if not args.data:
            print("--data is required with --train-driver", file=sys.stderr)
            return 2
        best = train_driver(args.data, args.epochs, args.batch)
        export_weight(best, DRIVER_DEST)

    if args.train_road:
        if not args.data:
            print("--data is required with --train-road", file=sys.stderr)
            return 2
        best = train_road(args.data, args.epochs, args.batch)
        export_weight(best, ROAD_DEST)

    if args.driver_best:
        export_weight(Path(args.driver_best), DRIVER_DEST)
    if args.road_best:
        export_weight(Path(args.road_best), ROAD_DEST)

    if not any(
        [args.train_driver, args.train_road, args.driver_best, args.road_best]
    ):
        print(
            "Nothing to do. Pass --driver-best/--road-best or --train-driver/--train-road.\n"
            "See docs/TRAINING.md (Module 8D).",
            file=sys.stderr,
        )
        return 2

    print("Module 8D complete. Verify with: python -m ml.models.download_registry --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
