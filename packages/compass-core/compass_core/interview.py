"""Interview pack builder (schema for model + starter session)."""

from __future__ import annotations

import json
from pathlib import Path

from .evidence import load_evidence
from .jd import ParsedJD
from .match import MatchResult


def build_pack(root: Path, job_id: str, lang: str = "zh") -> dict:
    job_dir = root / "jobs" / job_id
    jd_data = json.loads((job_dir / "jd.json").read_text(encoding="utf-8"))
    match_data = json.loads((job_dir / "match.json").read_text(encoding="utf-8"))
    jd = ParsedJD(**{k: jd_data[k] for k in ParsedJD.__dataclass_fields__ if k in jd_data})
    match = MatchResult.from_dict(match_data)
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

    from .questions import enrich_hits, infer_topics, search_questions

    topics = infer_topics(jd.keywords)
    query = " ".join(jd.keywords + jd.hard_requirements[:5] + [jd.title])
    try:
        from .rag import semantic_search

        bank_hits = semantic_search(root, query, k=12, lang=lang)
        if not bank_hits:
            raise RuntimeError("empty semantic")
    except Exception:
        bank_hits = search_questions(
            query,
            keywords=jd.keywords,
            topics=topics,
            limit=12,
            extra_root=root,
            lang=lang,
        )
    bank_hits = enrich_hits(bank_hits, lang=lang)
    from .question_dedup import filter_bank_hits, load_asked_hashes

    asked = load_asked_hashes(root)
    bank_hits = filter_bank_hits(bank_hits, asked)

    from .interview_persona import pick_persona

    persona = pick_persona(jd, match.match_explain)

    from .storybank import top_stories
    from .story_vault import recommend_stories

    stories = recommend_stories(root, job_id=job_id, keywords=jd.keywords, limit=5)
    if not stories:
        stories = top_stories(root, limit=5, skills=jd.keywords)

    from .company_pack import search_company_pack
    from .experience_bank import search_experience

    company_pack_hits = search_company_pack(jd.company, title=jd.title, limit=6)
    q_blob = " ".join((jd.keywords or [])[:8]) or (jd.title or "")
    experience_hits = search_experience(
        query=q_blob, company=jd.company, limit=6
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
        "lang": lang,
        "requirement_matrix": match.requirement_matrix,
        "match_explain": match.match_explain,
        "persona": persona,
        "bank_deduped": True,
        "stories": stories,
        "grade": match.grade,
        "company_pack_hits": company_pack_hits,
        "experience_hits": experience_hits,
    }
    from .retracted import collect_retracted_claims

    pack["retracted_claims"] = collect_retracted_claims(root, job_id)
    return pack


def render_session(pack: dict) -> str:
    from .questions import bank_section_title, format_bank_section

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
    for row in pack.get("requirement_matrix") or []:
        if row.get("kind") != "hard" or row.get("fit") not in ("direct", "partial"):
            continue
        eids = row.get("evidence_ids") or []
        eid = eids[0] if eids else "?"
        star.append(
            f"- STAR `{row.get('id')}` → `{eid}`（{row.get('fit')}）: "
            f"对齐「{str(row.get('text') or '')[:50]}」；Result 必须用证据指标或标 UNVERIFIED。"
        )
        if len(star) >= 4:
            break
    if not star:
        for e in (pack.get("evidence") or [])[:3]:
            star.append(
                f"- STAR around `{e['evidence_id']}` ({e['title']}): "
                f"Result 必须使用证据中的指标或标 UNVERIFIED。"
            )
    if not star:
        star = ["- 无匹配证据：先 /evidence 再模拟；勿编造 STAR。"]

    stress = []
    for row in pack.get("requirement_matrix") or []:
        if row.get("kind") == "hard" and row.get("fit") == "gap":
            stress.append(
                f"- 追问 `{row.get('id')}`（{row.get('severity')}）："
                f"简历未覆盖「{str(row.get('text') or '')[:50]}」，如何到岗前补齐？（/bridge，勿谎称已做过）"
            )
        if len(stress) >= 3:
            break
    if not stress:
        for g in (pack.get("gaps") or [])[:3]:
            stress.append(f"- 追问：你简历未覆盖「{g[:50]}」，如何在到岗前补齐？（指向 /bridge，勿谎称已做过）")
    for m in (pack.get("keyword_misses") or [])[:2]:
        stress.append(f"- 压力题：解释你对 `{m}` 的真实掌握边界。")

    retracted = pack.get("retracted_claims") or []
    retract_block = ""
    if retracted:
        lines = [
            f"- **勿声称**（{r.get('source')}）：{str(r.get('claim') or '')[:80]} — {r.get('reason')}"
            for r in retracted[:8]
        ]
        retract_block = "\n### Do not claim / 风险点\n" + "\n".join(lines) + "\n"

    mx = pack.get("match_explain") or {}
    band = ""
    if mx:
        band = (
            f"\n**match band**: `{mx.get('recommendation', '—')}` · "
            f"matrix={mx.get('matrix_score', '—')} · confidence={mx.get('confidence', '—')}\n"
        )
    persona = pack.get("persona") or {}
    if persona:
        band += (
            f"**persona**: `{persona.get('persona_id', '—')}` "
            f"({persona.get('label_zh') or persona.get('tone', '')})\n"
        )
    gr = pack.get("grade") or {}
    if gr.get("letter"):
        band += f"**grade**: `{gr.get('letter')}` · {gr.get('global_1_5')}/5 — {gr.get('verdict') or ''}\n"

    story_lines = []
    for s in (pack.get("stories") or [])[:5]:
        star_s = s.get("star") or {}
        story_lines.append(
            f"- `{s.get('id')}` strength={s.get('strength')} · "
            f"S: {str(star_s.get('situation') or '')[:40]} / "
            f"R: {str(star_s.get('result') or '')[:40]}"
        )
    stories_block = "\n".join(story_lines) or "- _(run `storybank rebuild`)_"

    pack_q = []
    for h in (pack.get("company_pack_hits") or [])[:5]:
        pack_q.append(f"- `{h.get('id')}` {h.get('q')}")
    company_block = "\n".join(pack_q) or "- _(no company pack match)_"
    exp_q = []
    for h in (pack.get("experience_hits") or [])[:5]:
        exp_q.append(f"- `{h.get('id')}` {h.get('q')}")
    experience_block = "\n".join(exp_q) or "- _(no experience bank hit)_"

    return f"""# Interview session: {pack['title']} @ {pack['company']}

**job_id**: `{pack['job_id']}`{band}
## Pack evidence

{ev_list}

## Storybank (top)

{stories_block}

## Company pack

{company_block}

## Experience bank

{experience_block}

## Questions

### Warm-up
{chr(10).join(warmup)}

### JD deep-dive
{chr(10).join(deep)}

### STAR stories (requirement-mapped)
{chr(10).join(star)}

### Stress follow-ups
{chr(10).join(stress) or '- （暂无）'}
{retract_block}
{bank_section_title(pack.get('lang') or 'zh')}
Topics: {', '.join(pack.get('bank_topics') or []) or '—'}

{format_bank_section(pack.get('bank_hits') or [], lang=pack.get('lang') or 'zh')}
## Scorecard

| Dimension | Score 1-5 | Notes | evidence_ids |
|-----------|-----------|-------|--------------|
| Technical |  |  |  |
| Ownership |  |  |  |
| Communication |  |  |  |
| JD fit |  |  |  |
"""

def interview_and_save(root: Path, job_id: str, lang: str = "zh") -> dict:
    pack = build_pack(root, job_id, lang=lang)
    out = root / "interviews" / job_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "pack.json").write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "session.md").write_text(render_session(pack), encoding="utf-8")
    (out / "bank_hits.json").write_text(
        json.dumps(pack.get("bank_hits") or [], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # Ensure empty scorecard exists; sync table if prior answers present
    from .scorecard import load_scorecard, save_scorecard, sync_session_md

    sc = load_scorecard(root, job_id)
    if not (out / "scorecard.json").is_file():
        save_scorecard(root, job_id, sc)
    else:
        sync_session_md(root, job_id, sc)
    return {
        "job_id": job_id,
        "evidence_n": len(pack.get("evidence") or []),
        "bank_n": len(pack.get("bank_hits") or []),
        "scorecard_path": str(out / "scorecard.json"),
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
        from .bei_probe import followup_from_probe, probe_star

        probe = probe_star(last_answer or "")
        pf = followup_from_probe(probe)
        if pf and (not gate_ok or not probe.get("ok")):
            return pf
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
    persona = pack.get("persona") or {}
    pid = persona.get("persona_id") or "technical"
    if pid == "challenging":
        return f"请用 90 秒证明你适合 {title}——我会追问任何缺少 evidence_id 的指标。"
    if pid == "hr":
        return f"请介绍你为什么选择 {title}，并引用至少一个 evidence_id 说明匹配点。"
    if pid == "supportive":
        return f"我们可以慢慢来：先用 90 秒介绍你与 {title} 最相关的一段经历，记得 cite evidence_id。"
    return f"请用 90 秒介绍你为什么适合 {title}，并引用至少一个 evidence_id。"
