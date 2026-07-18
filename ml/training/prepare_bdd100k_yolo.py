"""
Helpers for the optional YOLO-format BDD100K object-detection dataset.

Module 2B semantic segmentation uses ``notebooks/train_road_seg.ipynb``.

Usage:
  python -m ml.training.prepare_bdd100k_yolo --root data/bdd100k_yolo --scaffold
  python -m ml.training.prepare_bdd100k_yolo --root data/bdd100k_yolo --check
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ml.road_understanding.config import ROAD_CLASS_NAMES


def scaffold(root: Path) -> None:
    for split in ("train", "val"):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)

    dest_yaml = root / "data.yaml"
    text = f"""path: {root.resolve().as_posix()}
train: images/train
val: images/val

nc: {len(ROAD_CLASS_NAMES)}
names:
"""
    for i, name in enumerate(ROAD_CLASS_NAMES):
        text += f"  {i}: {name}\n"
    dest_yaml.write_text(text, encoding="utf-8")
    print(f"[ok] Scaffolded BDD YOLO layout at {root}")
    print(f"     classes ({len(ROAD_CLASS_NAMES)}): {list(ROAD_CLASS_NAMES)}")
    print(f"     yaml: {dest_yaml}")
    print(
        "Next: convert BDD100K detection labels to YOLO .txt under labels/{train,val}\n"
        "      Toolkit: https://github.com/bdd100k/bdd100k\n"
        "      Or add a Kaggle YOLO-format BDD dataset and train on Colab/Kaggle."
    )


def check(root: Path) -> int:
    yaml_candidates = [root / "data.yaml", root / "dataset.yaml"]
    yaml_path = next((p for p in yaml_candidates if p.is_file()), None)
    if yaml_path is None:
        print(f"[fail] No data.yaml under {root}")
        return 1

    img_train = root / "images" / "train"
    img_val = root / "images" / "val"
    # Also accept train/images layout
    if not img_train.is_dir():
        img_train = root / "train" / "images"
    if not img_val.is_dir():
        img_val = root / "val" / "images"
    if not img_val.is_dir():
        img_val = root / "valid" / "images"

    n_train = len(list(img_train.glob("*"))) if img_train.is_dir() else 0
    n_val = len(list(img_val.glob("*"))) if img_val.is_dir() else 0
    print(f"[ok] yaml={yaml_path}")
    print(f"     train images≈{n_train}  val images≈{n_val}")
    if n_train == 0:
        print("[warn] No training images found — dataset not ready for train_road_yolo")
        return 2
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scaffold/check BDD100K YOLO dataset layout")
    p.add_argument("--root", type=str, required=True, help="Dataset root directory")
    p.add_argument("--scaffold", action="store_true")
    p.add_argument("--check", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root)
    if args.scaffold:
        scaffold(root)
    if args.check:
        raise SystemExit(check(root))
    if not args.scaffold and not args.check:
        print("Specify --scaffold and/or --check")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
