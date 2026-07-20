"""Module 5G conversation memory helpers."""

from __future__ import annotations

from ml.assistant.memory import (
    format_conversation_memory,
    memory_summary,
    normalize_messages,
    trim_messages,
)


def test_normalize_messages_filters_roles() -> None:
    cleaned = normalize_messages(
        [
            {"role": "user", "content": "Why is TPMS on?"},
            {"role": "system", "content": "ignore"},
            {"role": "assistant", "content": "Check tire pressure."},
            {"role": "user", "content": "  "},
        ]
    )
    assert cleaned == [
        {"role": "user", "content": "Why is TPMS on?"},
        {"role": "assistant", "content": "Check tire pressure."},
    ]


def test_trim_messages_keeps_tail() -> None:
    rows = [{"role": "user", "content": f"q{i}"} for i in range(6)]
    trimmed = trim_messages(rows, max_messages=3)
    assert [item["content"] for item in trimmed] == ["q3", "q4", "q5"]


def test_format_conversation_memory() -> None:
    text = format_conversation_memory(
        [
            {"role": "user", "content": "What is P0420?"},
            {"role": "assistant", "content": "Catalyst efficiency code."},
            {"role": "user", "content": "Is it urgent?"},
        ]
    )
    assert "Prior conversation" in text
    assert "Driver: What is P0420?" in text
    assert "Assistant: Catalyst efficiency code." in text
    assert "Driver: Is it urgent?" in text


def test_memory_summary_empty() -> None:
    summary = memory_summary([])
    assert summary["has_memory"] is False
    assert summary["used_messages"] == 0
    assert summary["phase"] == "5G"
