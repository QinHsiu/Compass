"""Map scorecard five dimensions → root-cause labels (compas v0.10 / interview-coach)."""

from __future__ import annotations

# dimension → (root_cause_id, label_zh, fix_hint)
_MAP = {
    "substance": (
        "narrative_hoarding",
        "叙事囤积",
        "压缩背景，前置可验证 Result + evidence_id",
    ),
    "structure": (
        "status_anxiety",
        "结构焦虑/STAR 不全",
        "按 Situation→Task→Action→Result 重述，补个人「我」贡献",
    ),
    "credibility": (
        "evidence_gap",
        "证据缺口",
        "补 metrics 或标 UNVERIFIED；引用已知 evidence_id",
    ),
    "relevance": (
        "off_target",
        "答非所问",
        "先复述面试官问题关键词，再对齐 JD requirement_id",
    ),
    "jd_fit": (
        "role_mismatch",
        "岗位匹配弱",
        "用 requirement_matrix 中 direct/partial 行重练；gap 勿谎称",
    ),
}

THRESHOLD = 2.5


def diagnose_root_causes(aggregate_scores: dict | None, *, threshold: float = THRESHOLD) -> list[dict]:
    """Return root_causes for dimensions at or below threshold."""
    scores = aggregate_scores or {}
    out: list[dict] = []
    for dim, (cid, label, fix) in _MAP.items():
        val = float(scores.get(dim) or 0)
        if val <= 0:
            continue
        if val <= threshold:
            out.append(
                {
                    "dimension": dim,
                    "score": val,
                    "root_cause": cid,
                    "label_zh": label,
                    "fix": fix,
                }
            )
    out.sort(key=lambda x: x["score"])
    return out


def attach_root_causes(aggregate: dict) -> dict:
    agg = dict(aggregate or {})
    scores = agg.get("scores") or {}
    agg["root_causes"] = diagnose_root_causes(scores)
    return agg
