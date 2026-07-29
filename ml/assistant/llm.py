"""Module 5C — Ollama LLM client for the vehicle assistant.

Uses the Ollama HTTP API directly (no LangChain dependency required).
Falls back to a deterministic stub when Ollama is unavailable so tests and
local demos still exercise the RAG + telemetry pipeline.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

PHASE = "5C"
DEFAULT_OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = "llama3.2:3b"

GenerateFn = Callable[[str], str]


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    backend: str
    phase: str = PHASE

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "backend": self.backend,
            "phase": self.phase,
        }


class OllamaClient:
    """Thin client around ``POST /api/generate``."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_OLLAMA_BASE_URL,
        model: str = DEFAULT_OLLAMA_MODEL,
        timeout_seconds: float = 120.0,
        generate_fn: GenerateFn | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._generate_fn = generate_fn

    def available(self) -> bool:
        if self._generate_fn is not None:
            return True
        try:
            with urllib.request.urlopen(
                f"{self.base_url}/api/tags",
                timeout=min(5.0, self.timeout_seconds),
            ) as response:
                return response.status == 200
        except Exception:  # noqa: BLE001
            return False

    def generate(self, prompt: str) -> LLMResult:
        if self._generate_fn is not None:
            return LLMResult(
                text=self._generate_fn(prompt).strip(),
                model=self.model,
                backend="injected",
            )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 150},
        }
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Ollama unavailable at {self.base_url}: {exc}. "
                "Start it with `ollama serve` and pull `llama3.2:3b`."
            ) from exc

        text = str(body.get("response") or "").strip()
        if not text:
            raise RuntimeError("Ollama returned an empty response")
        return LLMResult(text=text, model=str(body.get("model") or self.model), backend="ollama")


def _section_after(prompt: str, start: str, *ends: str) -> str:
    if start not in prompt:
        return ""
    section = prompt.split(start, 1)[1]
    for end in ends:
        if end in section:
            section = section.split(end, 1)[0]
    return section.strip()


def _clean_manual_excerpt(section: str, *, max_chars: int = 520) -> str:
    """Pick useful RAG text; skip markdown titles / empty source headers."""
    lines: list[str] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line or line.lower() == "none":
            continue
        if line.startswith("[Source:"):
            # Keep content after "[Source: file] actual text..."
            if "]" in line:
                line = line.split("]", 1)[1].strip()
            if not line:
                continue
        if line.startswith("#"):
            line = line.lstrip("#").strip()
            if not line:
                continue
        lines.append(line)
    text = " ".join(lines)
    text = " ".join(text.split())
    if len(text) > max_chars:
        text = text[: max_chars - 1].rstrip() + "…"
    return text


def _telemetry_summary(section: str) -> str:
    if not section or "unavailable" in section.lower():
        return ""
    low_tires: list[str] = []
    for token in ("FL=", "FR=", "RL=", "RR="):
        if token not in section:
            continue
        try:
            value = float(section.split(token, 1)[1].split()[0].rstrip(","))
        except (IndexError, ValueError):
            continue
        corner = token.rstrip("=")
        if value < 28.0:
            low_tires.append(f"{corner}={value:g} PSI")
    bits: list[str] = []
    if low_tires:
        bits.append(
            "Demo/live tire pressures show under-inflation on "
            + ", ".join(low_tires)
            + " (typical cold target is often near 32–35 PSI — confirm the door-jamb label)."
        )
    elif "Tire Pressures:" in section:
        pressures = section.split("Tire Pressures:", 1)[1].splitlines()[0].strip()
        bits.append(f"Current tire pressures: {pressures}")
    return " ".join(bits)


def _maintenance_summary(section: str) -> str:
    if not section or "unavailable" in section.lower():
        return ""
    critical: list[str] = []
    for line in section.splitlines():
        lowered = line.lower()
        if "severity=critical" in lowered or "severity=high" in lowered:
            name = line.strip(" -").split(":", 1)[0].strip()
            if name:
                critical.append(name)
    if critical:
        return (
            "Predictive maintenance flags elevated risk for: "
            + ", ".join(critical)
            + "."
        )
    return ""


def fallback_generate(prompt: str) -> str:
    """Deterministic offline answer used when Ollama is not running.

    Builds a useful reply from retrieved manual/OBD context plus telemetry and
    maintenance sections already injected into the prompt.
    """
    question = _section_after(prompt, "Driver question:", "Assistant:") or prompt.strip()
    manual = _clean_manual_excerpt(
        _section_after(
            prompt,
            "Vehicle Manual Context:",
            "Current vehicle sensor readings:",
            "Live telemetry",
            "Latest predictive maintenance",
            "Prior conversation",
            "Driver question:",
        )
    )
    telemetry = _telemetry_summary(
        _section_after(
            prompt,
            "Current vehicle sensor readings:",
            "Latest predictive maintenance",
            "Prior conversation",
            "Driver question:",
        )
    )
    if not telemetry:
        # Some prompts use a non-sensor telemetry placeholder line.
        telemetry_block = _section_after(
            prompt,
            "Live telemetry",
            "Latest predictive maintenance",
            "Prior conversation",
            "Driver question:",
        )
        if "Current vehicle sensor readings:" in telemetry_block:
            telemetry = _telemetry_summary(
                telemetry_block.split("Current vehicle sensor readings:", 1)[1]
            )

    maintenance = _maintenance_summary(
        _section_after(
            prompt,
            "Latest predictive maintenance status for this vehicle:",
            "Prior conversation",
            "Driver question:",
        )
    )

    parts: list[str] = []
    if manual:
        parts.append(manual)
    else:
        parts.append(
            f'I can help with BMW vehicle questions. You asked: "{question}". '
            "No matching manual/OBD context was retrieved."
        )

    if telemetry:
        parts.append(telemetry)
    if maintenance:
        parts.append(maintenance)

    parts.append(
        "If a safety warning persists after correcting pressures or clearing codes, "
        "visit an authorized BMW service center."
    )
    parts.append("(Offline fallback — start Ollama with `ollama serve` and `ollama pull llama3.2:3b` for full LLM answers.)")
    return " ".join(parts)


def get_default_client(
    *,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    model: str = DEFAULT_OLLAMA_MODEL,
    allow_fallback: bool = True,
) -> OllamaClient:
    client = OllamaClient(base_url=base_url, model=model)
    if allow_fallback and not client.available():
        logger.warning("Ollama not reachable at %s — using offline fallback generator", base_url)
        return OllamaClient(
            base_url=base_url,
            model=model,
            generate_fn=fallback_generate,
        )
    return client
