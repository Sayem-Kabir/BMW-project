"""Demo Module 5C — RAG + telemetry + Ollama assistant.

Usage:

    # Ensure knowledge base exists
    python scripts/build_knowledge_base.py --reset

    # Optional: start Ollama and pull the model
    #   ollama serve
    #   ollama pull llama3.2:3b

    python scripts/demo_assistant_5c.py
    python scripts/demo_assistant_5c.py "Why is my tire pressure warning on?"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.assistant.agent import ask_assistant
from ml.assistant.knowledge_base import collection_stats
from ml.assistant.llm import OllamaClient


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    query = args[0] if args else "Why is my tire pressure warning light on?"

    stats = collection_stats()
    if not stats.get("available"):
        print(
            "Knowledge base empty. Run:\n  python scripts/build_knowledge_base.py --reset",
            file=sys.stderr,
        )
        return 1

    ollama = OllamaClient()
    print(f"Index: {stats['count']} chunks ({stats.get('backend')})")
    print(f"Ollama: {'available' if ollama.available() else 'offline fallback'}")
    print("=" * 72)
    print(f"Q: {query}")

    state = ask_assistant(query, allow_fallback_llm=True)
    print(f"intent={state.intent}  route={state.route}")
    print(f"citations={state.citations}")
    print(f"llm={state.llm_model} ({state.llm_backend})")
    print("-" * 72)
    print(state.final_response)
    print("-" * 72)
    if "--json" in args:
        print(json.dumps(state.to_dict(), indent=2)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
