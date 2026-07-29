"""Feast-style feature store stub — Spec Section 19.3 (training/serving parity)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STORE_PATH = Path(__file__).resolve().parent / "feature_store.json"


def _load() -> dict[str, Any]:
    if STORE_PATH.is_file():
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    return {"entities": {}, "phase": "19.3"}


def _save(data: dict[str, Any]) -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def write_features(entity_id: str, features: dict[str, Any]) -> dict[str, Any]:
    data = _load()
    data.setdefault("entities", {})[entity_id] = dict(features)
    _save(data)
    return {"entity_id": entity_id, "features": features, "phase": "19.3"}


def read_features(entity_id: str) -> dict[str, Any] | None:
    data = _load()
    feats = data.get("entities", {}).get(entity_id)
    if feats is None:
        return None
    return {"entity_id": entity_id, "features": feats, "phase": "19.3"}


def list_entities() -> list[str]:
    return list(_load().get("entities", {}).keys())
