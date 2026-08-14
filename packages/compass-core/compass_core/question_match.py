"""Attach vault evidence and JD keywords to question rows. Never mint evidence ids."""

from __future__ import annotations

from .evidence import EvidenceItem
from .interview_persona import PERSONA_TOPIC_BIAS


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
            eid = getattr(ev, "id", None)
            if eid is None and isinstance(ev, dict):
                eid = ev.get("id")
            if not isinstance(eid, str) or not eid.strip():
                continue
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


def rank_for_persona(hits: list[dict], persona: dict, *, limit: int = 12) -> list[dict]:
    pid = (persona or {}).get("persona_id") or "technical"
    bias = {x.lower() for x in PERSONA_TOPIC_BIAS.get(pid, ())}

    def _boost(h: dict) -> float:
        score = float(h.get("score") or 0.0)
        blob = " ".join(
            [
                str(h.get("pack") or ""),
                str(h.get("topic") or ""),
                str(h.get("round") or ""),
                str(h.get("difficulty") or ""),
                " ".join(h.get("tags") or []),
                " ".join(h.get("persona_affinity") or []),
            ]
        ).lower()
        if pid in {str(x).lower() for x in (h.get("persona_affinity") or [])}:
            score += 3.0
        if any(b in blob for b in bias):
            score += 2.0
        return score

    ranked = sorted(hits, key=_boost, reverse=True)
    out = []
    for h in ranked[:limit]:
        row = dict(h)
        row["persona_score"] = _boost(h)
        out.append(row)
    return out
