"""Population Stability Index (PSI) — Spec Phase 11B drift detection."""

from __future__ import annotations

import math
from typing import Sequence


def _digitize(values: Sequence[float], edges: Sequence[float]) -> list[int]:
    """Assign each value to a bin index using left-closed edges (len(edges)-1 bins)."""
    bins: list[int] = []
    n = len(edges) - 1
    for v in values:
        placed = n - 1
        for i in range(n):
            if v < edges[i + 1] or i == n - 1:
                placed = i
                if v < edges[i + 1]:
                    break
        bins.append(placed)
    return bins


def psi(
    expected: Sequence[float],
    actual: Sequence[float],
    *,
    n_bins: int = 10,
    eps: float = 1e-4,
) -> float:
    """Compute PSI between expected (training) and actual (live) distributions."""
    if len(expected) < 2 or len(actual) < 2:
        return 0.0
    lo = min(min(expected), min(actual))
    hi = max(max(expected), max(actual))
    if hi <= lo:
        return 0.0
    step = (hi - lo) / n_bins
    edges = [lo + i * step for i in range(n_bins)] + [hi + 1e-9]
    exp_bins = _digitize(expected, edges)
    act_bins = _digitize(actual, edges)
    total_e = float(len(expected))
    total_a = float(len(actual))
    score = 0.0
    for i in range(n_bins):
        pe = max(exp_bins.count(i) / total_e, eps)
        pa = max(act_bins.count(i) / total_a, eps)
        score += (pa - pe) * math.log(pa / pe)
    return float(score)


def drift_severity(psi_value: float) -> str:
    """Common PSI thresholds: <0.1 stable, 0.1–0.25 mild, >0.25 significant."""
    if psi_value < 0.1:
        return "stable"
    if psi_value < 0.25:
        return "mild"
    return "significant"
