"""Attach vault evidence and JD keywords to question rows. Never mint evidence ids."""

from __future__ import annotations

from .evidence import EvidenceItem


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def attach_evidence(
    question: dict,
    evidence: list[EvidenceItem] | list,
    jd_keywords: list[str] | None = None,
) -> dict:
    row = dict(question)
    skills = {_norm(x) for x in (row.get("skill_tags") or row.get("tags") or []) if _norm(x)}
    matched_ids: list[str] = []
    overlap: set[str] = set()
    for ev in evidence or []:
        raw_skills = getattr(ev, "skills", None)
        if raw_skills is None and isinstance(ev, dict):
            raw_skills = ev.get("skills") or []
        ev_skills = {_norm(x) for x in (raw_skills or [])}
        hit = skills & ev_skills
        if hit:
            eid = getattr(ev, "id", None) or (ev.get("id") if isinstance(ev, dict) else None)
            matched_ids.append(eid)
            overlap |= hit
    kws = {_norm(x) for x in (jd_keywords or []) if _norm(x)}
    row["matched_evidence_ids"] = list(dict.fromkeys(matched_ids))
    row["matched_jd_keywords"] = sorted(skills & kws)
    row["skill_overlap"] = sorted(overlap)
    return row


def attach_evidence_many(
    questions: list[dict],
    evidence: list,
    jd_keywords: list[str] | None = None,
) -> list[dict]:
    return [attach_evidence(q, evidence, jd_keywords) for q in questions]
