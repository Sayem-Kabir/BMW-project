"""Module 4D — TTC calculation and safety event detectors.

Pure, side-effect-free logic that consumes Phase 1 driver monitoring (1G),
Phase 2 road understanding (2G), and Phase 3 Kuksa telemetry (3F). Missing
inputs are tolerated; individual detectors simply skip when required data is
absent. Stateful counters (phone duration, speed history) live in
:class:`EventDetector` and reset per session.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping, Sequence

# Module 08 thresholds
NEAR_COLLISION_TTC_SECONDS = 2.0
DRIVER_ASLEEP_DROWSY_FRAMES = 60  # 2 seconds @ 30 fps
UNSAFE_FOLLOWING_TTC_SECONDS = 4.0
UNSAFE_FOLLOWING_MIN_SPEED_KMH = 60.0
HARD_BRAKING_DECEL_KMH_PER_S = -12.0
PROLONGED_PHONE_SECONDS = 5.0
PEDESTRIAN_HAZARD_DISTANCE_M = 15.0
MIN_CLOSING_SPEED_KMH = 0.5

DEFAULT_FPS = 30.0
EVENT_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

_VEHICLE_CLASSES = {
    "car",
    "truck",
    "bus",
    "motorcycle",
    "vehicle",
}


@dataclass(frozen=True)
class SafetyEvent:
    """One detected safety incident for a single frame."""

    event_type: str
    severity: str
    reason: str
    evidence: dict[str, Any]
    telemetry_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventDetectionResult:
    """All events raised on one evaluation tick."""

    vehicle_id: str
    events: tuple[SafetyEvent, ...]
    timestamp: datetime
    warnings: tuple[str, ...] = ()
    skipped_detectors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "vehicle_id": self.vehicle_id,
            "events": [event.to_dict() for event in self.events],
            "timestamp": self.timestamp.isoformat(),
            "warnings": list(self.warnings),
            "skipped_detectors": list(self.skipped_detectors),
        }


def compute_ttc_seconds(
    distance_m: float,
    relative_speed_kmh: float,
    *,
    min_closing_speed_kmh: float = MIN_CLOSING_SPEED_KMH,
) -> float | None:
    """Return time-to-collision when the object is closing.

  TTC = distance_m / (relative_speed_kmh / 3.6). Returns ``None`` when the
  object is not closing fast enough to produce a finite, positive TTC.
    """
    distance = _optional_non_negative_float(distance_m)
    speed = _optional_non_negative_float(relative_speed_kmh)
    if distance is None or speed is None or speed < min_closing_speed_kmh:
        return None
    ttc = distance / (speed / 3.6)
    return round(ttc, 3) if isfinite(ttc) and ttc > 0.0 else None


class EventDetector:
    """Stateful per-stream detector for Module 4D."""

    def __init__(self, *, fps: float = DEFAULT_FPS) -> None:
        self.fps = _finite_float(fps, "fps")
        if self.fps <= 0.0:
            raise ValueError("fps must be positive")
        self._phone_frames = 0
        self._prev_speed_kmh: float | None = None
        self._prev_timestamp: datetime | None = None

    def reset(self) -> None:
        """Clear session counters before a new drive stream."""
        self._phone_frames = 0
        self._prev_speed_kmh = None
        self._prev_timestamp = None

    def process_frame(
        self,
        vehicle_id: str,
        driver_state: Mapping[str, Any] | None = None,
        road_state: Mapping[str, Any] | None = None,
        telemetry: Mapping[str, Any] | None = None,
        *,
        risk_score: float | None = None,
        timestamp: datetime | None = None,
    ) -> EventDetectionResult:
        identity = str(vehicle_id).strip()
        if not identity:
            raise ValueError("vehicle_id must not be empty")

        evaluated_at = timestamp or datetime.now(timezone.utc)
        if evaluated_at.tzinfo is None:
            evaluated_at = evaluated_at.replace(tzinfo=timezone.utc)

        driver = driver_state or {}
        road = road_state or {}
        telem = telemetry or {}

        warnings: list[str] = []
        skipped: list[str] = []
        events: list[SafetyEvent] = []

        snapshot = _build_telemetry_snapshot(driver, road, telem, risk_score)

        # ── TTC-based vehicle hazards ───────────────────────────────────
        speed_kmh = _optional_non_negative_float(
            telem.get("speed_kmh", telem.get("Vehicle.Speed"))
        )
        ttc_targets = _vehicle_ttc_targets(road)
        if not ttc_targets:
            skipped.append("ttc_vehicle")
        else:
            nearest = min(ttc_targets, key=lambda item: item["ttc_seconds"])
            snapshot["ttc_seconds"] = nearest["ttc_seconds"]
            snapshot["object_class"] = nearest["object_class"]
            snapshot["object_distance_m"] = nearest["distance_m"]
            snapshot["relative_speed_kmh"] = nearest["relative_speed_kmh"]
            snapshot["track_id"] = nearest.get("track_id")

            if nearest["ttc_seconds"] < NEAR_COLLISION_TTC_SECONDS:
                events.append(
                    SafetyEvent(
                        event_type="NEAR_COLLISION",
                        severity="CRITICAL",
                        reason=(
                            f"Near collision: TTC {nearest['ttc_seconds']:.1f}s "
                            f"(threshold {NEAR_COLLISION_TTC_SECONDS:.1f}s)"
                        ),
                        evidence=dict(nearest),
                        telemetry_snapshot=dict(snapshot),
                    )
                )
            elif (
                speed_kmh is not None
                and speed_kmh > UNSAFE_FOLLOWING_MIN_SPEED_KMH
                and nearest["ttc_seconds"] < UNSAFE_FOLLOWING_TTC_SECONDS
            ):
                events.append(
                    SafetyEvent(
                        event_type="UNSAFE_FOLLOWING_DISTANCE",
                        severity="HIGH",
                        reason=(
                            f"Unsafe following distance at {speed_kmh:.0f} km/h: "
                            f"TTC {nearest['ttc_seconds']:.1f}s"
                        ),
                        evidence={
                            **nearest,
                            "speed_kmh": speed_kmh,
                            "threshold_ttc_s": UNSAFE_FOLLOWING_TTC_SECONDS,
                            "threshold_speed_kmh": UNSAFE_FOLLOWING_MIN_SPEED_KMH,
                        },
                        telemetry_snapshot=dict(snapshot),
                    )
                )
            elif speed_kmh is None:
                warnings.append("speed_kmh missing; unsafe-following check skipped")

        # ── Driver asleep ───────────────────────────────────────────────
        drowsy_frames = _drowsy_frame_count(driver)
        if drowsy_frames is None:
            skipped.append("driver_asleep")
        elif drowsy_frames > DRIVER_ASLEEP_DROWSY_FRAMES:
            events.append(
                SafetyEvent(
                    event_type="DRIVER_ASLEEP",
                    severity="CRITICAL",
                    reason=(
                        f"Driver asleep: {drowsy_frames} consecutive drowsy frames "
                        f"(threshold {DRIVER_ASLEEP_DROWSY_FRAMES})"
                    ),
                    evidence={
                        "consecutive_drowsy_frames": drowsy_frames,
                        "threshold_frames": DRIVER_ASLEEP_DROWSY_FRAMES,
                        "ear_value": _optional_float(driver.get("ear_value")),
                    },
                    telemetry_snapshot=dict(snapshot),
                )
            )

        # ── Prolonged phone usage ───────────────────────────────────────
        if "phone_detected" not in driver:
            skipped.append("prolonged_phone")
        else:
            if bool(driver.get("phone_detected", False)):
                self._phone_frames += 1
            else:
                self._phone_frames = 0
            phone_seconds = self._phone_frames / self.fps
            if phone_seconds > PROLONGED_PHONE_SECONDS:
                events.append(
                    SafetyEvent(
                        event_type="PROLONGED_PHONE_USAGE",
                        severity="HIGH",
                        reason=(
                            f"Prolonged phone usage: {phone_seconds:.1f}s "
                            f"(threshold {PROLONGED_PHONE_SECONDS:.1f}s)"
                        ),
                        evidence={
                            "duration_s": round(phone_seconds, 2),
                            "threshold_s": PROLONGED_PHONE_SECONDS,
                            "consecutive_frames": self._phone_frames,
                            "fps": self.fps,
                        },
                        telemetry_snapshot=dict(snapshot),
                    )
                )

        # ── Sudden hard braking ─────────────────────────────────────────
        if speed_kmh is None:
            skipped.append("hard_braking")
        else:
            decel = self._longitudinal_decel_kmh_per_s(speed_kmh, evaluated_at)
            self._prev_speed_kmh = speed_kmh
            self._prev_timestamp = evaluated_at
            if decel is not None and decel < HARD_BRAKING_DECEL_KMH_PER_S:
                events.append(
                    SafetyEvent(
                        event_type="SUDDEN_HARD_BRAKING",
                        severity="MEDIUM",
                        reason=(
                            f"Sudden hard braking: {decel:.1f} km/h/s "
                            f"(threshold {HARD_BRAKING_DECEL_KMH_PER_S:.1f})"
                        ),
                        evidence={
                            "deceleration_kmh_per_s": round(decel, 2),
                            "threshold_kmh_per_s": HARD_BRAKING_DECEL_KMH_PER_S,
                            "speed_kmh": speed_kmh,
                        },
                        telemetry_snapshot=dict(snapshot),
                    )
                )

        # ── Pedestrian proximity hazard ─────────────────────────────────
        pedestrian = _nearest_closing_pedestrian(road)
        if pedestrian is None:
            skipped.append("pedestrian_proximity")
        else:
            events.append(
                SafetyEvent(
                    event_type="PEDESTRIAN_PROXIMITY_HAZARD",
                    severity="HIGH",
                    reason=(
                        f"Pedestrian proximity hazard: "
                        f"{pedestrian['distance_m']:.1f} m with closing motion"
                    ),
                    evidence=pedestrian,
                    telemetry_snapshot=dict(snapshot),
                )
            )

        return EventDetectionResult(
            vehicle_id=identity,
            events=tuple(events),
            timestamp=evaluated_at,
            warnings=tuple(warnings),
            skipped_detectors=tuple(skipped),
        )

    def _longitudinal_decel_kmh_per_s(
        self,
        speed_kmh: float,
        timestamp: datetime,
    ) -> float | None:
        if self._prev_speed_kmh is None or self._prev_timestamp is None:
            return None
        dt = (timestamp - self._prev_timestamp).total_seconds()
        if dt <= 0.0:
            dt = 1.0 / self.fps
        return (speed_kmh - self._prev_speed_kmh) / dt


def detect_events(
    vehicle_id: str,
    driver_state: Mapping[str, Any] | None = None,
    road_state: Mapping[str, Any] | None = None,
    telemetry: Mapping[str, Any] | None = None,
    *,
    detector: EventDetector | None = None,
    risk_score: float | None = None,
    timestamp: datetime | None = None,
) -> EventDetectionResult:
    """Convenience wrapper around a shared or ephemeral :class:`EventDetector`."""
    instance = detector or EventDetector()
    return instance.process_frame(
        vehicle_id,
        driver_state,
        road_state,
        telemetry,
        risk_score=risk_score,
        timestamp=timestamp,
    )


def _vehicle_ttc_targets(road_state: Mapping[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for item in _road_objects(road_state):
        if not _track_confirmed(item):
            continue
        obj_class = _object_class(item)
        if obj_class not in _VEHICLE_CLASSES:
            continue
        distance = _object_distance(item)
        relative_speed = _relative_speed(item)
        if distance is None or relative_speed is None:
            continue
        ttc = compute_ttc_seconds(distance, relative_speed)
        if ttc is None:
            continue
        targets.append(
            {
                "track_id": item.get("track_id", item.get("id")),
                "object_class": obj_class,
                "distance_m": distance,
                "relative_speed_kmh": relative_speed,
                "ttc_seconds": ttc,
            }
        )
    return targets


def _nearest_closing_pedestrian(
    road_state: Mapping[str, Any],
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for item in _road_objects(road_state):
        if _object_class(item) != "pedestrian":
            continue
        if not (_track_confirmed(item) or bool(item.get("temporally_confirmed", False))):
            continue
        distance = _object_distance(item)
        if distance is None or distance >= PEDESTRIAN_HAZARD_DISTANCE_M:
            continue
        relative_speed = _relative_speed(item)
        if relative_speed is None or relative_speed < MIN_CLOSING_SPEED_KMH:
            continue
        candidates.append(
            {
                "track_id": item.get("track_id", item.get("id")),
                "distance_m": distance,
                "relative_speed_kmh": relative_speed,
                "threshold_m": PEDESTRIAN_HAZARD_DISTANCE_M,
                "temporally_confirmed": bool(item.get("temporally_confirmed", False)),
            }
        )
    if not candidates:
        return None
    return min(candidates, key=lambda item: item["distance_m"])


def _build_telemetry_snapshot(
    driver: Mapping[str, Any],
    road: Mapping[str, Any],
    telemetry: Mapping[str, Any],
    risk_score: float | None,
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    speed = _optional_non_negative_float(
        telemetry.get("speed_kmh", telemetry.get("Vehicle.Speed"))
    )
    if speed is not None:
        snapshot["speed_kmh"] = speed
    ear = _optional_float(driver.get("ear_value"))
    if ear is not None:
        snapshot["driver_ear"] = ear
    if risk_score is not None:
        snapshot["risk_score_at_event"] = round(
            max(0.0, min(100.0, float(risk_score))), 1
        )
    lat = _optional_float(
        telemetry.get("latitude", telemetry.get("Vehicle.CurrentLocation.Latitude"))
    )
    lon = _optional_float(
        telemetry.get("longitude", telemetry.get("Vehicle.CurrentLocation.Longitude"))
    )
    if lat is not None:
        snapshot["latitude"] = lat
    if lon is not None:
        snapshot["longitude"] = lon
    if "frame_id" in road:
        snapshot["frame_id"] = road["frame_id"]
    return snapshot


def _drowsy_frame_count(driver: Mapping[str, Any]) -> int | None:
    if "consecutive_drowsy_frames" in driver:
        value = driver.get("consecutive_drowsy_frames")
        if isinstance(value, bool) or value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return max(0, parsed)
    if "is_drowsy" in driver:
        return 1 if bool(driver.get("is_drowsy")) else 0
    return None


def _road_objects(road_state: Mapping[str, Any]) -> Sequence[Mapping[str, Any]]:
    raw = road_state.get("objects", ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return ()
    return tuple(item for item in raw if isinstance(item, Mapping))


def _track_confirmed(item: Mapping[str, Any]) -> bool:
    if "confirmed" in item:
        return bool(item.get("confirmed"))
    # Legacy / sparse contracts may omit confirmation; require distance instead.
    return _object_distance(item) is not None


def _object_class(item: Mapping[str, Any]) -> str:
    return str(item.get("class", item.get("class_name", ""))).strip().lower()


def _object_distance(item: Mapping[str, Any]) -> float | None:
    return _optional_non_negative_float(item.get("distance_m"))


def _relative_speed(item: Mapping[str, Any]) -> float | None:
    value = item.get(
        "relative_speed_kmh",
        item.get("closing_speed_kmh", item.get("estimated_relative_speed_kmh")),
    )
    return _optional_non_negative_float(value)


def _optional_non_negative_float(value: Any) -> float | None:
    parsed = _optional_float(value)
    return parsed if parsed is not None and parsed >= 0.0 else None


def _optional_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _finite_float(value: Any, name: str) -> float:
    parsed = _optional_float(value)
    if parsed is None:
        raise ValueError(f"{name} must be a finite number")
    return parsed
