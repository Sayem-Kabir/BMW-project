"""Demo Module 5B RAG retrieval (no LLM).

Usage:

    python scripts/demo_rag_retrieval.py
    python scripts/demo_rag_retrieval.py "What does P0420 mean?"
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.assistant.knowledge_base import collection_stats
from ml.assistant.retriever import retrieve


DEMO_QUERIES = (
    "Why is my tire pressure warning light on?",
    "When should I schedule brake fluid service?",
    "What does P0420 mean on my BMW?",
    "How does regenerative braking work?",
)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    queries = args or list(DEMO_QUERIES)

    stats = collection_stats()
    if not stats.get("available"):
        print(
            "Knowledge base is empty. Run first:\n"
            "  python scripts/build_knowledge_base.py --reset",
            file=sys.stderr,
        )
        return 1

    print(f"Index ready: {stats['count']} chunks via {stats.get('backend')}")
    print("=" * 72)

    for query in queries:
        result = retrieve(query, k=3)
        print(f"\nQ: {query}")
        print(f"  intent={result.intent}  route={result.route}")
        print(f"  citations={list(result.citations)}")
        if result.obd_matches:
            print(f"  obd={[m['code'] for m in result.obd_matches]}")
        if result.warnings:
            print(f"  warnings={list(result.warnings)}")
        preview = result.context[:400].replace("\n", " ")
        print(f"  context: {preview}{'...' if len(result.context) > 400 else ''}")

    if len(queries) == 1:
        print("\n" + json.dumps(retrieve(queries[0]).to_dict(), indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
