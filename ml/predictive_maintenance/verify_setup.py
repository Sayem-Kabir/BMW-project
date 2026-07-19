"""Smoke-check Module 3A local datasets and feature frames."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from ml.predictive_maintenance import (
        datasets_ready,
        prepare_all_module_frames,
        required_dataset_paths,
        summarize_frames,
    )

    print("Module 3A — predictive maintenance data check")
    print("=" * 60)
    for key, path in required_dataset_paths().items():
        mark = "OK" if path.is_file() else "MISSING"
        print(f"  [{mark}] {key}: {path}")

    if not datasets_ready():
        print("\nNot all required CSVs are present under data/predictive_maintenance/")
        return 1

    frames = prepare_all_module_frames()
    print()
    print(summarize_frames(frames))
    print("\n3A setup OK — ready for local 3B–3E training notebooks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
