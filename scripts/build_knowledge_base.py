"""Build the Module 5A RAG knowledge base (ChromaDB index).

Usage:

    pip install -r apps/backend/requirements-rag.txt
    python scripts/build_knowledge_base.py

Optional — index into the Docker Chroma server instead of local ``chroma_db/``:

    python scripts/build_knowledge_base.py --http --reset
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.assistant.config import DEFAULT_DATA_DIR, DEFAULT_PERSIST_DIR
from ml.assistant.knowledge_base import build_knowledge_base, collection_stats, default_document_paths


def main() -> int:
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Build BMW AI vehicle knowledge base (Phase 5A)")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--persist-dir", type=Path, default=DEFAULT_PERSIST_DIR)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--http", action="store_true")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    doc_paths = default_document_paths()
    if not doc_paths:
        print(f"No documents found under {args.data_dir}", file=sys.stderr)
        return 1

    result = build_knowledge_base(
        doc_paths,
        persist_directory=args.persist_dir,
        use_http=args.http,
        chroma_host=args.host,
        chroma_port=args.port,
        reset=args.reset,
    )
    stats = collection_stats(
        persist_directory=args.persist_dir,
        use_http=args.http,
        chroma_host=args.host,
        chroma_port=args.port,
    )
    print(json.dumps({"build": result.to_dict(), "stats": stats}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
