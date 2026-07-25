"""Interview persona picker (IntervAI-xuanyiying Round 12)."""

from __future__ import annotations

from .jd import ParsedJD

PERSONAS = {
    "technical": {
        "persona_id": "technical",
        "tone": "precise, systems-focused",
        "probe_depth": "deep",
        "label_zh": "技术深挖",
    },
    "challenging": {
        "persona_id": "challenging",
        "tone": "skeptical, pressure-test claims",
        "probe_depth": "aggressive",
        "label_zh": "挑战施压",
    },
    "supportive": {
        "persona_id": "supportive",
        "tone": "coaching, clarifying",
        "probe_depth": "gentle",
        "label_zh": "辅导澄清",
    },
    "hr": {
        "persona_id": "hr",
        "tone": "behavioral, culture, motivation",
        "probe_depth": "behavioral",
        "label_zh": "HR 行为面",
    },
}


def pick_persona(jd: ParsedJD, match_explain: dict | None = None) -> dict:
    blob = f"{jd.title} {jd.company} {' '.join(jd.hard_requirements[:8])}".lower()
    band = (match_explain or {}).get("recommendation") or ""
    fatal = int((match_explain or {}).get("fatal_count") or 0)

    if fatal > 0 or band == "skip":
        return dict(PERSONAS["challenging"])
    if any(k in blob for k in ("hr", "招聘", "校招", "实习", "intern")):
        return dict(PERSONAS["hr"])
    if any(k in blob for k in ("算法", "架构", "sre", "平台", "infra", "backend", "ml", "llm")):
        return dict(PERSONAS["technical"])
    if band in ("exploratory",):
        return dict(PERSONAS["supportive"])
    return dict(PERSONAS["technical"])
