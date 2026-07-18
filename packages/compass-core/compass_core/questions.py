"""Searchable interview question bank with open-source attribution."""

from __future__ import annotations

import json
import re
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets" / "questions"
BANK_PATH = ASSETS / "bank.jsonl"


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9\u4e00-\u9fff+#.]{2,}", (text or "").lower()))


def load_bank(extra_root: Path | None = None) -> list[dict]:
    rows: list[dict] = []
    for name in ("bank.jsonl", "llm_agent.jsonl"):
        path = ASSETS / name
        if path.is_file():
            for ln in path.read_text(encoding="utf-8").splitlines():
                if ln.strip():
                    rows.append(json.loads(ln))
    if extra_root:
        for name in ("extra.jsonl", "llm_agent.jsonl"):
            extra = Path(extra_root) / "questions" / name
            if extra.is_file():
                for ln in extra.read_text(encoding="utf-8").splitlines():
                    if ln.strip():
                        rows.append(json.loads(ln))
    return rows


def search_questions(
    query: str,
    *,
    keywords: list[str] | None = None,
    topics: list[str] | None = None,
    limit: int = 12,
    bank: list[dict] | None = None,
    extra_root: Path | None = None,
) -> list[dict]:
    """Token overlap retrieval; returns questions with score + source fields."""
    items = bank if bank is not None else load_bank(extra_root)
    q_tokens = _tokenize(query)
    for kw in keywords or []:
        q_tokens |= _tokenize(kw)
    topic_set = {t.lower() for t in (topics or [])}

    scored: list[tuple[float, dict]] = []
    for it in items:
        text = " ".join(
            [
                it.get("q") or "",
                it.get("topic") or "",
                " ".join(it.get("tags") or []),
            ]
        )
        tokens = _tokenize(text)
        overlap = len(q_tokens & tokens)
        score = float(overlap)
        if topic_set and (it.get("topic") or "").lower() in topic_set:
            score += 2.0
        for t in it.get("tags") or []:
            if t.lower() in q_tokens:
                score += 1.5
        if score > 0:
            scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for sc, it in scored[:limit]:
        row = dict(it)
        row["score"] = sc
        out.append(row)
    return out


def infer_topics(keywords: list[str]) -> list[str]:
    blob = " ".join(keywords).lower()
    topics = []
    mapping = [
        ("python", ["python", "django", "fastapi"]),
        ("java", ["java", "spring", "jvm", "kafka"]),
        ("frontend", ["react", "vue", "javascript", "typescript", "css", "frontend"]),
        ("mlops", ["ml", "llm", "rag", "feature store", "pytorch", "spark", "mlops"]),
        ("llm", ["llm", "gpt", "transformer", "prompt", "embedding", "finetune", "lora"]),
        ("agent", ["agent", "react", "tool", "langchain", "autogen", "mcp", "multi-agent"]),
        ("devops", ["kubernetes", "k8s", "docker", "devops", "sre", "linux", "redis"]),
        ("system-design", ["distributed", "scale", "architecture"]),
        ("behavioral", ["ownership", "leadership"]),
        ("algorithms", ["algorithm", "sql", "leetcode"]),
    ]
    for topic, keys in mapping:
        if any(k in blob for k in keys):
            topics.append(topic)
    if not topics:
        topics = ["behavioral", "system-design"]
    return topics


def format_bank_section(hits: list[dict]) -> str:
    if not hits:
        return "_No bank hits — rely on JD deep-dive questions._\n"
    lines = []
    for i, h in enumerate(hits, 1):
        src = h.get("source") or "unknown"
        url = h.get("source_url") or ""
        cite = f" — source: {src}" + (f" ({url})" if url else "")
        lines.append(
            f"{i}. **[{h.get('id')}]** ({h.get('topic')}/{h.get('difficulty')}) {h.get('q')}{cite}"
        )
    return "\n".join(lines) + "\n"
