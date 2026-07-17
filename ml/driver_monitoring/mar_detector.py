"""Mouth Aspect Ratio (MAR) — yawning detection (Module 1B)."""

from __future__ import annotations

import numpy as np
from scipy.spatial import distance


def compute_mar(mouth_points: np.ndarray) -> float:
    """
    Mouth Aspect Ratio from 8 inner-mouth landmarks (Dlib indices 60–67).

    mouth_points layout (relative to MOUTH_IDX order):
      0: left corner, 1–3: top, 4: right corner, 5–7: bottom

    MAR = vertical opening / horizontal width
    """
    if mouth_points.shape[0] < 8:
        raise ValueError(f"Expected 8 mouth points, got {mouth_points.shape[0]}")

    # Vertical: upper mid (index 2) to lower mid (index 6) in inner-mouth ring
    vertical = distance.euclidean(mouth_points[2], mouth_points[6])
    # Horizontal: left corner (0) to right corner (4)
    horizontal = distance.euclidean(mouth_points[0], mouth_points[4])
    if horizontal <= 0:
        return 0.0
    return float(vertical / horizontal)
