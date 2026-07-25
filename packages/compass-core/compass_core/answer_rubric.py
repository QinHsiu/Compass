"""Heuristic five-dim answer rubric for transcript / oral answers."""

from __future__ import annotations

import re

from .scorecard import DIMENSIONS


def score_qa_rubric(question: str, answer: str) -> dict[str, int]:
    """
    Local heuristic (no LLM): substance / structure / relevance / credibility / jd_fit.
    Used by transcript-import → scorecard.
    """
    q = (question or "").strip()
    a = (answer or "").strip()
    if not a:
        return {d: 1 for d in DIMENSIONS}

    # substance: length + metrics / evidence markers
    substance = 2
    if len(a) >= 80:
        substance = 3
    if len(a) >= 180:
        substance = 4
    if re.search(r"\d+\s*%|\d+\s*(ms|s|x|倍|万|k\b)|p99|latency|throughput|evidence", a, re.I):
        substance = min(5, substance + 1)

    # structure: STAR / BEI cues
    structure = 2
    star_hits = sum(
        1
        for kw in ("situation", "task", "action", "result", "背景", "行动", "结果", "复盘", "because", "所以")
        if kw in a.lower()
    )
    if star_hits >= 1:
        structure = 3
    if star_hits >= 3:
        structure = 4
    if re.search(r"(^|\n)\s*[-*•]", a) or "首先" in a or "然后" in a or "first" in a.lower():
        structure = max(structure, 3)
    try:
        from .bei_probe import probe_star

        structure = max(structure, int(probe_star(a).get("structure_score") or structure))
    except Exception:
        pass
    structure = min(5, structure)

    # relevance: overlap with question tokens
    relevance = 3
    q_toks = {t for t in re.findall(r"[\w\u4e00-\u9fff]{2,}", q.lower()) if len(t) > 1}
    a_low = a.lower()
    if q_toks:
        hit = sum(1 for t in q_toks if t in a_low)
        ratio = hit / max(len(q_toks), 1)
        if ratio >= 0.35:
            relevance = 4
        if ratio >= 0.55:
            relevance = 5
        if ratio < 0.1 and len(a) > 40:
            relevance = 2

    # credibility: hedging / fabrication smell
    credibility = 4
    if re.search(r"大概|可能|听说|据说|应该是|maybe|i think|possibly", a, re.I):
        credibility = 3
    if re.search(r"百分之百|绝对|一定能|保证上线就|never failed", a, re.I):
        credibility = 2
    if re.search(r"evidence_id|`ev_|指标|metric|实测|online", a, re.I):
        credibility = min(5, credibility + 1)

    # jd_fit: reuse relevance with slight dampen if answer ignores domain words in q
    jd_fit = relevance
    if re.search(r"系统|设计|python|k8s|rag|模型|分布式", q, re.I) and not re.search(
        r"系统|设计|python|k8s|rag|模型|分布式|architecture|latency", a, re.I
    ):
        jd_fit = max(1, relevance - 1)

    return {
        "substance": int(substance),
        "structure": int(structure),
        "relevance": int(relevance),
        "credibility": int(credibility),
        "jd_fit": int(jd_fit),
    }
