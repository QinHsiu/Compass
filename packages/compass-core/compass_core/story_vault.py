"""STAR Story Vault — SQLite + tags + recommend (compas v0.9)."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from .bei_probe import probe_star

_TAG_RULES = (
    ("leadership", ("领导", "带队", "负责人", "lead", "mentor", "管理")),
    ("conflict", ("冲突", "分歧", "pushback", "争议", "反对")),
    ("failure", ("失败", "事故", "回滚", "故障", "incident", "outage")),
    ("scale", ("规模", "百万", "高并发", "scale", "qps", "吞吐")),
    ("ml", ("模型", "llm", "训练", "推理", "embedding", "rag")),
    ("ownership", ("我负责", "独立", "ownership", "端到端")),
)


def vault_path(root: Path) -> Path:
    return Path(root) / "storybank" / "vault.sqlite"


def _conn(root: Path) -> sqlite3.Connection:
    path = vault_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS stories (
            id TEXT PRIMARY KEY,
            star_json TEXT NOT NULL,
            tags TEXT,
            evidence_ids TEXT,
            job_id TEXT,
            strength INTEGER DEFAULT 3,
            source TEXT,
            answer_text TEXT,
            updated_at TEXT
        )
        """
    )
    con.commit()
    return con


def extract_tags(text: str, extra: list[str] | None = None) -> list[str]:
    tags: list[str] = []
    blob = text or ""
    lower = blob.lower()
    for tag, hints in _TAG_RULES:
        if any(h in blob or h in lower for h in hints):
            tags.append(tag)
    for e in extra or []:
        t = re.sub(r"[^a-zA-Z0-9_\u4e00-\u9fff]+", "", str(e).lower())[:24]
        if t and t not in tags:
            tags.append(t)
    return tags[:12]


def _strength_from_probe(probe: dict, text: str) -> int:
    base = int(probe.get("structure_score") or 3)
    if probe.get("ok"):
        base = min(5, base + 1)
    if len(text or "") > 200:
        base = min(5, base + 1)
    return max(1, min(5, base))


def upsert_from_answer(
    root: Path,
    *,
    job_id: str,
    turn: int,
    answer: str,
    evidence_ids: list[str] | None = None,
    keywords: list[str] | None = None,
    gate_ok: bool = False,
) -> dict | None:
    """Persist STAR draft from a practice answer when gate_ok or long enough."""
    text = (answer or "").strip()
    if not text or len(text) < 40:
        return None
    if not gate_ok and "ev_" not in text and len(text) < 120:
        return None
    probe = probe_star(text)
    sid = f"vault_{job_id}_t{turn}"
    star = {
        "situation": "（由回答推断）背景见正文前段",
        "task": "（由回答推断）目标/职责",
        "action": text[:500],
        "result": "含指标" if re.search(r"\d", text) else "（补 Result）",
        "probe": probe,
    }
    tags = extract_tags(text, keywords)
    strength = _strength_from_probe(probe, text)
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with _conn(root) as con:
        con.execute(
            """
            INSERT INTO stories (id, star_json, tags, evidence_ids, job_id, strength, source, answer_text, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              star_json=excluded.star_json,
              tags=excluded.tags,
              evidence_ids=excluded.evidence_ids,
              strength=excluded.strength,
              answer_text=excluded.answer_text,
              updated_at=excluded.updated_at
            """,
            (
                sid,
                json.dumps(star, ensure_ascii=False),
                json.dumps(tags, ensure_ascii=False),
                json.dumps(list(evidence_ids or []), ensure_ascii=False),
                job_id,
                strength,
                "scorecard",
                text[:2000],
                ts,
            ),
        )
        con.commit()
    return {"id": sid, "tags": tags, "strength": strength, "job_id": job_id}


def import_json_storybank(root: Path) -> int:
    """Seed vault from content/storybank/index.json."""
    path = Path(root) / "storybank" / "index.json"
    if not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    n = 0
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with _conn(root) as con:
        for it in data.get("items") or []:
            sid = str(it.get("id") or f"json_{n}")
            star = it.get("star") or {}
            tags = extract_tags(json.dumps(star, ensure_ascii=False), it.get("skills") or [])
            con.execute(
                """
                INSERT INTO stories (id, star_json, tags, evidence_ids, job_id, strength, source, answer_text, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  star_json=excluded.star_json,
                  tags=excluded.tags,
                  strength=excluded.strength,
                  updated_at=excluded.updated_at
                """,
                (
                    sid,
                    json.dumps(star, ensure_ascii=False),
                    json.dumps(tags, ensure_ascii=False),
                    json.dumps(it.get("evidence_ids") or [], ensure_ascii=False),
                    None,
                    int(it.get("strength") or 3),
                    "evidence_json",
                    "",
                    ts,
                ),
            )
            n += 1
        con.commit()
    return n


def list_stories(root: Path, *, limit: int = 50) -> list[dict]:
    with _conn(root) as con:
        rows = con.execute(
            "SELECT id, tags, evidence_ids, job_id, strength, source, star_json, updated_at "
            "FROM stories ORDER BY strength DESC, updated_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "tags": json.loads(r["tags"] or "[]"),
                "evidence_ids": json.loads(r["evidence_ids"] or "[]"),
                "job_id": r["job_id"],
                "strength": r["strength"],
                "source": r["source"],
                "star": json.loads(r["star_json"] or "{}"),
                "updated_at": r["updated_at"],
            }
        )
    return out


def recommend_stories(
    root: Path,
    *,
    job_id: str | None = None,
    keywords: list[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """Token-overlap recommend against vault (+ optional JD keywords)."""
    kws = [k.lower() for k in (keywords or []) if k]
    if job_id and not kws:
        jd_path = Path(root) / "jobs" / job_id / "jd.json"
        if jd_path.is_file():
            jd = json.loads(jd_path.read_text(encoding="utf-8"))
            kws = [str(x).lower() for x in (jd.get("keywords") or [])[:20]]
    stories = list_stories(root, limit=200)
    if not stories:
        # fallback seed from JSON
        from .storybank import load_storybank, top_stories

        bank = load_storybank(root)
        if not bank.get("items"):
            return []
        return top_stories(root, limit=limit, skills=keywords)

    scored = []
    for s in stories:
        blob = " ".join(
            [
                json.dumps(s.get("star") or {}, ensure_ascii=False),
                " ".join(s.get("tags") or []),
                " ".join(s.get("evidence_ids") or []),
            ]
        ).lower()
        overlap = sum(1 for k in kws if k and k in blob) if kws else 0
        scored.append((overlap, int(s.get("strength") or 0), s))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [t[2] for t in scored[:limit]]
