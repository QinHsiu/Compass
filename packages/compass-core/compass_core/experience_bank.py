"""Local anonymized interview-experience bank (compas / clover-style 面经)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_BANK_PATH = Path(__file__).resolve().parent / "assets" / "questions" / "experience_bank.jsonl"


@lru_cache(maxsize=1)
def load_experience_bank() -> list[dict]:
    if not _BANK_PATH.is_file():
        return []
    items = []
    for ln in _BANK_PATH.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            items.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return items


def search_experience(
    query: str | None = None,
    *,
    company: str | None = None,
    topic: str | None = None,
    limit: int = 10,
) -> list[dict]:
    q = (query or "").strip().lower()
    co = (company or "").strip().lower()
    top = (topic or "").strip().lower()
    hits = []
    for it in load_experience_bank():
        blob = " ".join(
            [
                str(it.get("q") or ""),
                str(it.get("topic") or ""),
                " ".join(it.get("tags") or []),
                " ".join(it.get("company") or []),
                str(it.get("level") or ""),
            ]
        ).lower()
        score = 0
        if q and q in blob:
            score += 3
        elif q:
            for tok in q.split():
                if tok and tok in blob:
                    score += 1
        if co and any(co in str(c).lower() for c in (it.get("company") or [])):
            score += 2
        if top and top in blob:
            score += 2
        if not q and not co and not top:
            score = 1
        if score > 0:
            hits.append((score, it))
    hits.sort(key=lambda x: -x[0])
    return [h for _, h in hits[:limit]]
