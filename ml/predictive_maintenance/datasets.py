"""Phase 3A — loaders for local predictive-maintenance CSVs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from ml.predictive_maintenance.config import (
    BATTERY_CYCLE_TARGET,
    BATTERY_SOH_PATH,
    BATTERY_SOH_FEATURES,
    DEFAULT_RANDOM_STATE,
    DEFAULT_TEST_SIZE,
    EVIOT_BATTERY_FEATURES,
    EVIOT_BATTERY_TARGET,
    EVIOT_PATH,
    LOGISTICS_BRAKE_CLASS_NAMES,
    LOGISTICS_BRAKE_FEATURES,
    LOGISTICS_BRAKE_TARGET,
    LOGISTICS_TIRE_MODEL_FEATURES,
    LOGISTICS_TIRE_PATH,
    LOGISTICS_TIRE_TARGET,
    LOGISTICS_TIRE_TARGET_RAW,
    NEV_FAULT_FEATURES,
    NEV_FAULT_PATH,
    NEV_FAULT_TARGET,
)
from ml.predictive_maintenance.features import (
    engineer_battery_cycle_features,
    engineer_eviot_features,
    engineer_logistics_tire_features,
    engineer_nev_fault_features,
)


@dataclass(frozen=True)
class TrainReadyFrame:
    """Tabular frame ready for local sklearn / XGBoost / PyTorch training."""

    name: str
    features: tuple[str, ...]
    target: str
    frame: pd.DataFrame

    @property
    def X(self) -> pd.DataFrame:
        return self.frame.loc[:, list(self.features)]

    @property
    def y(self) -> pd.Series:
        return self.frame[self.target]

    def train_test_split(
        self,
        *,
        test_size: float = DEFAULT_TEST_SIZE,
        random_state: int = DEFAULT_RANDOM_STATE,
        stratify: bool = False,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        from sklearn.model_selection import train_test_split

        strat = self.y if stratify else None
        return train_test_split(
            self.X,
            self.y,
            test_size=test_size,
            random_state=random_state,
            stratify=strat,
        )


def _require_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            f"Copy the CSV into data/predictive_maintenance/ before training."
        )
    return path


def _require_columns(df: pd.DataFrame, columns: Iterable[str], *, label: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{label} missing columns: {missing}")


def load_eviot(path: Path | None = None) -> pd.DataFrame:
    """Load EVIoT 15-min predictive maintenance CSV (3C / 3D / 3G source)."""
    csv_path = _require_file(path or EVIOT_PATH)
    df = pd.read_csv(csv_path)
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    return engineer_eviot_features(df)


def load_battery_soh_cycles(path: Path | None = None) -> pd.DataFrame:
    """Load cycle-level battery aging CSV with SOH_pct (3D)."""
    csv_path = _require_file(path or BATTERY_SOH_PATH)
    df = pd.read_csv(csv_path)
    return engineer_battery_cycle_features(df)


def load_nev_fault(path: Path | None = None) -> pd.DataFrame:
    """Load NEV drivetrain fault classification CSV (3B)."""
    csv_path = _require_file(path or NEV_FAULT_PATH)
    df = pd.read_csv(csv_path)
    return engineer_nev_fault_features(df)


def load_logistics_tire(path: Path | None = None) -> pd.DataFrame:
    """Load logistics fleet CSV and derive Tire_Wear_pct from TPI (3E)."""
    csv_path = _require_file(path or LOGISTICS_TIRE_PATH)
    df = pd.read_csv(csv_path)
    return engineer_logistics_tire_features(df)


def prepare_brake_frame(path: Path | None = None) -> TrainReadyFrame:
    """3C — classify logistics Brake_Condition as Good / Fair / Poor."""
    df = load_logistics_tire(path)
    features = LOGISTICS_BRAKE_FEATURES
    target = LOGISTICS_BRAKE_TARGET
    _require_columns(df, [*features, target], label="logistics brake")
    frame = df.loc[:, [*features, target]].dropna().reset_index(drop=True)
    class_to_id = {
        class_name: class_id
        for class_id, class_name in enumerate(LOGISTICS_BRAKE_CLASS_NAMES)
    }
    unknown = sorted(set(frame[target]) - set(class_to_id))
    if unknown:
        raise ValueError(f"Unknown logistics brake classes: {unknown}")
    frame[target] = frame[target].map(class_to_id).astype(int)
    return TrainReadyFrame(
        name="brake_condition",
        features=features,
        target=target,
        frame=frame,
    )


def prepare_battery_eviot_frame(path: Path | None = None) -> TrainReadyFrame:
    """3D — regress SoH (0–1) from EVIoT battery telemetry."""
    df = load_eviot(path)
    features = EVIOT_BATTERY_FEATURES
    target = EVIOT_BATTERY_TARGET
    _require_columns(df, [*features, target], label="EVIoT battery")
    frame = df.loc[:, [*features, target]].dropna().reset_index(drop=True)
    return TrainReadyFrame(
        name="battery_soh_eviot",
        features=features,
        target=target,
        frame=frame,
    )


def prepare_battery_cycle_frame(path: Path | None = None) -> TrainReadyFrame:
    """3D — regress SOH_pct from cycle-level Li-ion aging CSV."""
    df = load_battery_soh_cycles(path)
    features = BATTERY_SOH_FEATURES
    target = BATTERY_CYCLE_TARGET
    _require_columns(df, [*features, target], label="battery cycle SoH")
    frame = df.loc[:, [*features, target]].dropna().reset_index(drop=True)
    return TrainReadyFrame(
        name="battery_soh_cycles",
        features=features,
        target=target,
        frame=frame,
    )


def prepare_engine_fault_frame(path: Path | None = None) -> TrainReadyFrame:
    """3B — classify NEV Fault Label (0–3)."""
    df = load_nev_fault(path)
    features = NEV_FAULT_FEATURES
    target = NEV_FAULT_TARGET
    _require_columns(df, [*features, target], label="NEV fault")
    frame = df.loc[:, [*features, target]].dropna().reset_index(drop=True)
    frame[target] = frame[target].astype(int)
    return TrainReadyFrame(
        name="engine_fault_nev",
        features=features,
        target=target,
        frame=frame,
    )


def prepare_tire_wear_frame(path: Path | None = None) -> TrainReadyFrame:
    """3E — regress the Tire_Wear_pct proxy derived from logistics TPI."""
    df = load_logistics_tire(path)
    features = LOGISTICS_TIRE_MODEL_FEATURES
    target = LOGISTICS_TIRE_TARGET
    needed = [*features, target]
    if LOGISTICS_TIRE_TARGET_RAW in df.columns:
        needed.append(LOGISTICS_TIRE_TARGET_RAW)
    _require_columns(df, needed, label="logistics tire")
    frame = df.loc[:, list(dict.fromkeys(needed))].dropna().reset_index(drop=True)
    return TrainReadyFrame(
        name="tire_wear_logistics",
        features=features,
        target=target,
        frame=frame,
    )


def dataset_inventory() -> pd.DataFrame:
    """Summarize which local CSVs exist and how many rows they have."""
    from ml.predictive_maintenance.config import required_dataset_paths

    rows: list[dict[str, object]] = []
    for key, path in required_dataset_paths().items():
        exists = path.is_file()
        n_rows = None
        n_cols = None
        if exists:
            # Cheap row count without loading full frame into memory twice.
            with path.open("rb") as fh:
                n_rows = sum(1 for _ in fh) - 1
            n_cols = len(pd.read_csv(path, nrows=0).columns)
        rows.append(
            {
                "dataset": key,
                "path": str(path),
                "exists": exists,
                "rows": n_rows,
                "cols": n_cols,
            }
        )
    return pd.DataFrame(rows)
