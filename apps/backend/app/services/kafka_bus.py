"""Kafka/Redpanda producer stub — Spec Section 19.3."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# In-memory fallback when Redpanda is not running
_BUFFER: list[dict[str, Any]] = []


def publish(topic: str, payload: dict[str, Any], *, bootstrap: str | None = None) -> dict[str, Any]:
    """Publish JSON event. Tries kafka-python if available + broker up; else buffers."""
    entry = {"topic": topic, "payload": payload}
    brokers = bootstrap or "localhost:19092"
    try:
        from kafka import KafkaProducer  # type: ignore

        producer = KafkaProducer(
            bootstrap_servers=brokers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=2000,
        )
        fut = producer.send(topic, payload)
        fut.get(timeout=2)
        producer.close()
        return {"ok": True, "mode": "kafka", "topic": topic, "phase": "19.3"}
    except Exception as exc:  # noqa: BLE001
        _BUFFER.append(entry)
        if len(_BUFFER) > 500:
            del _BUFFER[:-500]
        logger.debug("Kafka unavailable (%s) — buffered %s", exc, topic)
        return {
            "ok": True,
            "mode": "buffer",
            "topic": topic,
            "buffered": len(_BUFFER),
            "phase": "19.3",
        }


def drain_buffer() -> list[dict[str, Any]]:
    items = list(_BUFFER)
    _BUFFER.clear()
    return items
