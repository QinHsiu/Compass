"""RAG retrieval evaluation: hit@k over a query set."""

from __future__ import annotations

import json
from pathlib import Path

from .rag import semantic_search
from .questions import search_questions


def load_queries(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        return rows
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        rows.append(json.loads(ln))
    return rows


def evaluate_queries(
    root: Path,
    queries: list[dict],
    *,
    k: int = 3,
    semantic: bool = True,
) -> dict:
    """
    Each query: {query, expect_ids: [id, ...], keywords?: []}
    Returns summary with hit_at_k and per-query rows.
    """
    results = []
    hits = 0
    for q in queries:
        text = q.get("query") or ""
        expect = set(q.get("expect_ids") or [])
        if semantic:
            try:
                found = semantic_search(root, text, k=k, lang="zh")
            except Exception:
                found = search_questions(text, keywords=q.get("keywords") or [], limit=k, extra_root=root)
        else:
            found = search_questions(text, keywords=q.get("keywords") or [], limit=k, extra_root=root)
        ids = [h.get("id") for h in found]
        ok = bool(expect & set(ids)) if expect else bool(ids)
        if ok:
            hits += 1
        results.append(
            {
                "query": text,
                "expect_ids": list(expect),
                "got_ids": ids,
                "hit": ok,
            }
        )
    n = max(len(queries), 1)
    return {
        "k": k,
        "n": len(queries),
        "hits": hits,
        "hit_at_k": round(hits / n, 4) if queries else 0.0,
        "backend": "semantic" if semantic else "token",
        "rows": results,
    }


def log_query(root: Path, query: str, hit_ids: list[str], *, backend: str = "") -> None:
    """Append optional query log under content/rag/ (gitignore)."""
    d = root / "rag"
    d.mkdir(parents=True, exist_ok=True)
    path = d / "query_log.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"query": query, "ids": hit_ids, "backend": backend},
                ensure_ascii=False,
            )
            + "\n"
        )
