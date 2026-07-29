"""RAGAS-inspired faithfulness/retrieval eval — Spec Phase 11D (no heavy RAGAS dep)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


def _eval_path() -> Path:
    here = Path(__file__).resolve()
    return here.parents[4] / "ml" / "assistant" / "eval" / "ragas_eval_set.json"


def load_eval_set() -> dict[str, Any]:
    path = _eval_path()
    if not path.exists():
        path = Path("ml/assistant/eval/ragas_eval_set.json")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def score_reply(case: dict[str, Any], reply: str) -> dict[str, Any]:
    text = (reply or "").lower()
    must_any = [s.lower() for s in case.get("must_include_any") or []]
    must_not = [s.lower() for s in case.get("must_not_include") or []]
    hit = any(s in text for s in must_any) if must_any else True
    bad = any(s in text for s in must_not)
    if case.get("expect_refusal"):
        faithful = hit and not bad
    else:
        faithful = hit and not bad
    return {
        "id": case.get("id"),
        "faithful": faithful,
        "hit_required": hit,
        "violated_forbidden": bad,
    }


async def run_eval(
    answer_fn: Callable[[str], Awaitable[str]],
) -> dict[str, Any]:
    """Run eval set through an async answer function (question → reply text)."""
    data = load_eval_set()
    cases = list(data.get("cases") or [])
    rows: list[dict[str, Any]] = []
    for case in cases:
        q = str(case.get("question") or "")
        try:
            reply = await answer_fn(q)
        except Exception as exc:  # noqa: BLE001
            rows.append({"id": case.get("id"), "faithful": False, "error": str(exc)})
            continue
        row = score_reply(case, reply)
        row["reply_preview"] = (reply or "")[:160]
        rows.append(row)

    n = len(rows) or 1
    faithful = sum(1 for r in rows if r.get("faithful"))
    score = faithful / n
    return {
        "score": round(score, 4),
        "faithful_count": faithful,
        "total": len(rows),
        "pass": score >= 0.75,
        "cases": rows,
        "phase": "11D",
    }
