#!/usr/bin/env python3
"""Export YOLO weights to ONNX (+ optional INT8 notes) — Spec Section 19.2 / Phase 13."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Ultralytics YOLO → ONNX")
    parser.add_argument(
        "--model",
        default="ml/models/driver_monitor_best.pt",
        help="Path to .pt weights (or yolov8n.pt)",
    )
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--int8", action="store_true", help="Request INT8 export when supported")
    args = parser.parse_args()

    model_path = Path(args.model)
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ultralytics not installed — pip install ultralytics")
        return 1

    if not model_path.is_file():
        print(f"Model not found: {model_path} — will try Ultralytics name download")
        name = args.model
    else:
        name = str(model_path)

    model = YOLO(name)
    kwargs = {"format": "onnx", "imgsz": args.imgsz}
    if args.int8:
        kwargs["int8"] = True
    out = model.export(**kwargs)
    print(f"Exported: {out}")

    # Sign sidecar when possible
    try:
        from ml.models.signed_ota import sign_file

        p = Path(str(out))
        if p.is_file():
            meta = sign_file(p)
            print(f"Signed: {meta}")
    except Exception as exc:  # noqa: BLE001
        print(f"Signing skipped: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
