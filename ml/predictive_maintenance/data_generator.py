"""Phase 3A — prepare train/val frames for local maintenance notebooks.

Thin facade over `datasets.py` so training notebooks can call one entry point:
    from ml.predictive_maintenance import prepare_all_module_frames
"""

from __future__ import annotations

from ml.predictive_maintenance.datasets import (
    TrainReadyFrame,
    dataset_inventory,
    prepare_battery_cycle_frame,
    prepare_brake_frame,
    prepare_engine_fault_frame,
    prepare_tire_wear_frame,
)


def prepare_all_module_frames() -> dict[str, TrainReadyFrame]:
    """Build the four Module 3B–3E training frames from local CSVs."""
    return {
        "3B_engine_fault": prepare_engine_fault_frame(),
        "3C_brake_condition": prepare_brake_frame(),
        "3D_battery_soh": prepare_battery_cycle_frame(),
        "3E_tire_wear": prepare_tire_wear_frame(),
    }


def summarize_frames(frames: dict[str, TrainReadyFrame] | None = None) -> str:
    frames = frames or prepare_all_module_frames()
    lines = ["Predictive maintenance train-ready frames:", ""]
    for name, frame in frames.items():
        lines.append(
            f"  {name}: rows={len(frame.frame):,} "
            f"features={len(frame.features)} target={frame.target}"
        )
    lines.append("")
    lines.append("Dataset inventory:")
    inv = dataset_inventory()
    for _, row in inv.iterrows():
        status = "OK" if row["exists"] else "MISSING"
        lines.append(
            f"  [{status}] {row['dataset']}: "
            f"rows={row['rows']} cols={row['cols']} → {row['path']}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(summarize_frames())
