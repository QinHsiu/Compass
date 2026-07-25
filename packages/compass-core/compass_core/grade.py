"""Deterministic A–F / 1.0–5.0 grade from match matrix (compas.txt P0).

No LLM — maps matrix_score + gates into letter, global_1_5, and five dimensions.
"""

from __future__ import annotations


def _clamp_15(v: float) -> float:
    return round(max(1.0, min(5.0, float(v))), 1)


def letter_from_score(matrix_score: float, *, fatal: int = 0, recommendation: str = "") -> str:
    if fatal > 0 or recommendation == "skip":
        return "F"
    s = float(matrix_score or 0)
    if s >= 85:
        return "A"
    if s >= 75:
        return "B"
    if s >= 65:
        return "C"
    if s >= 50:
        return "D"
    return "F"


def compute_grade(
    *,
    matrix_score: float,
    coverage: float = 0.0,
    fatal_count: int = 0,
    recommendation: str = "exploratory",
    evidence_hit_n: int = 0,
    skill_gap: dict | None = None,
    profile_fit: dict | None = None,
    posting_liveness: dict | None = None,
) -> dict:
    """Return grade dict: letter, global_1_5, dimensions, verdict."""
    sg = skill_gap or {}
    pf = profile_fit or {}
    lv = posting_liveness or {}

    existing = len(sg.get("existing") or [])
    supported = len(sg.get("supported_by_evidence") or [])
    gap_n = len(sg.get("gap") or [])
    skill_total = max(existing + supported + gap_n, 1)
    skill_cov = (existing + supported) / skill_total

    match_cv = _clamp_15(1 + 4 * (float(matrix_score) / 100.0))
    evidence_depth = _clamp_15(1 + min(evidence_hit_n, 5) * 0.8)
    skill_coverage = _clamp_15(1 + 4 * skill_cov)
    # profile
    pf_status = (pf.get("status") or "pass").lower()
    if pf_status == "block":
        profile_dim = 1.0
    elif pf_status == "warn":
        profile_dim = 3.0
    else:
        profile_dim = 5.0
    # posting health
    lv_status = (lv.get("status") or "unknown").lower()
    if lv_status == "fresh":
        posting_health = 5.0
    elif lv_status == "stale":
        posting_health = 2.0
    else:
        posting_health = 3.0

    dims = {
        "match_cv": match_cv,
        "evidence_depth": evidence_depth,
        "skill_coverage": skill_coverage,
        "profile_fit": float(profile_dim),
        "posting_health": float(posting_health),
    }
    # weighted global
    weights = {
        "match_cv": 0.35,
        "evidence_depth": 0.2,
        "skill_coverage": 0.2,
        "profile_fit": 0.15,
        "posting_health": 0.1,
    }
    global_raw = sum(dims[k] * weights[k] for k in weights)
    global_15 = _clamp_15(global_raw)

    # Caps from gates
    if fatal_count > 0 or recommendation == "skip" or pf_status == "block":
        global_15 = min(global_15, 2.0)
    elif lv_status == "stale":
        global_15 = min(global_15, 3.5)
    elif pf_status == "warn":
        global_15 = min(global_15, 4.0)

    letter = letter_from_score(
        matrix_score, fatal=fatal_count, recommendation=recommendation
    )
    # Align letter with capped global when gates fire
    if global_15 <= 2.0:
        letter = "F"
    elif letter == "A" and global_15 < 4.0:
        letter = "B"

    apply_line = global_15 >= 4.0
    verdict = (
        f"{letter} · {global_15}/5 — "
        + (
            "优先投递"
            if apply_line and recommendation == "strong"
            else (
                "可定制后投"
                if global_15 >= 3.5
                else ("探索/补证据" if global_15 >= 2.5 else "建议跳过")
            )
        )
    )
    return {
        "letter": letter,
        "global_1_5": global_15,
        "dimensions": dims,
        "apply_line": apply_line,
        "verdict": verdict,
        "coverage": round(float(coverage or 0), 3),
    }
