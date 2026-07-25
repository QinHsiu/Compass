"""Four-quadrant gap diagnosis + bridge plan."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .evidence import load_evidence
from .jd import ParsedJD
from .match import MatchResult


def _load_job(root: Path, job_id: str) -> tuple[ParsedJD, MatchResult]:
    job_dir = root / "jobs" / job_id
    jd_data = json.loads((job_dir / "jd.json").read_text(encoding="utf-8"))
    match_data = json.loads((job_dir / "match.json").read_text(encoding="utf-8"))
    jd = ParsedJD(**{k: jd_data[k] for k in ParsedJD.__dataclass_fields__ if k in jd_data})
    match = MatchResult.from_dict(match_data)
    return jd, match


def build_actions(jd: ParsedJD, match: MatchResult) -> list[dict]:
    actions: list[dict] = []
    matrix = match.requirement_matrix or []
    fatal_rows = [r for r in matrix if r.get("severity") == "fatal"]
    material_gaps = [
        r for r in matrix if r.get("kind") == "hard" and r.get("fit") == "gap" and r.get("severity") != "fatal"
    ]
    partial_rows = [r for r in matrix if r.get("fit") == "partial" and r.get("evidence_ids")]

    # Evidence: fatal / material hard gaps from requirement matrix (prefer over coarse hard_gaps)
    for row in fatal_rows[:5]:
        actions.append(
            {
                "quadrant": "evidence",
                "priority": "P0",
                "what": f"致命缺口（{row.get('id')}）：补齐可验证经历 — {str(row.get('text') or '')[:80]}",
                "proof": "新 evidence 条目（含指标/链接）",
                "eta": "3-7天",
                "related_evidence": list(row.get("evidence_ids") or []),
                "related_jd_keywords": [k for k in match.keyword_misses if k.lower() in str(row.get("text") or "").lower()][:5],
            }
        )
    if not fatal_rows:
        for row in material_gaps[:3]:
            actions.append(
                {
                    "quadrant": "evidence",
                    "priority": "P0",
                    "what": f"硬性缺口（{row.get('id')}）：{str(row.get('text') or '')[:80]}",
                    "proof": "新 evidence 条目（含指标/链接）",
                    "eta": "3-7天",
                    "related_evidence": [],
                    "related_jd_keywords": [k for k in match.keyword_misses if k.lower() in str(row.get("text") or "").lower()][:5],
                }
            )
    if not fatal_rows and not material_gaps:
        for gap in match.hard_gaps[:5]:
            actions.append(
                {
                    "quadrant": "evidence",
                    "priority": "P0",
                    "what": f"补齐可验证经历以覆盖：{gap[:80]}",
                    "proof": "新 evidence 条目（含指标/链接）",
                    "eta": "3-7天",
                    "related_evidence": [],
                    "related_jd_keywords": [k for k in match.keyword_misses if k.lower() in gap.lower()][:5],
                }
            )

    # Narrative: elevate partial evidence metrics for a requirement
    for row in partial_rows[:2]:
        eids = list(row.get("evidence_ids") or [])[:2]
        actions.append(
            {
                "quadrant": "narrative",
                "priority": "P1",
                "what": f"把 {', '.join(eids)} 的指标前置，对齐 JD「{str(row.get('text') or '')[:40]}」",
                "proof": "更新后的 resume.md（含 evidence_id）",
                "eta": "0.5天",
                "related_evidence": eids,
                "related_jd_keywords": match.keyword_hits[:5],
            }
        )
    if not partial_rows and match.evidence_hits and match.score < 85:
        eids = [h["evidence_id"] for h in match.evidence_hits[:3]]
        actions.append(
            {
                "quadrant": "narrative",
                "priority": "P1",
                "what": f"把 {', '.join(eids)} 的指标前置到简历摘要与首条 bullet",
                "proof": "更新后的 resume.md（含 evidence_id）",
                "eta": "0.5天",
                "related_evidence": eids,
                "related_jd_keywords": match.keyword_hits[:5],
            }
        )

    # Skill gaps from keyword misses + skill_gap.gap
    skill_gaps = list((match.skill_gap or {}).get("gap") or [])[:5]
    for kw in skill_gaps or match.keyword_misses[:5]:
        actions.append(
            {
                "quadrant": "skill",
                "priority": "P1",
                "what": f"针对 `{kw}` 做可演示练习（demo/笔记/PR）",
                "proof": f"仓库或文章链接 → 入库 evidence（skills含 {kw}）",
                "eta": "2-5天",
                "related_evidence": [],
                "related_jd_keywords": [kw],
            }
        )

    # Process — include recommendation band when available
    band = (match.match_explain or {}).get("recommendation") or ""
    band_note = f"（match 建议：{band}）" if band else ""
    actions.append(
        {
            "quadrant": "process",
            "priority": "P2",
            "what": f"将该岗位写入 /track，并设定 3 日内跟进节点{band_note}",
            "proof": "content/track/board.json 状态更新",
            "eta": "15分钟",
            "related_evidence": [],
            "related_jd_keywords": [],
        }
    )
    return actions


def render_report(jd: ParsedJD, match: MatchResult, actions: list[dict]) -> str:
    def lines_for(q: str) -> str:
        items = [a for a in actions if a["quadrant"] == q]
        if not items:
            return "_无_\n"
        return "\n".join(
            f"- **{a['priority']}** {a['what']}（证明物：{a['proof']}；耗时：{a['eta']}）"
            for a in items
        ) + "\n"

    table = "\n".join(
        f"| {a['priority']} | {a['quadrant']} | {a['what']} | {a['proof']} | {a['eta']} |"
        for a in actions
    )
    summary = (
        f"匹配分 {match.score}，关键词覆盖 {match.coverage:.0%}；"
        f"命中 {len(match.keyword_hits)}，缺失 {len(match.keyword_misses)}；"
        f"硬性缺口 {len(match.hard_gaps)} 条。"
    )
    mx = match.match_explain or {}
    if mx:
        summary += (
            f" 矩阵分 {mx.get('matrix_score', '—')}，建议 `{mx.get('recommendation', '—')}`"
            f"（置信 {mx.get('confidence', '—')}；"
            f"direct/partial/gap={mx.get('direct_count', 0)}/{mx.get('partial_count', 0)}/{mx.get('gap_count', 0)}；"
            f"fatal={mx.get('fatal_count', 0)}）。"
        )
    lv = match.posting_liveness or {}
    if lv.get("status"):
        summary += (
            f" 岗位活跃度 `{lv.get('status')}`"
            f"（ats={lv.get('ats', 'unknown')}；age_days={lv.get('age_days', '—')}）。"
        )
    return f"""# Diagnose: {jd.title} @ {jd.company}

**job_id**: `{jd.job_id}`  
**match_score**: {match.score}  
**date**: {date.today().isoformat()}

## Summary

{summary}

## Quadrant: Evidence

{lines_for("evidence")}
## Quadrant: Narrative

{lines_for("narrative")}
## Quadrant: Skill

{lines_for("skill")}
## Quadrant: Process

{lines_for("process")}
## Next actions

| Priority | Quadrant | 做什么 | 证明物 | 预计耗时 |
|----------|----------|--------|--------|----------|
{table}
"""


def render_bridge(jd: ParsedJD, actions: list[dict]) -> str:
    skill_actions = [a for a in actions if a["quadrant"] in ("skill", "evidence")]
    rows = []
    plan_parts = []
    for i, a in enumerate(skill_actions[:6], 1):
        eid = f"ev_bridge_{jd.job_id}_{i}"
        kws = ", ".join(a.get("related_jd_keywords") or []) or "general"
        rows.append(f"| `{eid}` | {a['proof']} | {kws} | {a['eta']} |")
        plan_parts.append(f"{i}. **{a['what']}** — 产出写入 `{eid}`，禁止写回虚假在职经历。")
    return f"""# Bridge plan: {jd.job_id}

Goal: close skill/evidence gaps with **new verifiable artifacts**. Do not backdate onto CV.

## Plan

{chr(10).join(plan_parts) or '_无技能/证据缺口_'}

## Evidence to create

| Proposed id | Deliverable | Maps to JD keywords | ETA |
|-------------|-------------|---------------------|-----|
{chr(10).join(rows) or '| — | — | — | — |'}
"""


def diagnose_and_save(root: Path, job_id: str) -> dict:
    from .questions import infer_topics, search_questions

    jd, match = _load_job(root, job_id)
    actions = build_actions(jd, match)
    # Suggest bank drills for skill gaps
    topics = infer_topics(match.keyword_misses + jd.keywords)
    drills = search_questions(
        " ".join(match.keyword_misses + match.hard_gaps[:3]),
        keywords=match.keyword_misses,
        topics=topics,
        limit=8,
        extra_root=root,
    )
    if drills:
        actions.append(
            {
                "quadrant": "skill",
                "priority": "P1",
                "what": f"按检索题库练习：{', '.join(d['id'] for d in drills[:3])}",
                "proof": "interview session 笔记 + bank_hits.json",
                "eta": "1-2天",
                "related_evidence": [],
                "related_jd_keywords": match.keyword_misses[:5],
                "bank_ids": [d["id"] for d in drills],
            }
        )
    out = root / "diagnoses" / job_id
    out.mkdir(parents=True, exist_ok=True)
    report = render_report(jd, match, actions)
    if drills:
        drill_lines = "\n".join(
            f"- `{d['id']}` {d['q']} _(source: {d.get('source')})_" for d in drills
        )
        report += f"\n## Suggested bank drills\n\n{drill_lines}\n"
    bridge = render_bridge(jd, actions)
    (out / "report.md").write_text(report, encoding="utf-8")
    (out / "bridge_plan.md").write_text(bridge, encoding="utf-8")
    (out / "actions.json").write_text(
        json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "bank_drills.json").write_text(
        json.dumps(drills, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    track_item = None
    try:
        from .track import seed_from_match

        track_item = seed_from_match(root, job_id)
    except Exception:
        track_item = None
    resume_metrics = None
    resume_path = root / "resumes" / job_id / "resume.json"
    if resume_path.is_file():
        from .resume_metrics import calculate_key_metrics

        resume_metrics = calculate_key_metrics(
            json.loads(resume_path.read_text(encoding="utf-8"))
        )
    from .practice_stats import practice_rollup

    return {
        "job_id": job_id,
        "actions": len(actions),
        "score": match.score,
        "bank_drills": len(drills),
        "track_item": track_item,
        "resume_metrics": resume_metrics,
        "practice": practice_rollup(root),
        "posting_liveness": match.posting_liveness,
        "path": str(out),
    }
