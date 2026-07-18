"""Local Chroma-backed semantic search over question banks."""

from __future__ import annotations

import json
from pathlib import Path

from .questions import load_bank, search_questions


COLLECTION = "compass_questions"


def _rag_dir(root: Path) -> Path:
    d = root / "rag"
    d.mkdir(parents=True, exist_ok=True)
    return d


def index_questions(root: Path) -> dict:
    """Build/rebuild local vector index. Falls back gracefully if chromadb missing."""
    rows = load_bank(root)
    try:
        import chromadb
    except ImportError:
        path = _rag_dir(root) / "bank_fallback.json"
        path.write_text(json.dumps({"count": len(rows)}, ensure_ascii=False), encoding="utf-8")
        return {
            "ok": False,
            "count": len(rows),
            "backend": "token-fallback",
            "error": "chromadb not installed; pip install chromadb",
        }

    client = chromadb.PersistentClient(path=str(_rag_dir(root) / "chroma"))
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    col = client.create_collection(COLLECTION)
    ids, docs, metas = [], [], []
    for r in rows:
        qid = r.get("id") or f"anon_{len(ids)}"
        text = f"{r.get('q', '')} topic:{r.get('topic', '')} tags:{' '.join(r.get('tags') or [])}"
        ids.append(qid)
        docs.append(text)
        metas.append(
            {
                "topic": str(r.get("topic") or ""),
                "source": str(r.get("source") or "")[:200],
                "difficulty": str(r.get("difficulty") or ""),
            }
        )
    # batch add
    batch = 100
    for i in range(0, len(ids), batch):
        col.add(
            ids=ids[i : i + batch],
            documents=docs[i : i + batch],
            metadatas=metas[i : i + batch],
        )
    return {"ok": True, "count": len(ids), "backend": "chromadb", "path": str(_rag_dir(root) / "chroma")}


def semantic_search(root: Path, query: str, k: int = 8) -> list[dict]:
    """Semantic search; falls back to token search_questions."""
    try:
        import chromadb
    except ImportError:
        return search_questions(query, limit=k, extra_root=root)

    path = _rag_dir(root) / "chroma"
    if not path.exists():
        index_questions(root)
    client = chromadb.PersistentClient(path=str(path))
    try:
        col = client.get_collection(COLLECTION)
    except Exception:
        index_questions(root)
        col = client.get_collection(COLLECTION)

    res = col.query(query_texts=[query], n_results=min(k, max(col.count(), 1)))
    bank = {r["id"]: r for r in load_bank(root)}
    out = []
    ids = (res.get("ids") or [[]])[0]
    docs = (res.get("documents") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    for i, qid in enumerate(ids):
        base = dict(bank.get(qid) or {"id": qid, "q": docs[i] if i < len(docs) else query})
        base["score"] = float(1.0 / (1.0 + (dists[i] if i < len(dists) else 1.0)))
        base["semantic"] = True
        out.append(base)
    return out
