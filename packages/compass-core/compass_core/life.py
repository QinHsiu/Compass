"""Interest exploration → career planning (Holland RIASEC + confidence routing)."""

from __future__ import annotations

import html
import json
import math
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from .ingest import extract_text
from .llm import chat
from .paths import ensure_dirs

DIMS = ("R", "I", "A", "S", "E", "C")
CONFIDENCE_THRESHOLD = 0.72
MIN_SIGNAL_CLASSES = 3

# Keyword heuristics for soft RIASEC inference from free text
_DIM_KEYWORDS: dict[str, tuple[str, ...]] = {
    "R": ("硬件", "嵌入式", "运维", "sre", "机械", "制造", "实验", "动手", "设备", "现场", "devops"),
    "I": ("算法", "研究", "论文", "分析", "建模", "科研", "数学", "统计", "rag", "ml", "ai", "数据科学"),
    "A": ("设计", "ux", "ui", "创意", "文案", "视觉", "内容", "品牌", "多媒体", "写作"),
    "S": ("教学", "培训", "辅导", "客服", "人力", "hr", "助人", "社区", "运营支持", "协作"),
    "E": ("产品经理", "创业", "商务", "销售", "增长", "领导", "融资", "商业", "pm", "负责人"),
    "C": ("财务", "审计", "质量", "流程", "规范", "文档", "项目管理", "数据治理", "运营", "合规"),
}

_DOMAIN_RE = re.compile(
    r"(算法|机器学习|深度学习|大模型|llm|nlp|cv|后端|前端|全栈|数据|运维|产品|设计|"
    r"金融|教育|医疗|电商|游戏|安全|嵌入式|硬件|科研|咨询|销售|运营)",
    re.I,
)
_SKILL_RE = re.compile(
    r"(python|java|go|c\+\+|javascript|typescript|pytorch|tensorflow|spark|kafka|"
    r"kubernetes|docker|sql|react|vue|fastapi|django|redis|mysql|aws|gcp|azure)",
    re.I,
)
_EDU_RE = re.compile(
    r"(博士|硕士|本科|学士|大专|研究生|phd|master|bachelor|mba|学历|"
    r"\d+\s*年|工作\s*\d+|经验\s*\d+|应届|在读|毕业)",
    re.I,
)
_CONSTRAINT_RE = re.compile(
    r"(北京|上海|深圳|杭州|广州|成都|远程|hybrid|薪资|待遇|签证|签证|"
    r"转行|跳槽|升职|考研|出国|实习|全职|兼职|行业|赛道|阶段)",
    re.I,
)


def _assets_path() -> Path:
    return Path(__file__).resolve().parent / "assets" / "life" / "riasec_zh.json"


def load_riasec_bank() -> dict:
    path = _assets_path()
    return json.loads(path.read_text(encoding="utf-8"))


def new_session_id() -> str:
    return f"life_{date.today().isoformat().replace('-', '')}_{uuid.uuid4().hex[:8]}"


def session_dir(root: Path, session_id: str) -> Path:
    return root / "life" / session_id


def ingest_life_input(
    root: Path,
    *,
    text: str | None = None,
    file_path: str | Path | None = None,
    session_id: str | None = None,
) -> dict:
    """Persist raw narrative; return session_id + text length."""
    ensure_dirs(root)
    (root / "life").mkdir(parents=True, exist_ok=True)
    body = (text or "").strip()
    warnings: list[str] = []
    source = "paste"
    if file_path:
        extracted = extract_text(file_path)
        body = (extracted.get("text") or "").strip() or body
        warnings = list(extracted.get("warnings") or [])
        source = str(extracted.get("format") or "file")
    if not body:
        raise ValueError("empty life input: provide text or readable file")
    sid = session_id or new_session_id()
    d = session_dir(root, sid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "input.md").write_text(
        f"# Life input\n\n- **session**: `{sid}`\n- **source**: {source}\n\n---\n\n{body}\n",
        encoding="utf-8",
    )
    return {"session_id": sid, "chars": len(body), "source": source, "warnings": warnings, "path": str(d)}


def _uniq(items: list[str], limit: int = 12) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = x.lower().strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x.strip())
        if len(out) >= limit:
            break
    return out


def assess_confidence(text: str) -> dict:
    """
    Rule-based signal extraction + confidence.
    route = direct | assessment
    """
    t = text or ""
    domains = _uniq([m.group(0) for m in _DOMAIN_RE.finditer(t)])
    skills = _uniq([m.group(0) for m in _SKILL_RE.finditer(t)])
    edu_hits = _uniq([m.group(0) for m in _EDU_RE.finditer(t)])
    constraints = _uniq([m.group(0) for m in _CONSTRAINT_RE.finditer(t)])

    has_domain = bool(domains or skills)
    has_edu = bool(edu_hits)
    has_constraint = bool(constraints)
    classes = sum([has_domain, has_edu, has_constraint])

    # coverage score
    coverage = classes / 3.0
    richness = min(1.0, (len(domains) + len(skills)) / 6.0) * 0.35
    length_bonus = 0.15 if len(t) >= 280 else (0.08 if len(t) >= 120 else 0.0)
    consistency = 0.1 if (has_domain and has_edu) else 0.0
    confidence = round(min(1.0, coverage * 0.55 + richness + length_bonus + consistency), 3)

    route = (
        "direct"
        if confidence >= CONFIDENCE_THRESHOLD and classes >= MIN_SIGNAL_CLASSES
        else "assessment"
    )
    return {
        "domains": domains,
        "skills": skills,
        "education_or_tenure": edu_hits,
        "constraints": constraints,
        "signal_classes": classes,
        "confidence": confidence,
        "threshold": CONFIDENCE_THRESHOLD,
        "route": route,
        "reason": (
            "信号齐全且置信度达标，可生成详细规划（仍标注不确定项）"
            if route == "direct"
            else "经历信号不足，建议先完成 Holland RIASEC 测评再出规划"
        ),
    }


def infer_riasec_from_text(text: str) -> dict[str, int]:
    """Soft 0–100 scores from keyword hits (for path A visualization)."""
    low = (text or "").lower()
    raw: dict[str, float] = {d: 0.0 for d in DIMS}
    for dim, kws in _DIM_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in low:
                raw[dim] += 1.0
    # normalize to 0-100 with floor so chart is readable
    mx = max(raw.values()) or 1.0
    scores = {d: int(round(25 + 75 * (raw[d] / mx))) if raw[d] else 20 for d in DIMS}
    # boost dims that clearly dominate
    if mx >= 2:
        for d in DIMS:
            if raw[d] >= mx:
                scores[d] = min(100, scores[d] + 5)
    return scores


def score_riasec(answers: dict[str, int] | list[dict]) -> dict:
    """
    answers: {question_id: 1-5} or list of {id, value}.
    Returns scores 0-100 per dim + ranked code (e.g. IAS).
    """
    bank = load_riasec_bank()
    qmap = {q["id"]: q for q in bank["questions"]}
    if isinstance(answers, list):
        adict = {str(a.get("id") or a.get("question_id")): int(a.get("value") or a.get("score") or 0) for a in answers}
    else:
        adict = {str(k): int(v) for k, v in answers.items()}

    sums: dict[str, list[int]] = {d: [] for d in DIMS}
    for qid, val in adict.items():
        q = qmap.get(qid)
        if not q:
            continue
        v = max(1, min(5, val))
        sums[q["dim"]].append(v)

    scores: dict[str, int] = {}
    for d in DIMS:
        vals = sums[d]
        if not vals:
            scores[d] = 0
        else:
            # mean Likert → 0-100
            scores[d] = int(round((sum(vals) / len(vals) - 1) / 4 * 100))

    ranked = sorted(DIMS, key=lambda d: (-scores[d], d))
    code = "".join(ranked[:3])
    return {
        "scores": scores,
        "holland_code": code,
        "ranked": ranked,
        "answered": len([k for k in adict if k in qmap]),
        "total_questions": len(qmap),
    }


def _role_suggestions(scores: dict[str, int], extract: dict) -> list[dict]:
    bank = load_riasec_bank()
    clusters = bank.get("role_clusters") or {}
    ranked = sorted(DIMS, key=lambda d: (-scores.get(d, 0), d))
    paths: list[dict] = []
    domains = extract.get("domains") or []
    skills = extract.get("skills") or []
    for i, dim in enumerate(ranked[:3]):
        roles = list(clusters.get(dim) or [])[:3]
        # weave user domain if present
        if domains and i == 0:
            roles = [f"{domains[0]}方向 · {roles[0]}"] + roles[1:]
        paths.append(
            {
                "rank": i + 1,
                "holland_focus": dim,
                "title": roles[0] if roles else f"{dim} 相关方向",
                "roles": roles,
                "fit_score": scores.get(dim, 0),
                "why": f"维度 {dim} 得分 {scores.get(dim, 0)}；"
                + (f"与已识别技能 {', '.join(skills[:3])} 可叠加。" if skills else "需用测评与实践进一步验证。"),
                "evidence_note": "基于输入信号与 RIASEC 分数；未核实处标 UNVERIFIED",
            }
        )
    # fill to 3-5 with cross combos
    if len(paths) < 4 and len(ranked) >= 2:
        a, b = ranked[0], ranked[1]
        paths.append(
            {
                "rank": len(paths) + 1,
                "holland_focus": f"{a}+{b}",
                "title": f"{a}/{b} 交叉方向",
                "roles": (clusters.get(a) or [])[:1] + (clusters.get(b) or [])[:1],
                "fit_score": int((scores.get(a, 0) + scores.get(b, 0)) / 2),
                "why": f"主码 {a} 与次码 {b} 组合，适合复合岗位探索。",
                "evidence_note": "UNVERIFIED 交叉假设，需用项目验证",
            }
        )
    return paths[:5]


def _actions_90d(extract: dict, scores: dict[str, int], paths: list[dict]) -> list[dict]:
    top = paths[0]["title"] if paths else "目标方向"
    skills = extract.get("skills") or []
    return [
        {
            "when": "第1-2周",
            "what": f"写清目标方向一句话（候选：{top}），并列出 5 条可验证经历要点",
            "proof": "content/life 会话 plan.json 更新 + 可选写入 evidence",
        },
        {
            "when": "第3-6周",
            "what": f"围绕主码维度完成 1 个可演示小项目"
            + (f"（优先用到 {skills[0]}）" if skills else ""),
            "proof": "仓库/笔记链接（新 evidence，勿伪造过往）",
        },
        {
            "when": "第7-10周",
            "what": "用 Compass「求职准备」对 2-3 个真实 JD 跑匹配与缺口诊断",
            "proof": "jobs/*/match.json + diagnoses/*/report.md",
        },
        {
            "when": "第11-12周",
            "what": "根据诊断补齐 P0 缺口；更新简历叙事，准备 2 个 STAR 故事",
            "proof": "resume.md + interviews/*/session.md",
        },
    ]


def _narrative_offline(extract: dict, scores: dict, paths: list[dict], route: str) -> str:
    code = "".join(sorted(DIMS, key=lambda d: (-scores.get(d, 0), d))[:3])
    lines = [
        f"基于规则分析（route={route}），Holland 倾向码约 **{code}**。",
        f"识别到领域/技能：{', '.join((extract.get('domains') or []) + (extract.get('skills') or [])[:6]) or '（较少）'}。",
        f"教育/年限信号：{', '.join(extract.get('education_or_tenure') or []) or '（不足）'}。",
        f"约束信号：{', '.join(extract.get('constraints') or []) or '（不足）'}。",
        "",
        "优先探索路径：",
    ]
    for p in paths[:3]:
        lines.append(f"- **{p['title']}**（契合 {p['fit_score']}）：{p['why']}")
    lines.append("")
    lines.append("不确定或未在输入中证实的推断均标为 UNVERIFIED，请勿当作已发生经历写入简历。")
    return "\n".join(lines)


def _llm_narrative(text: str, extract: dict, scores: dict, paths: list[dict]) -> str:
    prompt = (
        "你是严谨的生涯顾问。根据用户经历摘要与 RIASEC 分数，写中文分析（400字内）。"
        "只依据给定信号；不确定处写 UNVERIFIED；不要编造公司/学历/业绩。"
        f"\n经历摘录:\n{text[:2500]}\n"
        f"\n信号JSON:\n{json.dumps(extract, ensure_ascii=False)[:1500]}\n"
        f"\nRIASEC:\n{json.dumps(scores, ensure_ascii=False)}\n"
        f"\n候选路径:\n{json.dumps(paths, ensure_ascii=False)[:1200]}\n"
    )
    res = chat(
        [
            {"role": "system", "content": "Career counselor; evidence-first; Chinese."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    if res.get("used_llm") and (res.get("text") or "").strip():
        return res["text"].strip()
    return ""


def build_plan_payload(
    *,
    session_id: str,
    text: str,
    extract: dict,
    scores: dict[str, int],
    score_meta: dict,
    route: str,
    score_source: str,
) -> dict:
    paths = _role_suggestions(scores, extract)
    actions = _actions_90d(extract, scores, paths)
    narrative = _llm_narrative(text, extract, scores, paths) or _narrative_offline(
        extract, scores, paths, route
    )
    dims_meta = (load_riasec_bank().get("meta") or {}).get("dimensions") or {}
    dimensions = []
    for d in DIMS:
        meta = dims_meta.get(d) or {}
        dimensions.append(
            {
                "code": d,
                "name": meta.get("name") or d,
                "blurb": meta.get("blurb") or "",
                "score": scores.get(d, 0),
            }
        )
    target_roles = []
    for p in paths:
        target_roles.extend(p.get("roles") or [])
    target_roles = _uniq(target_roles, 8)
    return {
        "session_id": session_id,
        "date": date.today().isoformat(),
        "route": route,
        "score_source": score_source,
        "confidence": extract.get("confidence"),
        "holland_code": score_meta.get("holland_code"),
        "scores": scores,
        "dimensions": dimensions,
        "analysis": narrative,
        "paths": paths,
        "actions_90d": actions,
        "target_roles": target_roles,
        "handoff_jd_hint": (
            "目标方向（来自职业探索）：\n"
            + "\n".join(f"- {r}" for r in target_roles[:5])
            + "\n\n请粘贴具体职位描述（JD）以继续匹配与简历准备。"
        ),
        "disclaimer": "本报告基于 Holland RIASEC 自研改编题与规则/LLM 叙述，非商业量表结果，不作心理诊断。",
    }


def render_report_md(plan: dict) -> str:
    scores = plan.get("scores") or {}
    lines = [
        f"# 职业探索报告 · {plan.get('session_id')}",
        "",
        f"- **日期**: {plan.get('date')}",
        f"- **路径**: {plan.get('route')}（计分来源: {plan.get('score_source')}）",
        f"- **置信度**: {plan.get('confidence')}",
        f"- **Holland 码**: {plan.get('holland_code')}",
        "",
        "## 六维得分",
        "",
        "| 维度 | 得分 |",
        "|------|------|",
    ]
    for d in DIMS:
        lines.append(f"| {d} | {scores.get(d, 0)} |")
    lines += ["", "## 分析", "", plan.get("analysis") or "", "", "## 可行路径", ""]
    for p in plan.get("paths") or []:
        lines.append(f"### {p.get('rank')}. {p.get('title')}（{p.get('fit_score')}）")
        lines.append(p.get("why") or "")
        roles = ", ".join(p.get("roles") or [])
        if roles:
            lines.append(f"- 角色簇: {roles}")
        lines.append(f"- 备注: {p.get('evidence_note') or ''}")
        lines.append("")
    lines += ["## 近 90 天行动", ""]
    for a in plan.get("actions_90d") or []:
        lines.append(f"- **{a.get('when')}**: {a.get('what')}")
        lines.append(f"  - 证明物: {a.get('proof')}")
    lines += ["", f"> {plan.get('disclaimer') or ''}", ""]
    return "\n".join(lines)


def _radar_svg(scores: dict[str, int], size: int = 280) -> str:
    cx = cy = size / 2
    r = size * 0.36
    n = len(DIMS)
    pts = []
    for i, d in enumerate(DIMS):
        ang = -math.pi / 2 + (2 * math.pi * i / n)
        val = max(0, min(100, scores.get(d, 0))) / 100.0
        x = cx + r * val * math.cos(ang)
        y = cy + r * val * math.sin(ang)
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    axes = []
    labels = []
    for i, d in enumerate(DIMS):
        ang = -math.pi / 2 + (2 * math.pi * i / n)
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        lx = cx + (r + 22) * math.cos(ang)
        ly = cy + (r + 22) * math.sin(ang)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#cbd5e1" stroke-width="1"/>')
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" '
            f'font-size="12" fill="#334155">{html.escape(d)} {scores.get(d, 0)}</text>'
        )
    ring = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e2e8f0"/>'
    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="RIASEC radar">'
        f"{ring}{''.join(axes)}"
        f'<polygon points="{poly}" fill="rgba(43,109,229,0.25)" stroke="#2b6de5" stroke-width="2"/>'
        f"{''.join(labels)}</svg>"
    )


def export_life_html(root: Path, session_id: str) -> dict:
    d = session_dir(root, session_id)
    plan_path = d / "plan.json"
    if not plan_path.is_file():
        raise FileNotFoundError(f"no plan for session {session_id}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    scores = plan.get("scores") or {}
    radar = _radar_svg(scores)
    bars = []
    for dim in plan.get("dimensions") or []:
        sc = int(dim.get("score") or 0)
        bars.append(
            "<div class='dim'>"
            f"<div class='dim-h'><strong>{html.escape(str(dim.get('code')))}</strong> "
            f"{html.escape(str(dim.get('name') or ''))} <span>{sc}</span></div>"
            f"<div class='bar'><i style='width:{sc}%'></i></div>"
            f"<p>{html.escape(str(dim.get('blurb') or ''))}</p></div>"
        )
    path_cards = []
    for p in plan.get("paths") or []:
        path_cards.append(
            "<article class='card'>"
            f"<h3>{html.escape(str(p.get('title')))}</h3>"
            f"<p class='meta'>契合 {p.get('fit_score')} · {html.escape(str(p.get('holland_focus')))}</p>"
            f"<p>{html.escape(str(p.get('why') or ''))}</p>"
            f"<p class='roles'>{html.escape(', '.join(p.get('roles') or []))}</p>"
            "</article>"
        )
    actions = "".join(
        f"<li><strong>{html.escape(str(a.get('when')))}</strong> — "
        f"{html.escape(str(a.get('what')))}<br/><small>{html.escape(str(a.get('proof') or ''))}</small></li>"
        for a in (plan.get("actions_90d") or [])
    )
    analysis = html.escape(plan.get("analysis") or "").replace("\n", "<br/>")
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>职业探索 · {html.escape(session_id)}</title>
<style>
body{{font-family:Segoe UI,system-ui,sans-serif;margin:0;background:#f6f8fb;color:#0f172a}}
.wrap{{max-width:960px;margin:0 auto;padding:28px 20px}}
h1{{font-size:1.5rem;margin:0 0 8px}}
.meta{{color:#64748b;font-size:.9rem}}
.grid{{display:grid;grid-template-columns:280px 1fr;gap:20px;margin:20px 0}}
@media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
.panel{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px}}
.dim{{margin-bottom:12px}}.dim-h{{display:flex;justify-content:space-between;font-size:.9rem}}
.bar{{height:8px;background:#e2e8f0;border-radius:99px;overflow:hidden}}
.bar i{{display:block;height:100%;background:#2b6de5}}
.cards{{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}}
.card{{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px}}
.card h3{{margin:0 0 6px;font-size:1rem}}
.roles{{color:#334155;font-size:.85rem}}
ul{{padding-left:1.1rem}} li{{margin:8px 0}}
.foot{{margin-top:24px;font-size:.8rem;color:#94a3b8}}
</style></head><body><div class="wrap">
<h1>职业探索报告</h1>
<p class="meta">{html.escape(session_id)} · Holland {html.escape(str(plan.get('holland_code') or ''))}
 · 置信度 {plan.get('confidence')}</p>
<div class="grid">
<div class="panel">{radar}</div>
<div class="panel">{''.join(bars)}</div>
</div>
<div class="panel"><h2>分析</h2><p>{analysis}</p></div>
<h2>可行路径</h2><div class="cards">{''.join(path_cards)}</div>
<div class="panel" style="margin-top:20px"><h2>近 90 天行动</h2><ul>{actions}</ul></div>
<p class="foot">{html.escape(str(plan.get('disclaimer') or ''))}</p>
</div></body></html>"""
    out_dir = d / "export"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "report.html"
    html_path.write_text(doc, encoding="utf-8")
    return {"session_id": session_id, "html": str(html_path)}


def _read_input_text(root: Path, session_id: str) -> str:
    p = session_dir(root, session_id) / "input.md"
    if not p.is_file():
        return ""
    raw = p.read_text(encoding="utf-8")
    if "\n---\n" in raw:
        return raw.split("\n---\n", 1)[1].strip()
    return raw


def _save_plan(root: Path, session_id: str, plan: dict) -> dict:
    d = session_dir(root, session_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / "scores.json").write_text(
        json.dumps(
            {"scores": plan.get("scores"), "holland_code": plan.get("holland_code"), "source": plan.get("score_source")},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    md = render_report_md(plan)
    (d / "report.md").write_text(md, encoding="utf-8")
    exp = export_life_html(root, session_id)
    return {"plan": plan, "report_md": md, "export_html": exp.get("html"), "session_id": session_id}


def explore_life(
    root: Path,
    *,
    text: str | None = None,
    file_path: str | Path | None = None,
    session_id: str | None = None,
) -> dict:
    """Ingest + confidence route; if direct, build full plan; else return assessment questions."""
    meta = ingest_life_input(root, text=text, file_path=file_path, session_id=session_id)
    sid = meta["session_id"]
    body = _read_input_text(root, sid)
    extract = assess_confidence(body)
    d = session_dir(root, sid)
    (d / "extract.json").write_text(json.dumps(extract, ensure_ascii=False, indent=2), encoding="utf-8")

    bank = load_riasec_bank()
    questions = [
        {"id": q["id"], "dim": q["dim"], "text": q["text"]} for q in bank["questions"]
    ]
    base: dict[str, Any] = {
        "session_id": sid,
        "route": extract["route"],
        "confidence": extract["confidence"],
        "extract": extract,
        "questions": questions,
        "scale": bank.get("meta", {}).get("scale"),
        "dimensions_meta": bank.get("meta", {}).get("dimensions"),
        "chars": meta["chars"],
        "warnings": meta.get("warnings") or [],
    }

    if extract["route"] == "direct":
        scores = infer_riasec_from_text(body)
        ranked = sorted(DIMS, key=lambda x: (-scores[x], x))
        score_meta = {"holland_code": "".join(ranked[:3]), "ranked": ranked}
        plan = build_plan_payload(
            session_id=sid,
            text=body,
            extract=extract,
            scores=scores,
            score_meta=score_meta,
            route="direct",
            score_source="inferred_from_text",
        )
        saved = _save_plan(root, sid, plan)
        base.update(
            {
                "ready": True,
                "plan": saved["plan"],
                "report_md": saved["report_md"],
                "export_html": saved["export_html"],
                "scores": scores,
                "holland_code": plan["holland_code"],
            }
        )
    else:
        base.update({"ready": False, "need_assessment": True})
    return base


def answer_life(root: Path, session_id: str, answers: dict | list) -> dict:
    d = session_dir(root, session_id)
    if not d.is_dir():
        raise FileNotFoundError(f"unknown session {session_id}")
    extract = {}
    if (d / "extract.json").is_file():
        extract = json.loads((d / "extract.json").read_text(encoding="utf-8"))
    (d / "answers.json").write_text(
        json.dumps(answers if isinstance(answers, dict) else {"items": answers}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    scored = score_riasec(answers)
    body = _read_input_text(root, session_id)
    plan = build_plan_payload(
        session_id=session_id,
        text=body,
        extract=extract,
        scores=scored["scores"],
        score_meta=scored,
        route="assessment",
        score_source="riasec_likert",
    )
    saved = _save_plan(root, session_id, plan)
    return {
        "session_id": session_id,
        "ready": True,
        "route": "assessment",
        "scored": scored,
        "plan": saved["plan"],
        "report_md": saved["report_md"],
        "export_html": saved["export_html"],
        "scores": scored["scores"],
        "holland_code": scored["holland_code"],
    }


def refine_plan(root: Path, session_id: str, message: str) -> dict:
    d = session_dir(root, session_id)
    plan_path = d / "plan.json"
    if not plan_path.is_file():
        raise FileNotFoundError("plan not ready; complete explore/assessment first")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    msg = (message or "").strip()
    if not msg:
        raise ValueError("empty refine message")

    history_path = d / "refine.jsonl"
    context = json.dumps(
        {
            "holland_code": plan.get("holland_code"),
            "scores": plan.get("scores"),
            "paths": plan.get("paths"),
            "target_roles": plan.get("target_roles"),
        },
        ensure_ascii=False,
    )[:2000]

    reply = ""
    res = chat(
        [
            {
                "role": "system",
                "content": "你是生涯顾问。基于已有规划回答用户追问；不编造经历；不确定标 UNVERIFIED；中文简洁。",
            },
            {
                "role": "user",
                "content": f"已有规划摘要:\n{context}\n\n用户追问:\n{msg}",
            },
        ],
        temperature=0.35,
    )
    if res.get("used_llm") and (res.get("text") or "").strip():
        reply = res["text"].strip()
    else:
        roles = ", ".join(plan.get("target_roles") or [])[:200]
        reply = (
            f"（离线回复）结合 Holland 码 {plan.get('holland_code')} 与方向 {roles}：\n"
            f"关于「{msg}」——建议优先验证路径 #1 的可演示项目，并用真实 JD 在求职准备中匹配。"
            f" 细节 UNVERIFIED，需你补充约束（城市/薪资/年限）后再细化。"
        )

    # lightly update analysis appendix
    appendix = f"\n\n### 交互补充（{date.today().isoformat()}）\n\n**问**: {msg}\n\n**答**: {reply}\n"
    plan["analysis"] = (plan.get("analysis") or "") + appendix
    plan.setdefault("refinements", []).append({"q": msg, "a": reply, "date": date.today().isoformat()})
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"q": msg, "a": reply, "date": date.today().isoformat()}, ensure_ascii=False) + "\n")
    saved = _save_plan(root, session_id, plan)
    return {
        "session_id": session_id,
        "reply": reply,
        "plan": saved["plan"],
        "report_md": saved["report_md"],
        "export_html": saved["export_html"],
    }


def load_life_report(root: Path, session_id: str) -> dict:
    d = session_dir(root, session_id)
    plan_path = d / "plan.json"
    if not plan_path.is_file():
        raise FileNotFoundError(session_id)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    md = (d / "report.md").read_text(encoding="utf-8") if (d / "report.md").is_file() else render_report_md(plan)
    html_p = d / "export" / "report.html"
    return {
        "session_id": session_id,
        "plan": plan,
        "report_md": md,
        "export_html": str(html_p) if html_p.is_file() else None,
        "scores": plan.get("scores"),
        "holland_code": plan.get("holland_code"),
        "handoff_jd_hint": plan.get("handoff_jd_hint"),
    }
