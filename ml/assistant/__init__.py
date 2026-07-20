"""LangGraph RAG assistant — Phase 5."""

from ml.assistant.agent import AssistantState, ask_assistant, assistant_graph, build_assistant_graph
from ml.assistant.config import COLLECTION_NAME, DEFAULT_PERSIST_DIR, EMBEDDING_MODEL
from ml.assistant.context import format_maintenance_context, format_telemetry_context
from ml.assistant.knowledge_base import (
    BuildResult,
    build_knowledge_base,
    collection_stats,
    default_document_paths,
    search_knowledge,
)
from ml.assistant.llm import OllamaClient, get_default_client
from ml.assistant.retriever import (
    RetrievalResult,
    classify_intent,
    retrieve,
    retrieve_for_prompt,
)

__all__ = [
    "AssistantState",
    "BuildResult",
    "COLLECTION_NAME",
    "DEFAULT_PERSIST_DIR",
    "EMBEDDING_MODEL",
    "OllamaClient",
    "RetrievalResult",
    "ask_assistant",
    "assistant_graph",
    "build_assistant_graph",
    "build_knowledge_base",
    "classify_intent",
    "collection_stats",
    "default_document_paths",
    "format_maintenance_context",
    "format_telemetry_context",
    "get_default_client",
    "retrieve",
    "retrieve_for_prompt",
    "search_knowledge",
]
