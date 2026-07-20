"""Module 5C–5G — LangGraph-style vehicle assistant agent.

Wires Module 5B retrieval + Kuksa telemetry + predictive-maintenance state
+ multi-turn conversation memory into an Ollama LLM response.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping, Sequence

from ml.assistant.context import (
    demo_maintenance_snapshot,
    format_maintenance_context,
    format_telemetry_context,
    should_inject_maintenance,
    should_inject_telemetry,
)
from ml.assistant.llm import (
    OllamaClient,
    get_default_client,
)
from ml.assistant.memory import format_conversation_memory, memory_summary
from ml.assistant.retriever import (
    INTENT_GENERAL,
    ROUTE_DIRECT,
    ROUTE_RAG_TELEMETRY,
    classify_intent,
    retrieve,
    route_for_intent,
)

logger = logging.getLogger(__name__)

PHASE = "5G"
DEFAULT_VEHICLE_ID = "00000000-0000-4000-8000-000000000003"

TelemetryFn = Callable[[str], Mapping[str, Any] | None]
MaintenanceFn = Callable[[str], Sequence[Mapping[str, Any]] | None]


@dataclass
class AssistantState:
    user_query: str
    vehicle_id: str = DEFAULT_VEHICLE_ID
    intent: str = INTENT_GENERAL
    route: str = ROUTE_DIRECT
    retrieved_context: str = ""
    citations: list[str] = field(default_factory=list)
    obd_matches: list[dict[str, str]] = field(default_factory=list)
    telemetry_context: str = ""
    maintenance_context: str = ""
    conversation_memory: str = ""
    memory_message_count: int = 0
    final_response: str = ""
    warnings: list[str] = field(default_factory=list)
    llm_backend: str = ""
    llm_model: str = ""
    phase: str = PHASE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _demo_telemetry(vehicle_id: str) -> dict[str, Any]:
    """Demo snapshot used when Kuksa is unavailable (matches Module 07 example)."""
    return {
        "vehicle_id": vehicle_id,
        "speed_kmh": 48.0,
        "tire_fl": 32.0,
        "tire_fr": 34.0,
        "tire_rl": 22.0,
        "tire_rr": 33.0,
        "battery_soc": 64.0,
        "oil_temp": None,
    }


def classify_intent_node(state: AssistantState) -> AssistantState:
    intent = classify_intent(state.user_query)
    route = route_for_intent(intent)
    state.intent = intent
    state.route = route
    return state


def rag_retriever_node(
    state: AssistantState,
    *,
    retrieve_kwargs: Mapping[str, Any] | None = None,
) -> AssistantState:
    result = retrieve(state.user_query, **dict(retrieve_kwargs or {}))
    state.intent = result.intent
    state.route = result.route
    state.retrieved_context = result.context
    state.citations = list(result.citations)
    state.obd_matches = [dict(item) for item in result.obd_matches]
    state.warnings.extend(result.warnings)
    return state


def telemetry_injector_node(
    state: AssistantState,
    *,
    telemetry_fn: TelemetryFn | None = None,
    use_demo_telemetry: bool = True,
) -> AssistantState:
    telemetry: Mapping[str, Any] | None = None
    if telemetry_fn is not None:
        try:
            telemetry = telemetry_fn(state.vehicle_id)
        except Exception as exc:  # noqa: BLE001
            state.warnings.append(f"Telemetry callback failed: {exc}")
    else:
        try:
            telemetry = asyncio.run(_fetch_kuksa_telemetry(state.vehicle_id))
        except Exception as exc:  # noqa: BLE001
            logger.info("Kuksa telemetry unavailable (%s)", exc)
            state.warnings.append("Live Kuksa telemetry unavailable")
            if use_demo_telemetry and should_inject_telemetry(state.intent, state.route):
                telemetry = _demo_telemetry(state.vehicle_id)
                state.warnings.append("Using demo telemetry snapshot")
    state.telemetry_context = format_telemetry_context(telemetry)
    return state


def maintenance_injector_node(
    state: AssistantState,
    *,
    maintenance_fn: MaintenanceFn | None = None,
    use_demo_maintenance: bool = True,
) -> AssistantState:
    predictions: Sequence[Mapping[str, Any]] | None = None
    if maintenance_fn is not None:
        try:
            predictions = maintenance_fn(state.vehicle_id)
        except Exception as exc:  # noqa: BLE001
            state.warnings.append(f"Maintenance callback failed: {exc}")
    elif use_demo_maintenance and should_inject_maintenance(state.intent, state.route):
        predictions = demo_maintenance_snapshot(state.vehicle_id)
        state.warnings.append("Using demo maintenance snapshot")

    state.maintenance_context = format_maintenance_context(predictions)
    return state


async def _fetch_kuksa_telemetry(vehicle_id: str) -> dict[str, Any]:
    from sdv.kuksa.signal_subscriber import get_current_telemetry

    return await get_current_telemetry(vehicle_id)


def memory_injector_node(
    state: AssistantState,
    *,
    prior_messages: Sequence[Mapping[str, Any]] | None = None,
) -> AssistantState:
    summary = memory_summary(prior_messages)
    state.conversation_memory = format_conversation_memory(prior_messages)
    state.memory_message_count = int(summary["used_messages"])
    if summary["has_memory"]:
        state.warnings.append(
            f"Using {summary['used_messages']} prior turn(s) as conversation memory"
        )
    return state


def build_prompt(state: AssistantState) -> str:
    manual = state.retrieved_context.strip() or "None"
    telemetry = state.telemetry_context.strip() or "Live telemetry unavailable."
    maintenance = state.maintenance_context.strip() or "Personalized maintenance history unavailable."
    memory = state.conversation_memory.strip() or "No prior conversation turns."
    citations = ", ".join(state.citations) if state.citations else "None"
    return f"""You are an intelligent automotive assistant for a BMW vehicle.
You have access to the vehicle's owner manual, OBD references, live sensor data, predictive maintenance status, and prior conversation turns.
Be helpful, precise, and safety-conscious. If the vehicle has a safety-critical issue, always recommend professional service.
Prefer citing the provided sources. Do not invent diagnostic codes, pressures, or health scores.
When maintenance scores are provided, use them to personalize service advice.
Use prior conversation turns for continuity, but prioritize the latest driver question.

Intent: {state.intent}
Citations: {citations}

Vehicle Manual Context:
{manual}

{telemetry}

{maintenance}

{memory}

Driver question: {state.user_query}

Assistant:"""


def response_generator_node(
    state: AssistantState,
    *,
    llm: OllamaClient | None = None,
) -> AssistantState:
    client = llm or get_default_client()
    prompt = build_prompt(state)
    result = client.generate(prompt)
    state.final_response = result.text
    state.llm_backend = result.backend
    state.llm_model = result.model
    return state


def build_assistant_graph(
    *,
    llm: OllamaClient | None = None,
    telemetry_fn: TelemetryFn | None = None,
    maintenance_fn: MaintenanceFn | None = None,
    use_demo_telemetry: bool = True,
    use_demo_maintenance: bool = True,
    retrieve_kwargs: Mapping[str, Any] | None = None,
    prior_messages: Sequence[Mapping[str, Any]] | None = None,
):
    """Return a simple compiled graph with ``.invoke(state_dict_or_state)``."""

    class _CompiledGraph:
        def invoke(self, payload: AssistantState | Mapping[str, Any]) -> AssistantState:
            if isinstance(payload, AssistantState):
                state = payload
            else:
                state = AssistantState(
                    user_query=str(payload.get("user_query") or ""),
                    vehicle_id=str(payload.get("vehicle_id") or DEFAULT_VEHICLE_ID),
                )
            if not state.user_query.strip():
                raise ValueError("user_query must not be empty")

            classify_intent_node(state)
            rag_retriever_node(state, retrieve_kwargs=retrieve_kwargs)
            memory_injector_node(state, prior_messages=prior_messages)

            if should_inject_telemetry(state.intent, state.route):
                telemetry_injector_node(
                    state,
                    telemetry_fn=telemetry_fn,
                    use_demo_telemetry=use_demo_telemetry,
                )
            elif not state.telemetry_context:
                state.telemetry_context = "Live telemetry not requested for this intent."

            if should_inject_maintenance(state.intent, state.route):
                maintenance_injector_node(
                    state,
                    maintenance_fn=maintenance_fn,
                    use_demo_maintenance=use_demo_maintenance,
                )
            elif not state.maintenance_context:
                state.maintenance_context = (
                    "Personalized maintenance history not requested for this intent."
                )

            response_generator_node(state, llm=llm)
            return state

    return _CompiledGraph()


# Default compiled graph for Module 07 import style.
assistant_graph = build_assistant_graph()


def ask_assistant(
    user_query: str,
    *,
    vehicle_id: str = DEFAULT_VEHICLE_ID,
    llm: OllamaClient | None = None,
    telemetry_fn: TelemetryFn | None = None,
    maintenance_fn: MaintenanceFn | None = None,
    use_demo_telemetry: bool = True,
    use_demo_maintenance: bool = True,
    retrieve_kwargs: Mapping[str, Any] | None = None,
    prior_messages: Sequence[Mapping[str, Any]] | None = None,
    allow_fallback_llm: bool = True,
) -> AssistantState:
    """One-shot assistant invocation used by demos and REST endpoints."""
    client = llm
    if client is None:
        client = get_default_client(allow_fallback=allow_fallback_llm)
    graph = build_assistant_graph(
        llm=client,
        telemetry_fn=telemetry_fn,
        maintenance_fn=maintenance_fn,
        use_demo_telemetry=use_demo_telemetry,
        use_demo_maintenance=use_demo_maintenance,
        retrieve_kwargs=retrieve_kwargs,
        prior_messages=prior_messages,
    )
    return graph.invoke({"user_query": user_query, "vehicle_id": vehicle_id})
