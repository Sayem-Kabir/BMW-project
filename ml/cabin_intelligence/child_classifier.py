"""Child vs adult classification from person bbox vs seat-zone size (Module 1H)."""

from __future__ import annotations


def seat_zone_height_px(zone_xyxy: tuple[float, float, float, float], frame_h: int) -> float:
    """Absolute pixel height of a normalized seat zone."""
    _x1, y1, _x2, y2 = zone_xyxy
    return max(1.0, (y2 - y1) * float(frame_h))


def bbox_height_px(bbox_xyxy: list[float] | tuple[float, ...]) -> float:
    if len(bbox_xyxy) < 4:
        return 0.0
    return max(0.0, float(bbox_xyxy[3]) - float(bbox_xyxy[1]))


def child_height_ratio(
    bbox_xyxy: list[float] | tuple[float, ...],
    zone_xyxy: tuple[float, float, float, float],
    frame_h: int,
) -> float:
    """bbox_height / seat_zone_height (lower → more likely a child)."""
    zone_h = seat_zone_height_px(zone_xyxy, frame_h)
    return bbox_height_px(bbox_xyxy) / zone_h


def is_child(
    bbox_xyxy: list[float] | tuple[float, ...],
    zone_xyxy: tuple[float, float, float, float],
    frame_h: int,
    *,
    threshold: float = 0.50,
) -> bool:
    """True when person bbox is short relative to the seat zone (spec: ratio < 0.5)."""
    return child_height_ratio(bbox_xyxy, zone_xyxy, frame_h) < threshold
