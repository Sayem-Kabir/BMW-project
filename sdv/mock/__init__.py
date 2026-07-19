"""Synthetic VSS signal simulator for demos."""

from typing import Any

__all__ = [
    "DEFAULT_VEHICLE_ID",
    "SensorSimulator",
    "publish_to_kuksa",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    from sdv.mock import sensor_simulator

    return getattr(sensor_simulator, name)
