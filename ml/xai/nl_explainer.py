"""Module 6G — natural-language XAI composer (template-first, Ollama optional)."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


PHASE = "6G"


def compose_nl_explanation(
    *,
    event_type: str,
    evidence: Sequence[str] | None = None,
    visual_description: str | None = None,
    shap_top: Sequence[Mapping[str, Any]] | None = None,
    vehicle_state: Mapping[str, Any] | None = None,
    action: str | None = None,
) -> str:
    lines = [f"{event_type.replace('_', ' ').title()} explanation:"]

    if evidence:
        for item in evidence[:5]:
            lines.append(f"• {item}")

    if shap_top:
        bits = []
        for item in list(shap_top)[:3]:
            name = item.get("feature") or item.get("name") or "feature"
            impact = item.get("impact") or item.get("contribution")
            direction = item.get("direction") or ""
            if impact is not None:
                bits.append(f"{name} ({direction} {float(impact):+.3f})".strip())
            else:
                bits.append(str(name))
        if bits:
            lines.append("• Top model contributions: " + ", ".join(bits))

    if visual_description:
        lines.append(f"• Visual evidence: {visual_description}")

    if vehicle_state:
        speed = vehicle_state.get("speed_kmh")
        if speed is not None:
            lines.append(f"• Vehicle state: speed≈{speed} km/h")

    lines.append(
        action
        or "Action: Review the evidence, reduce risk if safe to do so, and seek authorized BMW service when a safety-critical warning persists."
    )
    return "\n".join(lines)


def shap_waterfall_ascii(top_features: Sequence[Mapping[str, Any]]) -> str:
    """Lightweight text 'plot' when matplotlib SHAP waterfall is unavailable."""
    if not top_features:
        return "No SHAP contributions available."
    lines = ["SHAP feature contributions (top-k):"]
    for item in top_features:
        name = str(item.get("feature") or item.get("name") or "?")
        value = item.get("contribution", item.get("impact", 0.0))
        direction = str(item.get("direction") or "")
        bar = "#" * min(20, max(1, int(abs(float(value)) * 40)))
        sign = "+" if float(value) >= 0 else "-"
        lines.append(f"  {name:24s} {sign}{bar} ({float(value):+.4f}) {direction}")
    return "\n".join(lines)
