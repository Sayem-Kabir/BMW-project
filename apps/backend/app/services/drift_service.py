"""Drift detection service — Spec Phase 11B."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ml.governance.psi import drift_severity, psi

logger = logging.getLogger(__name__)

_BASELINE_PATH = (
    Path(__file__).resolve().parents[3] / "ml" / "governance" / "baselines" / "telemetry_baseline.json"
)
# parents: services -> app -> backend -> BMW? 
# __file__ = apps/backend/app/services/drift_service.py
# parents[0]=services, [1]=app, [2]=backend, [3]=apps, [4]=BMW
# Fix path


def _baseline_path() -> Path:
    here = Path(__file__).resolve()
    # apps/backend/app/services/drift_service.py → repo root
    return here.parents[4] / "ml" / "governance" / "baselines" / "telemetry_baseline.json"


def load_baseline() -> dict[str, Any]:
    path = _baseline_path()
    if not path.exists():
        # Fallback relative to cwd
        alt = Path("ml/governance/baselines/telemetry_baseline.json")
        path = alt if alt.exists() else path
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def check_drift(
    live_features: dict[str, list[float]],
    *,
    threshold: float | None = None,
) -> dict[str, Any]:
    baseline = load_baseline()
    thr = float(threshold if threshold is not None else baseline.get("alert_threshold_psi", 0.25))
    features_meta = baseline.get("features") or {}
    results: list[dict[str, Any]] = []
    alerts: list[str] = []

    for name, meta in features_meta.items():
        expected = list(meta.get("samples") or [])
        actual = list(live_features.get(name) or [])
        if not actual:
            results.append(
                {
                    "feature": name,
                    "psi": None,
                    "severity": "missing",
                    "n_live": 0,
                    "n_baseline": len(expected),
                }
            )
            continue
        score = psi(expected, actual)
        sev = drift_severity(score)
        row = {
            "feature": name,
            "psi": round(score, 4),
            "severity": sev,
            "n_live": len(actual),
            "n_baseline": len(expected),
            "alert": score >= thr,
        }
        results.append(row)
        if score >= thr:
            alerts.append(f"{name}: PSI={score:.3f} ({sev})")

    return {
        "threshold_psi": thr,
        "features": results,
        "drift_detected": bool(alerts),
        "alerts": alerts,
        "phase": "11B",
    }
