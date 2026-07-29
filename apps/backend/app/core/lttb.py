"""Largest-Triangle-Three-Buckets downsampling — Spec Phase 13 charts."""

from __future__ import annotations

import math
from typing import Any, Sequence


def lttb(
    points: Sequence[dict[str, Any]],
    threshold: int,
    *,
    x_key: str = "i",
    y_key: str = "y",
) -> list[dict[str, Any]]:
    """Downsample ``points`` to ``threshold`` while preserving visual shape."""
    n = len(points)
    if threshold <= 0 or n <= threshold:
        return list(points)
    if threshold == 1:
        return [points[0]]

    def x_of(idx: int) -> float:
        p = points[idx]
        if x_key in p and p[x_key] is not None:
            try:
                return float(p[x_key])
            except (TypeError, ValueError):
                pass
        return float(idx)

    def y_of(idx: int) -> float:
        try:
            return float(points[idx].get(y_key) or 0)
        except (TypeError, ValueError):
            return 0.0

    sampled: list[dict[str, Any]] = [points[0]]
    bucket_size = (n - 2) / (threshold - 2)
    a = 0

    for i in range(threshold - 2):
        avg_range_start = int(math.floor((i + 1) * bucket_size) + 1)
        avg_range_end = int(math.floor((i + 2) * bucket_size) + 1)
        avg_range_end = min(avg_range_end, n)

        avg_x = 0.0
        avg_y = 0.0
        avg_range_length = max(avg_range_end - avg_range_start, 1)
        for j in range(avg_range_start, avg_range_end):
            avg_x += x_of(j)
            avg_y += y_of(j)
        avg_x /= avg_range_length
        avg_y /= avg_range_length

        range_offs = int(math.floor(i * bucket_size) + 1)
        range_to = int(math.floor((i + 1) * bucket_size) + 1)
        range_to = min(range_to, n - 1)

        point_ax = x_of(a)
        point_ay = y_of(a)
        max_area = -1.0
        next_a = range_offs
        for j in range(range_offs, range_to):
            area = abs(
                (point_ax - avg_x) * (y_of(j) - point_ay)
                - (point_ax - x_of(j)) * (avg_y - point_ay)
            ) * 0.5
            if area > max_area:
                max_area = area
                next_a = j
        sampled.append(points[next_a])
        a = next_a

    sampled.append(points[-1])
    return sampled


def downsample_series(
    rows: Sequence[dict[str, Any]],
    max_points: int,
    *,
    y_key: str = "speed_kmh",
) -> list[dict[str, Any]]:
    """Attach synthetic x indices and LTTB-downsample chart rows."""
    indexed = [{**row, "i": i, "y": row.get(y_key)} for i, row in enumerate(rows)]
    out = lttb(indexed, max_points, x_key="i", y_key="y")
    cleaned: list[dict[str, Any]] = []
    for row in out:
        item = dict(row)
        item.pop("i", None)
        item.pop("y", None)
        cleaned.append(item)
    return cleaned
