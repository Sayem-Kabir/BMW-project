"""
Helpers to validate / scaffold a YOLO-format driver monitoring dataset (Module 1D).

Primary dataset (Colab):
  https://www.kaggle.com/datasets/habbas11/dms-driver-monitoring-system
  Layout: train/images, valid/images, train/labels, valid/labels

Usage:
  python -m ml.training.prepare_dmd_yolo --root path/to/dms --check
  python -m ml.training.prepare_dmd_yolo --root path/to/empty_dir --scaffold
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ml.driver_monitoring.config import YOLO_CLASS_NAMES

TEMPLATE_YAML = Path(__file__).resolve().parent / "datasets" / "driver_monitoring_dataset.yaml"


def scaffold(root: Path) -> None:
    for split in ("train", "valid"):
        (root / split / "images").mkdir(parents=True, exist_ok=True)
        (root / split / "labels").mkdir(parents=True, exist_ok=True)

    dest_yaml = root / "data.yaml"
    text = f"""path: {root.resolve().as_posix()}
train: train/images
val: valid/images

nc: {len(YOLO_CLASS_NAMES)}
names:
"""
    for i, name in enumerate(YOLO_CLASS_NAMES):
        text += f"  {i}: {name}\n"
    dest_yaml.write_text(text, encoding="utf-8")
    print(f"[ok] Scaffolded YOLO layout at {root}")
    print(f"     classes: {list(YOLO_CLASS_NAMES)}")
    print(f"     yaml: {dest_yaml}")
    print(
        "Next: download Kaggle DMS dataset (habbas11/dms-driver-monitoring-system)\n"
        "      or place images/labels here, then train with Colab notebook."
    )


def check(root: Path) -> int:
    yaml_candidates = [root / "data.yaml", root / "dataset.yaml"]
    yaml_path = next((p for p in yaml_candidates if p.is_file()), None)
    errors = 0
    if yaml_path is None:
        print(f"[FAIL] Missing data.yaml / dataset.yaml under {root}")
        errors += 1
    else:
        print(f"[ok] Found {yaml_path.name}")

    # Support both Roboflow (train/images) and classic (images/train) layouts
    layouts = [
        ("train", root / "train" / "images", root / "train" / "labels"),
        ("valid", root / "valid" / "images", root / "valid" / "labels"),
        ("train", root / "images" / "train", root / "labels" / "train"),
        ("val", root / "images" / "val", root / "labels" / "val"),
    ]
    found_any = False
    for split, img_dir, lbl_dir in layouts:
        if not img_dir.is_dir():
            continue
        found_any = True
        images = list(img_dir.glob("*.*"))
        labels = list(lbl_dir.glob("*.txt")) if lbl_dir.is_dir() else []
        print(f"[{'ok' if images else 'WARN'}] {split}: {len(images)} images, {len(labels)} labels")
        if not images:
            errors += 1

    if not found_any:
        print("[FAIL] No train/valid image folders found")
        errors += 1

    if errors == 0:
        print("[ok] Dataset layout looks ready for Ultralytics training.")
    return errors


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True, help="Dataset root directory")
    p.add_argument("--scaffold", action="store_true", help="Create empty YOLO folders + data.yaml")
    p.add_argument("--check", action="store_true", help="Validate existing YOLO layout")
    args = p.parse_args()

    if args.scaffold:
        scaffold(args.root)
    if args.check:
        raise SystemExit(check(args.root))
    if not args.scaffold and not args.check:
        p.error("Specify --scaffold and/or --check")


if __name__ == "__main__":
    main()
