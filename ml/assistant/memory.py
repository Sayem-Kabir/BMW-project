"""Module 5G — multi-turn conversation memory helpers."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

PHASE = "5G"
DEFAULT_MEMORY_TURNS = 8  # user+assistant pairs counted as messages; keep last N messages


def normalize_messages(messages: Sequence[Mapping[str, Any]] | None) -> list[dict[str, str]]:
    """Keep only role/content pairs suitable for prompt memory."""
    cleaned: list[dict[str, str]] = []
    for item in messages or []:
        role = str(item.get("role") or "").strip().lower()
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        cleaned.append({"role": role, "content": content})
    return cleaned


def trim_messages(
    messages: Sequence[Mapping[str, str]],
    *,
    max_messages: int = DEFAULT_MEMORY_TURNS * 2,
) -> list[dict[str, str]]:
    """Keep the most recent messages within the memory window."""
    rows = list(messages)
    if max_messages <= 0:
        return []
    return rows[-max_messages:]


def format_conversation_memory(
    messages: Sequence[Mapping[str, Any]] | None,
    *,
    max_messages: int = DEFAULT_MEMORY_TURNS * 2,
) -> str:
    """Render prior turns for the LLM system prompt."""
    trimmed = trim_messages(normalize_messages(messages), max_messages=max_messages)
    if not trimmed:
        return "No prior conversation turns."

    lines = ["Prior conversation (most recent last):"]
    for item in trimmed:
        label = "Driver" if item["role"] == "user" else "Assistant"
        lines.append(f"{label}: {item['content']}")
    return "\n".join(lines)


def memory_summary(messages: Sequence[Mapping[str, Any]] | None) -> dict[str, Any]:
    normalized = normalize_messages(messages)
    trimmed = trim_messages(normalized)
    return {
        "total_messages": len(normalized),
        "used_messages": len(trimmed),
        "has_memory": bool(trimmed),
        "phase": PHASE,
    }
