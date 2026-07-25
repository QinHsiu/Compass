"""Requirement Evidence Matrix — per JD line: direct / partial / gap.

Inspired by job-resume-tailor match tables; zero-LLM, evidence-native.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .evidence import EvidenceItem
from .gate import _STOP
from .jd import HARD_MARKERS, ParsedJD
from .skill_gap import skill_mentioned_in_text

_FATAL_MARKERS = (
    "必须",
    "必备",
    "required",
    "must have",
    "must-have",
    "签证",
    "visa",
    "license",
    "执照",
    "本科",
    "硕士",
    "博士",
    "学历",
    "degree",
)


@dataclass
class RequirementRow:
    id: str
    kind: str  # responsibility | hard | nice
    text: str
    fit: str  # direct | partial | gap
    evidence_ids: list[str] = field(default_factory=list)
    fit_score: float = 0.0
    severity: str = "none"  # fatal | material | manageable | none
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _line_tokens(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9\u4e00-\u9fff+#.]{2,}", text.lower())
    return [t for t in toks if t not in _STOP and not t.isdigit()]


def _score_evidence_for_line(line: str, tokens: list[str], it: EvidenceItem) -> tuple[float, str]:
    """Return (fit_score contribution 0/0.5/1, rationale snippet)."""
    skills_blob = " ".join(it.skills or [])
    action_metric = f"{it.actions}\n{it.metrics}"
    soft = f"{it.title}\n{it.context}\n{it.body}"

    skill_hits = [t for t in tokens if skill_mentioned_in_text(t, skills_blob)]
    am_hits = [t for t in tokens if len(t) >= 3 and skill_mentioned_in_text(t, action_metric)]
    soft_hits = [t for t in tokens if len(t) >= 3 and skill_mentioned_in_text(t, soft)]

    if len(skill_hits) >= 1 or len(am_hits) >= 2:
        why = []
        if skill_hits:
            why.append(f"skills:{','.join(skill_hits[:3])}")
        if am_hits:
            why.append(f"actions/metrics:{','.join(am_hits[:3])}")
        return 1.0, "; ".join(why)
    if soft_hits or (len(am_hits) == 1):
        hits = soft_hits or am_hits
        return 0.5, f"context/title:{','.join(hits[:3])}"
    return 0.0, ""


def _classify_line(kind: str, text: str, evidence: list[EvidenceItem], row_id: str) -> RequirementRow:
    tokens = _line_tokens(text)
    ranked: list[tuple[EvidenceItem, float, str]] = []
    for it in evidence:
        sc, why = _score_evidence_for_line(text, tokens, it)
        if sc > 0:
            ranked.append((it, sc, why))
    ranked.sort(key=lambda x: x[1], reverse=True)

    if ranked and ranked[0][1] >= 1.0:
        fit, fit_score = "direct", 1.0
    elif ranked and ranked[0][1] >= 0.5:
        fit, fit_score = "partial", 0.5
    else:
        fit, fit_score = "gap", 0.0

    eids = [it.id for it, _, _ in ranked[:3]]
    rationale = ranked[0][2] if ranked else "no evidence overlap"

    severity = "none"
    if kind == "hard":
        if fit == "gap":
            blob = text.lower()
            if any(m in blob or m in text for m in _FATAL_MARKERS) or any(
                m in blob for m in HARD_MARKERS if isinstance(m, str)
            ):
                # Prefer fatal for hard credential/must language; else material
                if any(m in blob or m in text for m in _FATAL_MARKERS):
                    severity = "fatal"
                else:
                    severity = "material"
            else:
                severity = "material"
        elif fit == "partial":
            severity = "manageable"
    elif kind == "nice" and fit == "gap":
        severity = "manageable"
    elif kind == "responsibility" and fit == "gap":
        severity = "manageable"

    return RequirementRow(
        id=row_id,
        kind=kind,
        text=text,
        fit=fit,
        evidence_ids=eids,
        fit_score=fit_score,
        severity=severity,
        rationale=rationale,
    )


def build_requirement_matrix(jd: ParsedJD, evidence: list[EvidenceItem]) -> list[RequirementRow]:
    rows: list[RequirementRow] = []
    for i, text in enumerate(jd.responsibilities[:15], 1):
        rows.append(_classify_line("responsibility", text, evidence, f"resp_{i:02d}"))
    for i, text in enumerate(jd.hard_requirements[:15], 1):
        rows.append(_classify_line("hard", text, evidence, f"hard_{i:02d}"))
    for i, text in enumerate(jd.nice_to_have[:10], 1):
        rows.append(_classify_line("nice", text, evidence, f"nice_{i:02d}"))
    return rows


def summarize_matrix(rows: list[RequirementRow], evidence_count: int) -> dict:
    direct = sum(1 for r in rows if r.fit == "direct")
    partial = sum(1 for r in rows if r.fit == "partial")
    gap = sum(1 for r in rows if r.fit == "gap")
    fatal = sum(1 for r in rows if r.severity == "fatal")
    n = max(len(rows), 1)

    # Kind-weighted mean fit (resp 0.30, hard 0.50, nice 0.20 across present rows)
    weights = {"responsibility": 0.30, "hard": 0.50, "nice": 0.20}
    w_sum = 0.0
    s_sum = 0.0
    for r in rows:
        w = weights.get(r.kind, 0.2)
        w_sum += w
        s_sum += w * r.fit_score
    matrix_score = round(100 * (s_sum / w_sum if w_sum else 0.0), 1)

    if fatal > 0 or matrix_score < 40:
        recommendation = "skip"
    elif matrix_score >= 80:
        recommendation = "strong"
    elif matrix_score >= 60:
        recommendation = "plausible"
    else:
        recommendation = "exploratory"

    covered = direct + partial
    if evidence_count >= 3 and covered / n >= 0.8:
        confidence = "high"
    elif evidence_count >= 1 and covered / n >= 0.4:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "direct_count": direct,
        "partial_count": partial,
        "gap_count": gap,
        "fatal_count": fatal,
        "row_count": len(rows),
        "matrix_score": matrix_score,
        "recommendation": recommendation,
        "confidence": confidence,
    }


def render_match_explain_md(
    jd: ParsedJD,
    rows: list[RequirementRow],
    summary: dict,
    profile_fit: dict | None = None,
    posting_liveness: dict | None = None,
) -> str:
    def table(kind: str, title: str) -> str:
        subset = [r for r in rows if r.kind == kind]
        if not subset:
            return f"## {title}\n\n_无_\n"
        lines = [
            f"## {title}",
            "",
            "| id | fit | severity | evidence | text |",
            "|----|-----|----------|----------|------|",
        ]
        for r in subset:
            eids = ", ".join(f"`{e}`" for e in r.evidence_ids) or "—"
            text = r.text.replace("|", "/").replace("\n", " ")[:80]
            lines.append(
                f"| `{r.id}` | {r.fit} | {r.severity} | {eids} | {text} |"
            )
        return "\n".join(lines) + "\n"

    band = summary.get("recommendation", "?")
    conf = summary.get("confidence", "?")
    ms = summary.get("matrix_score", 0)
    pf = profile_fit or {}
    pf_block = ""
    if pf:
        pf_block = (
            f"\n## Profile fit\n\n"
            f"**status**: `{pf.get('status', 'pass')}`\n\n"
            + (
                "\n".join(f"- blocker: {b}" for b in (pf.get("blockers") or []))
                or "- blockers: —"
            )
            + "\n"
            + (
                "\n".join(f"- warning: {w}" for w in (pf.get("warnings") or []))
                or "- warnings: —"
            )
            + "\n"
        )
    lv = posting_liveness or {}
    lv_block = ""
    if lv:
        lv_block = (
            f"\n## Posting liveness\n\n"
            f"**status**: `{lv.get('status', 'unknown')}` · **ats**: `{lv.get('ats', 'unknown')}`"
            f" · age_days={lv.get('age_days', '—')} · posted_at={lv.get('posted_at') or '—'}\n"
        )
    return f"""# Match explain: {jd.title} @ {jd.company}

**job_id**: `{jd.job_id}`  
**recommendation**: `{band}` · **confidence**: `{conf}` · **matrix_score**: {ms}  
**direct/partial/gap**: {summary.get('direct_count', 0)}/{summary.get('partial_count', 0)}/{summary.get('gap_count', 0)} · **fatal**: {summary.get('fatal_count', 0)}
{pf_block}{lv_block}
{table("responsibility", "Responsibilities")}
{table("hard", "Hard requirements")}
{table("nice", "Nice to have")}
"""


def evidence_priority_from_matrix(rows: list[RequirementRow] | list[dict]) -> dict[str, float]:
    """Sum fit_score across rows citing each evidence_id (for resume ordering)."""
    scores: dict[str, float] = {}
    for r in rows:
        if isinstance(r, dict):
            eids = r.get("evidence_ids") or []
            fs = float(r.get("fit_score") or 0.0)
        else:
            eids = r.evidence_ids
            fs = r.fit_score
        for eid in eids:
            scores[eid] = scores.get(eid, 0.0) + fs
    return scores
