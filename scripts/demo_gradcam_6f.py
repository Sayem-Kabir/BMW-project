"""Module 6F live Grad-CAM demo script.

Usage:
    python scripts/demo_gradcam_6f.py
    python scripts/demo_gradcam_6f.py path/to/frame.jpg --event-type road_hazard
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.xai.gradcam import generate_gradcam


def main() -> int:
    parser = argparse.ArgumentParser(description="Module 6F Grad-CAM demo")
    parser.add_argument("image", nargs="?", default=None, help="Optional image path")
    parser.add_argument("--event-type", default="drowsiness")
    args = parser.parse_args()

    if args.image:
        frame = cv2.imread(args.image)
        if frame is None:
            print(f"Could not read image: {args.image}")
            return 1
    else:
        frame = np.zeros((360, 480, 3), dtype=np.uint8)
        frame[:] = (35, 35, 45)
        cv2.rectangle(frame, (120, 80), (360, 280), (90, 90, 120), -1)
        cv2.circle(frame, (190, 150), 18, (200, 200, 220), -1)
        cv2.circle(frame, (290, 150), 18, (200, 200, 220), -1)

    result = generate_gradcam(frame, event_type=args.event_type)
    print("phase=", result.phase)
    print("method=", result.method)
    print("activation_mass=", result.activation_mass)
    print("heatmap_url=", result.heatmap_url)
    print("heatmap_path=", result.heatmap_path)
    print("description=", result.description)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
