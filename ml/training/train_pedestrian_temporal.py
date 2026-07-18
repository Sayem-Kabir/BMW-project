"""
Train Module 2F temporal pedestrian localization (Caltech Pedestrian YOLO).

Dataset:
  https://www.kaggle.com/datasets/abhinavsasikumar/caltech-pedestrian-yolo/data

Preferred: notebooks/train_pedestrian_temporal.ipynb

This script is a local helper for architecture/checkpoint checks. Full sequence
training (dataset download, temporal grouping, augmentations, and evaluation)
lives in the notebook.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def verify_checkpoint(weights: str | Path) -> None:
    """Confirm a checkpoint matches the Module 2F YOLO-LSTM architecture."""
    import torch

    from ml.road_understanding.pedestrian_temporal import build_temporal_model

    weights = Path(weights)
    if not weights.is_file():
        raise FileNotFoundError(weights)

    try:
        state = torch.load(weights, map_location="cpu", weights_only=True)
    except TypeError:
        state = torch.load(weights, map_location="cpu")
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    if not isinstance(state, dict):
        raise ValueError("Checkpoint must contain a state_dict")

    model = build_temporal_model()
    model.load_state_dict(state, strict=True)
    print(f"Checkpoint OK: {weights}")
    print("Architecture: YOLOv8n backbone + LSTM(256) + fc_bbox/fc_conf")
    print("Task: primary pedestrian temporal localization (not crossing intent)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Module 2F Caltech temporal pedestrian localization helpers"
    )
    parser.add_argument(
        "--verify-weights",
        type=Path,
        default=Path("ml/models/best_pedestrian_yololstm.pt"),
        help="Validate a YOLO-LSTM checkpoint against the inference architecture",
    )
    args = parser.parse_args()

    print("Preferred training entrypoint:")
    print("  notebooks/train_pedestrian_temporal.ipynb")
    print(
        "Dataset: "
        "https://www.kaggle.com/datasets/abhinavsasikumar/caltech-pedestrian-yolo/data"
    )
    print()
    verify_checkpoint(args.verify_weights)


if __name__ == "__main__":
    main()
