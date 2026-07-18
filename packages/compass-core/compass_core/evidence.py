"""Evidence vault indexing and search."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class EvidenceItem:
    id: str
    title: str
    context: str = ""
    actions: str = ""
    metrics: str = ""
    skills: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    proof: str = ""
    body: str = ""

    def searchable_text(self) -> str:
        parts = [
            self.title,
            self.context,
            self.actions,
            self.metrics,
            self.proof,
            self.body,
            " ".join(self.skills),
            " ".join(self.tags),
        ]
        return " ".join(parts).lower()

    def to_dict(self) -> dict:
        return asdict(self)


_FRONT_RE = re.compile(r"^- \*\*(\w+)\*\*:\s*(.+)$", re.M)


def parse_evidence_md(path: Path) -> EvidenceItem:
    text = path.read_text(encoding="utf-8")
    eid = path.stem
    title = path.stem
    meta: dict[str, str] = {}
    for m in _FRONT_RE.finditer(text):
        meta[m.group(1)] = m.group(2).strip().strip("`")
    if "id" in meta:
        eid = meta["id"]
    m = re.match(r"^#\s+(.+)$", text, re.M)
    if m:
        title = m.group(1).strip()

    def section(name: str) -> str:
        pat = re.compile(
            rf"##\s+{name}\s*\n(.*?)(?=\n##\s+|\Z)", re.S | re.I
        )
        mm = pat.search(text)
        return (mm.group(1).strip() if mm else "")

    skills = []
    tags = []
    if "skills" in meta:
        skills = [s.strip() for s in re.split(r"[,，|/]", meta["skills"].strip("[]")) if s.strip()]
    if "tags" in meta:
        tags = [s.strip() for s in re.split(r"[,，|/]", meta["tags"].strip("[]")) if s.strip()]

    return EvidenceItem(
        id=eid,
        title=title,
        context=section("Context"),
        actions=section("Actions"),
        metrics=section("Metrics"),
        skills=skills,
        tags=tags,
        proof=meta.get("proof", ""),
        body=text,
    )


def load_evidence(root: Path) -> list[EvidenceItem]:
    ev_dir = root / "evidence"
    items: list[EvidenceItem] = []
    if not ev_dir.is_dir():
        return items
    for p in sorted(ev_dir.glob("*.md")):
        if p.name.lower() == "readme.md":
            continue
        items.append(parse_evidence_md(p))
    return items


def build_index(root: Path) -> dict:
    items = load_evidence(root)
    index = {
        "version": 1,
        "count": len(items),
        "items": [
            {
                "id": it.id,
                "title": it.title,
                "skills": it.skills,
                "tags": it.tags,
                "proof": it.proof,
                "path": f"evidence/{it.id}.md",
            }
            for it in items
        ],
    }
    out = root / "evidence" / "index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def search_evidence(
    items: list[EvidenceItem],
    query: str,
    skills: list[str] | None = None,
    limit: int = 20,
) -> list[tuple[EvidenceItem, float]]:
    q = query.lower()
    q_tokens = set(re.findall(r"[a-z0-9\u4e00-\u9fff+#.]+", q))
    skill_set = {s.lower() for s in (skills or [])}
    scored: list[tuple[EvidenceItem, float]] = []
    for it in items:
        text = it.searchable_text()
        score = 0.0
        for tok in q_tokens:
            if len(tok) < 2:
                continue
            if tok in text:
                score += 1.0
        for s in it.skills:
            if s.lower() in skill_set or s.lower() in q_tokens:
                score += 2.0
        for t in it.tags:
            if t.lower() in q_tokens:
                score += 0.5
        if score > 0:
            scored.append((it, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]
