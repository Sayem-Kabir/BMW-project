"""Assistant semantic cache — Spec Phase 13 (embedding similarity, in-memory)."""

from __future__ import annotations

import hashlib
import math
import re
import time
from dataclasses import dataclass
from typing import Any


_TOKEN = re.compile(r"[a-z0-9]+", re.I)


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def bag_of_words_vector(text: str, vocab: dict[str, int] | None = None) -> tuple[dict[str, float], dict[str, int]]:
    """Sparse TF vector; grows vocab in-place when provided."""
    tokens = _tokenize(text)
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    if vocab is None:
        vocab = {}
    for t in counts:
        if t not in vocab:
            vocab[t] = len(vocab)
    total = float(sum(counts.values()) or 1)
    vec = {t: c / total for t, c in counts.items()}
    return vec, vocab


def cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass
class _Entry:
    text: str
    vec: dict[str, float]
    answer: dict[str, Any]
    created: float


class SemanticCache:
    """In-process similarity cache for common assistant questions."""

    def __init__(self, *, threshold: float = 0.92, ttl_sec: float = 300, max_entries: int = 128) -> None:
        self.threshold = threshold
        self.ttl_sec = ttl_sec
        self.max_entries = max_entries
        self._entries: list[_Entry] = []
        self.hits = 0
        self.misses = 0

    def clear(self) -> None:
        self._entries.clear()
        self.hits = 0
        self.misses = 0

    def lookup(self, question: str) -> dict[str, Any] | None:
        now = time.monotonic()
        self._entries = [e for e in self._entries if now - e.created <= self.ttl_sec]
        qvec, _ = bag_of_words_vector(question)
        best: tuple[float, _Entry] | None = None
        for entry in self._entries:
            sim = cosine_sparse(qvec, entry.vec)
            if best is None or sim > best[0]:
                best = (sim, entry)
        if best and best[0] >= self.threshold:
            self.hits += 1
            payload = dict(best[1].answer)
            payload["semantic_cache"] = {
                "hit": True,
                "similarity": round(best[0], 4),
                "phase": "13",
            }
            return payload
        self.misses += 1
        return None

    def store(self, question: str, answer: dict[str, Any]) -> None:
        vec, _ = bag_of_words_vector(question)
        self._entries.append(
            _Entry(text=question, vec=vec, answer=dict(answer), created=time.monotonic())
        )
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries :]


_GLOBAL = SemanticCache()


def get_cache(*, threshold: float | None = None, ttl_sec: float | None = None) -> SemanticCache:
    if threshold is not None:
        _GLOBAL.threshold = threshold
    if ttl_sec is not None:
        _GLOBAL.ttl_sec = ttl_sec
    return _GLOBAL


def cache_key(question: str) -> str:
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()[:16]
