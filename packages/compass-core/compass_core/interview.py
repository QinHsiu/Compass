"""Interview pack builder (schema for model + starter session)."""

from __future__ import annotations

import json
from pathlib import Path

from .evidence import load_evidence
from .jd import ParsedJD
from .match import MatchResult


def build_pack(root: Path, job_id: str) -> dict:
    job_dir = root / "jobs" / job_id
    jd_data = json.loads((job_dir / "jd.json").read_text(encoding="utf-8"))
    match_data = json.loads((job_dir / "match.json").read_text(encoding="utf-8"))
    jd = ParsedJD(**{k: jd_data[k] for k in ParsedJD.__dataclass_fields__})
    match = MatchResult(**{k: match_data[k] for k in MatchResult.__dataclass_fields__})
    evidence = {e.id: e for e in load_evidence(root)}

    hit_details = []
    for h in match.evidence_hits:
        ev = evidence.get(h["evidence_id"])
        if not ev:
            continue
        hit_details.append(
            {
                "evidence_id": ev.id,
                "title": ev.title,
                "metrics": ev.metrics,
                "skills": ev.skills,
                "actions": ev.actions[:500],
            }
        )

    from .questions import infer_topics, search_questions

    topics = infer_topics(jd.keywords)
    query = " ".join(jd.keywords + jd.hard_requirements[:5] + [jd.title])
    try:
        from .rag import semantic_search

        bank_hits = semantic_search(root, query, k=12)
        if not bank_hits:
            raise RuntimeError("empty semantic")
    except Exception:
        bank_hits = search_questions(
            query,
            keywords=jd.keywords,
            topics=topics,
            limit=12,
            extra_root=root,
        )

    pack = {
        "job_id": job_id,
        "title": jd.title,
        "company": jd.company,
        "hard_requirements": jd.hard_requirements,
        "keywords": jd.keywords,
        "gaps": match.hard_gaps,
        "keyword_misses": match.keyword_misses,
        "evidence": hit_details,
        "bank_topics": topics,
        "bank_hits": bank_hits,
    }
    return pack


def render_session(pack: dict) -> str:
    from .questions import format_bank_section

    ev_list = "\n".join(
        f"- `{e['evidence_id']}` {e['title']}" for e in pack.get("evidence") or []
    ) or "- _(no evidence hits)_"

    warmup = [
        f"1. 用 90 秒介绍你为什么适合 {pack['title']}（必须点到至少 1 个 evidence_id）。",
        "2. 最近一次线上问题你怎么定位与复盘？",
    ]
    deep = []
    for i, req in enumerate((pack.get("hard_requirements") or [])[:5], 1):
        deep.append(f"{i}. 结合 JD 要求「{req[:60]}」说明你的相关证据（cite evidence_id）。")
    if not deep:
        deep = ["1. 描述你与本岗位关键词最相关的一段经历。"]

    star = []
    for e in (pack.get("evidence") or [])[:3]:
        star.append(
            f"- STAR around `{e['evidence_id']}` ({e['title']}): "
            f"Result 必须使用证据中的指标或标 UNVERIFIED。"
        )
    if not star:
        star = ["- 无匹配证据：先 /evidence 再模拟；勿编造 STAR。"]

    stress = []
    for g in (pack.get("gaps") or [])[:3]:
        stress.append(f"- 追问：你简历未覆盖「{g[:50]}」，如何在到岗前补齐？（指向 /bridge，勿谎称已做过）")
    for m in (pack.get("keyword_misses") or [])[:2]:
        stress.append(f"- 压力题：解释你对 `{m}` 的真实掌握边界。")

    return f"""# Interview session: {pack['title']} @ {pack['company']}

**job_id**: `{pack['job_id']}`

## Pack evidence

{ev_list}

## Questions

### Warm-up
{chr(10).join(warmup)}

### JD deep-dive
{chr(10).join(deep)}

### STAR stories
{chr(10).join(star)}

### Stress follow-ups
{chr(10).join(stress) or '- （暂无）'}

### Retrieved bank questions
Topics: {', '.join(pack.get('bank_topics') or []) or '—'}

{format_bank_section(pack.get('bank_hits') or [])}
## Scorecard

| Dimension | Score 1-5 | Notes | evidence_ids |
|-----------|-----------|-------|--------------|
| Technical |  |  |  |
| Ownership |  |  |  |
| Communication |  |  |  |
| JD fit |  |  |  |
"""


def interview_and_save(root: Path, job_id: str) -> dict:
    pack = build_pack(root, job_id)
    out = root / "interviews" / job_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "session.md").write_text(render_session(pack), encoding="utf-8")
    (out / "bank_hits.json").write_text(
        json.dumps(pack.get("bank_hits") or [], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "job_id": job_id,
        "evidence_n": len(pack.get("evidence") or []),
        "bank_n": len(pack.get("bank_hits") or []),
        "path": str(out),
    }


def next_followup(
    pack: dict,
    last_answer: str,
    gate_ok: bool,
    gate_reason: str = "",
    turn: int = 0,
) -> dict:
    """
    Adaptive follow-up. Returns {question, mode: llm|rules, meta}.
    """
    from .llm import chat, load_config

    gaps = pack.get("gaps") or pack.get("keyword_misses") or []
    evidence = pack.get("evidence") or []
    bank = pack.get("bank_hits") or []
    title = pack.get("title") or "this role"

    # Rule path (always available)
    def _rules() -> str:
        if not gate_ok:
            eid = evidence[0]["evidence_id"] if evidence else "ev_xxx"
            return (
                f"你的回答缺少可验证证据。请用 STAR 重述，并引用至少一个 evidence_id"
                f"（例如 `{eid}`），给出可量化结果。"
            )
        if gaps and turn % 2 == 0:
            g = gaps[min(turn, len(gaps) - 1)]
            return f"JD 仍有缺口：「{str(g)[:80]}」。你计划如何在到岗前补齐？勿编造未做过的经历。"
        if bank:
            b = bank[min(turn, len(bank) - 1)]
            return str(b.get("q") or f"结合 {title} 再深入一层：你如何权衡 trade-off？")
        if evidence:
            ev = evidence[min(turn, len(evidence) - 1)]
            return (
                f"围绕 `{ev.get('evidence_id')}`（{ev.get('title')}）："
                f"如果指标再差 30%，你会怎么定位？"
            )
        return f"为什么你比其他候选人更适合 {title}？请只基于真实经历。"

    cfg = load_config()
    system = (
        "You are a strict technical interviewer for Compass. "
        "Ask ONE short follow-up question in the user's language (default Chinese). "
        "If the answer lacks evidence, demand metrics or evidence_id. "
        "If solid, probe the next JD gap. Never invent candidate experience. "
        "Output only the question text."
    )
    user = json.dumps(
        {
            "role": title,
            "gaps": gaps[:5],
            "evidence_ids": [e.get("evidence_id") for e in evidence[:5]],
            "last_answer": (last_answer or "")[:800],
            "gate_ok": gate_ok,
            "gate_reason": gate_reason,
            "turn": turn,
        },
        ensure_ascii=False,
    )
    res = chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        config=cfg,
    )
    if res.get("used_llm") and res.get("text"):
        return {
            "question": res["text"].strip().split("\n")[0][:300],
            "mode": "llm",
            "meta": {"provider": res.get("provider"), "model": res.get("model")},
        }
    return {"question": _rules(), "mode": "rules", "meta": {"error": res.get("error") or ""}}


def opening_question(pack: dict) -> str:
    title = pack.get("title") or "本岗位"
    return f"请用 90 秒介绍你为什么适合 {title}，并引用至少一个 evidence_id。"
