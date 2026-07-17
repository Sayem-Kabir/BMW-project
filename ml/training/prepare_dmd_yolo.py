"""
Helpers to validate / scaffold a YOLO-format driver monitoring dataset (Module 1D).

This does NOT download DMD (access is request-only). Use Vicomtech DEx to export
frames, then convert boxes to YOLO .txt labels matching class ids in config.py:

  0 = phone
  1 = smoking
  2 = no_seatbelt

Usage:
  python -m ml.training.prepare_dmd_yolo --root path/to/yolo_dataset --check
  python -m ml.training.prepare_dmd_yolo --root path/to/empty_dir --scaffold
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from ml.driver_monitoring.config import YOLO_CLASS_NAMES

TEMPLATE_YAML = Path(__file__).resolve().parent / "datasets" / "driver_monitoring_dataset.yaml"


def scaffold(root: Path) -> None:
    for split in ("train", "val"):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)

    dest_yaml = root / "dataset.yaml"
    text = TEMPLATE_YAML.read_text(encoding="utf-8")
    # Point path at this root for local training
    lines = []
    for line in text.splitlines():
        if line.startswith("path:"):
            lines.append(f"path: {root.resolve().as_posix()}")
        else:
            lines.append(line)
    dest_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ok] Scaffolded YOLO layout at {root}")
    print(f"     classes: {list(YOLO_CLASS_NAMES)}")
    print(f"     yaml: {dest_yaml}")
    print(
        "Next: export DMD RGB frames/boxes via Vicomtech DEx, write YOLO .txt labels,\n"
        "      then upload this folder to Kaggle."
    )


def check(root: Path) -> int:
    yaml_path = root / "dataset.yaml"
    errors = 0
    if not yaml_path.is_file():
        print(f"[FAIL] Missing {yaml_path}")
        errors += 1
    for split in ("train", "val"):
        img_dir = root / "images" / split
        lbl_dir = root / "labels" / split
        if not img_dir.is_dir():
            print(f"[FAIL] Missing {img_dir}")
            errors += 1
            continue
        images = list(img_dir.glob("*.*"))
        labels = list(lbl_dir.glob("*.txt")) if lbl_dir.is_dir() else []
        print(f"[{'ok' if images else 'WARN'}] {split}: {len(images)} images, {len(labels)} labels")
        if not images:
            errors += 1
    if errors == 0:
        print("[ok] Dataset layout looks ready for Ultralytics training.")
    return errors


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True, help="Dataset root directory")
    p.add_argument("--scaffold", action="store_true", help="Create empty YOLO folders + dataset.yaml")
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
