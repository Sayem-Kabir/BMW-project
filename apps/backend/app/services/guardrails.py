"""LLM input/output guardrails — Spec Phase 11D."""

from __future__ import annotations

import re
from typing import Any

# Refuse jailbreaks / unsafe vehicle advice / out-of-scope
_BLOCKED_INPUT = [
    re.compile(p, re.I)
    for p in (
        r"ignore (all |previous )?instructions",
        r"jailbreak",
        r"how to (disable|bypass) (airbag|abs|esp|traction)",
        r"remove seatbelt interlock",
        r"hack (the )?(ecu|can bus|obd)",
        r"make (the )?car (go )?faster than (limiter|governor)",
    )
]

_BLOCKED_OUTPUT = [
    re.compile(p, re.I)
    for p in (
        r"disable (your )?airbags?",
        r"bypass (the )?(abs|esp)",
        r"ignore (the )?seatbelt",
        r"cut the brake",
    )
]

_OUT_OF_SCOPE = [
    re.compile(p, re.I)
    for p in (
        r"\b(bitcoin|crypto|stock tip|medical diagnosis|prescribe)\b",
        r"write (me )?(malware|ransomware)",
    )
]

REFUSAL = (
    "I can only help with BMW vehicle operation, maintenance, OBD codes, "
    "and safety guidance from the owner documentation. I can't assist with "
    "that request."
)


def check_input(message: str) -> dict[str, Any] | None:
    text = (message or "").strip()
    if not text:
        return {"blocked": True, "reason": "empty", "reply": "Please ask a vehicle-related question."}
    for rx in _BLOCKED_INPUT + _OUT_OF_SCOPE:
        if rx.search(text):
            return {"blocked": True, "reason": "policy", "reply": REFUSAL, "pattern": rx.pattern}
    return None


def filter_output(reply: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    text = reply or ""
    for rx in _BLOCKED_OUTPUT:
        if rx.search(text):
            warnings.append(f"output_blocked:{rx.pattern}")
            return REFUSAL, warnings
    return text, warnings
