"""Module 5C assistant agent tests."""

from __future__ import annotations

from pathlib import Path

from ml.assistant.agent import (
    ask_assistant,
    build_assistant_graph,
    format_telemetry_context,
)
from ml.assistant.knowledge_base import build_knowledge_base, resolve_document_paths
from ml.assistant.llm import OllamaClient, fallback_generate
from ml.assistant.retriever import INTENT_VEHICLE_WARNING, ROUTE_RAG_TELEMETRY


def _fake_embed(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        lowered = text.lower()
        base = [0.0] * 8
        base[0] = float(sum(ord(c) for c in lowered) % 17)
        if "tpms" in lowered or "tire" in lowered or "pressure" in lowered:
            base[1] = 10.0
        if "p0420" in lowered or "catalyst" in lowered:
            base[2] = 10.0
        if "service" in lowered or "maintenance" in lowered:
            base[3] = 10.0
        vectors.append(base)
    return vectors


def test_format_telemetry_context() -> None:
    text = format_telemetry_context(
        {"speed_kmh": 48, "tire_rl": 22, "battery_soc": 64, "tire_fl": 32, "tire_fr": 34, "tire_rr": 33}
    )
    assert "RL=22" in text
    assert "Battery SoC: 64%" in text


def test_fallback_generate_mentions_context() -> None:
    prompt = (
        "Vehicle Manual Context:\n"
        "# BMW Owner Manual Excerpt\n"
        "If the TPMS warning appears: 1. Stop safely and check all four tire pressures.\n\n"
        "Current vehicle sensor readings:\n"
        "- Tire Pressures: FL=32.0 PSI, FR=34.0 PSI, RL=22.0 PSI, RR=33.0 PSI\n\n"
        "Latest predictive maintenance status for this vehicle:\n"
        "- brake: health=0.15 · severity=critical\n\n"
        "Driver question: Why is TPMS on?\n\nAssistant:"
    )
    answer = fallback_generate(prompt)
    assert "TPMS" in answer
    assert "RL=22" in answer
    assert "brake" in answer.lower()
    assert "Offline fallback" in answer
    assert "# BMW" not in answer


def test_ask_assistant_with_injected_llm(tmp_path: Path) -> None:
    paths = resolve_document_paths(None, include_optional_pdf=False)
    persist_dir = tmp_path / "chroma"
    build_knowledge_base(
        paths,
        persist_directory=persist_dir,
        reset=True,
        include_optional_pdf=False,
        embed_fn=_fake_embed,
    )

    llm = OllamaClient(
        model="test-model",
        generate_fn=lambda prompt: "Grounded answer about TPMS from the manual.",
    )
    state = ask_assistant(
        "Why is my tire pressure warning light on?",
        llm=llm,
        telemetry_fn=lambda _vid: {
            "speed_kmh": 40,
            "tire_fl": 32,
            "tire_fr": 34,
            "tire_rl": 22,
            "tire_rr": 33,
            "battery_soc": 70,
            "oil_temp": None,
        },
        maintenance_fn=lambda _vid: [
            {
                "component": "tire",
                "health_score": 0.55,
                "severity": "medium",
                "confidence": 0.8,
            }
        ],
        use_demo_maintenance=False,
        retrieve_kwargs={"persist_directory": persist_dir, "embed_fn": _fake_embed},
    )

    assert state.intent == INTENT_VEHICLE_WARNING
    assert state.route == ROUTE_RAG_TELEMETRY
    assert state.retrieved_context
    assert "RL=22" in state.telemetry_context
    assert "tire" in state.maintenance_context
    assert "health=0.55" in state.maintenance_context
    assert "Grounded answer" in state.final_response
    assert state.llm_backend == "injected"
    assert state.phase == "5G"


def test_ask_assistant_uses_conversation_memory(tmp_path: Path) -> None:
    paths = resolve_document_paths(None, include_optional_pdf=False)
    persist_dir = tmp_path / "chroma"
    build_knowledge_base(
        paths,
        persist_directory=persist_dir,
        reset=True,
        include_optional_pdf=False,
        embed_fn=_fake_embed,
    )

    captured: dict[str, str] = {}

    def _capture(prompt: str) -> str:
        captured["prompt"] = prompt
        return "Follow-up answer using prior context."

    llm = OllamaClient(model="test-model", generate_fn=_capture)
    state = ask_assistant(
        "Is that urgent?",
        llm=llm,
        telemetry_fn=lambda _vid: None,
        use_demo_telemetry=False,
        use_demo_maintenance=False,
        prior_messages=[
            {"role": "user", "content": "What does P0420 mean?"},
            {"role": "assistant", "content": "Catalyst efficiency below threshold."},
        ],
        retrieve_kwargs={"persist_directory": persist_dir, "embed_fn": _fake_embed},
    )

    assert state.memory_message_count == 2
    assert "Catalyst efficiency below threshold." in state.conversation_memory
    assert "Prior conversation" in captured["prompt"]
    assert "Is that urgent?" in captured["prompt"]
    assert any("prior turn" in warning.lower() for warning in state.warnings)


def test_graph_invoke_dict_payload(tmp_path: Path) -> None:
    paths = resolve_document_paths(None, include_optional_pdf=False)
    persist_dir = tmp_path / "chroma"
    build_knowledge_base(
        paths,
        persist_directory=persist_dir,
        reset=True,
        include_optional_pdf=False,
        embed_fn=_fake_embed,
    )
    graph = build_assistant_graph(
        llm=OllamaClient(generate_fn=lambda _p: "ok"),
        telemetry_fn=lambda _vid: None,
        use_demo_telemetry=False,
        retrieve_kwargs={"persist_directory": persist_dir, "embed_fn": _fake_embed},
    )
    state = graph.invoke({"user_query": "What does P0420 mean?"})
    assert state.final_response == "ok"
    assert state.obd_matches
