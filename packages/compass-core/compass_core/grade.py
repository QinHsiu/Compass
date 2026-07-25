"""Deterministic A–F / 1.0–5.0 grade + three-part 100-point score (compas v0.9)."""

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


def letter_from_score_100(score_100: float, *, fatal: int = 0, recommendation: str = "") -> str:
    if fatal > 0 or recommendation == "skip":
        return "F"
    s = float(score_100 or 0)
    if s >= 85:
        return "A"
    if s >= 75:
        return "B"
    if s >= 65:
        return "C"
    if s >= 50:
        return "D"
    return "F"


def compute_score_parts(
    *,
    match_explain: dict | None = None,
    skill_gap: dict | None = None,
    evidence_hit_n: int = 0,
    fatal_count: int = 0,
) -> dict:
    """Three-part 100-pt: direct_evidence / transferable / gap_risk (higher=better)."""
    mx = match_explain or {}
    sg = skill_gap or {}
    row_n = max(int(mx.get("row_count") or 0), 1)
    direct = int(mx.get("direct_count") or 0)
    partial = int(mx.get("partial_count") or 0)
    gap = int(mx.get("gap_count") or 0)
    fatal = int(fatal_count or mx.get("fatal_count") or 0)

    # 0–40 direct
    direct_ratio = direct / row_n
    evid_boost = min(evidence_hit_n, 5) / 5.0
    direct_evidence = round(40.0 * (0.7 * direct_ratio + 0.3 * evid_boost), 1)

    # 0–35 transferable
    existing = len(sg.get("existing") or [])
    supported = len(sg.get("supported_by_evidence") or [])
    gap_n = len(sg.get("gap") or [])
    skill_tot = max(existing + supported + gap_n, 1)
    partial_ratio = partial / row_n
    support_ratio = supported / skill_tot
    transferable = round(35.0 * (0.55 * partial_ratio + 0.45 * support_ratio), 1)

    # 0–25 gap_risk (higher = safer / fewer gaps)
    gap_ratio = gap / row_n
    penalty = min(25.0, 25.0 * gap_ratio + (10.0 if fatal else 0.0) + min(gap_n, 5) * 1.5)
    gap_risk = round(max(0.0, 25.0 - penalty), 1)

    score_100 = round(direct_evidence + transferable + gap_risk, 1)
    score_100 = max(0.0, min(100.0, score_100))
    return {
        "direct_evidence": direct_evidence,
        "transferable": transferable,
        "gap_risk": gap_risk,
        "score_100": score_100,
    }


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
    match_explain: dict | None = None,
) -> dict:
    """Return grade dict: letter, global_1_5, parts, score_100, display, dimensions."""
    sg = skill_gap or {}
    pf = profile_fit or {}
    lv = posting_liveness or {}
    mx = match_explain or {}

    existing = len(sg.get("existing") or [])
    supported = len(sg.get("supported_by_evidence") or [])
    gap_n = len(sg.get("gap") or [])
    skill_total = max(existing + supported + gap_n, 1)
    skill_cov = (existing + supported) / skill_total

    match_cv = _clamp_15(1 + 4 * (float(matrix_score) / 100.0))
    evidence_depth = _clamp_15(1 + min(evidence_hit_n, 5) * 0.8)
    skill_coverage = _clamp_15(1 + 4 * skill_cov)
    pf_status = (pf.get("status") or "pass").lower()
    if pf_status == "block":
        profile_dim = 1.0
    elif pf_status == "warn":
        profile_dim = 3.0
    else:
        profile_dim = 5.0
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
    weights = {
        "match_cv": 0.35,
        "evidence_depth": 0.2,
        "skill_coverage": 0.2,
        "profile_fit": 0.15,
        "posting_health": 0.1,
    }
    global_15 = _clamp_15(sum(dims[k] * weights[k] for k in weights))

    if fatal_count > 0 or recommendation == "skip" or pf_status == "block":
        global_15 = min(global_15, 2.0)
    elif lv_status == "stale":
        global_15 = min(global_15, 3.5)
    elif pf_status == "warn":
        global_15 = min(global_15, 4.0)

    parts = compute_score_parts(
        match_explain=mx or {
            "row_count": 1,
            "direct_count": 0,
            "partial_count": 0,
            "gap_count": 0,
            "fatal_count": fatal_count,
        },
        skill_gap=sg,
        evidence_hit_n=evidence_hit_n,
        fatal_count=fatal_count,
    )
    score_100 = parts["score_100"]
    if fatal_count > 0 or recommendation == "skip" or pf_status == "block":
        score_100 = min(score_100, 39.0)
        parts = {**parts, "score_100": score_100}
    elif lv_status == "stale":
        score_100 = min(score_100, 74.0)
        parts = {**parts, "score_100": score_100}

    letter = letter_from_score_100(
        score_100, fatal=fatal_count, recommendation=recommendation
    )
    if global_15 <= 2.0:
        letter = "F"

    apply_line = global_15 >= 4.0 and score_100 >= 75
    display = f"综合匹配度：{score_100:.0f}/100（{letter}级）"
    verdict = (
        f"{display} · {global_15}/5 — "
        + (
            "优先投递"
            if apply_line and recommendation == "strong"
            else (
                "可定制后投"
                if score_100 >= 65
                else ("探索/补证据" if score_100 >= 50 else "建议跳过")
            )
        )
    )
    return {
        "letter": letter,
        "global_1_5": global_15,
        "dimensions": dims,
        "parts": {
            "direct_evidence": parts["direct_evidence"],
            "transferable": parts["transferable"],
            "gap_risk": parts["gap_risk"],
        },
        "score_100": score_100,
        "display": display,
        "apply_line": apply_line,
        "verdict": verdict,
        "coverage": round(float(coverage or 0), 3),
    }
