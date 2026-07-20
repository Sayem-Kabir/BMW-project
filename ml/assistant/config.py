"""Module 5A — RAG knowledge base configuration."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_PERSIST_DIR = REPO_ROOT / "chroma_db"

COLLECTION_NAME = "vehicle_knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

DEFAULT_DOCUMENTS: tuple[Path, ...] = (
    DEFAULT_DATA_DIR / "bmw_owner_manual.txt",
    DEFAULT_DATA_DIR / "obd2_codes.txt",
    DEFAULT_DATA_DIR / "service_intervals.txt",
)

# Optional PDF when present locally (not committed — large file).
OPTIONAL_PDF = DEFAULT_DATA_DIR / "bmw_owner_manual.pdf"

DEFAULT_CHROMA_HOST = "localhost"
DEFAULT_CHROMA_PORT = 8001

# Module 5B — retrieval defaults
DEFAULT_TOP_K = 4
MAX_CONTEXT_CHARS = 3500
DISTANCE_SOFT_LIMIT = 1.35
