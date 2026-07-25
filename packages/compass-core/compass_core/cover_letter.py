"""Evidence-gated cover letter (career-ops / Resume-Matcher parity).

Draft-only: never sends email or submits applications.
Only cites evidence_ids present on the match; never invents experience.
"""

from __future__ import annotations

import json
from pathlib import Path

from .evidence import load_evidence
from .intake import load_profile


def _pick_bullets(root: Path, job_id: str, *, limit: int = 3) -> list[dict]:
    match_path = Path(root) / "jobs" / job_id / "match.json"
    if not match_path.is_file():
        return []
    match = json.loads(match_path.read_text(encoding="utf-8"))
    explain = match.get("match_explain") or {}
    matrix = explain.get("requirement_matrix") or match.get("requirement_matrix") or []
    ev_by_id = {e.id: e for e in load_evidence(root)}
    bullets: list[dict] = []
    seen: set[str] = set()
    for row in matrix:
        if str(row.get("status") or "") not in ("direct", "partial"):
            continue
        for eid in row.get("evidence_ids") or []:
            if eid in seen:
                continue
            ev = ev_by_id.get(eid)
            if not ev:
                continue
            seen.add(eid)
            metrics = getattr(ev, "metrics", "") or ""
            if isinstance(metrics, list):
                metric_s = "；".join(str(m) for m in metrics[:2])
            else:
                metric_s = str(metrics).strip().splitlines()[0] if str(metrics).strip() else ""
            bullets.append(
                {
                    "evidence_id": eid,
                    "requirement": str(row.get("requirement") or row.get("text") or "")[:120],
                    "title": getattr(ev, "title", "") or eid,
                    "metric": metric_s,
                }
            )
            if len(bullets) >= limit:
                return bullets
    # fallback: top evidence
    if not bullets:
        for ev in load_evidence(root)[:limit]:
            bullets.append(
                {
                    "evidence_id": ev.id,
                    "requirement": "",
                    "title": getattr(ev, "title", "") or ev.id,
                    "metric": "",
                }
            )
    return bullets


def build_cover_letter(
    root: Path,
    job_id: str,
    *,
    angle: str = "why",
    lang: str = "zh",
) -> dict:
    """Generate cover letter markdown+json under content/jobs/{id}/cover_letter.*"""
    root = Path(root)
    jd_path = root / "jobs" / job_id / "jd.json"
    if not jd_path.is_file():
        raise FileNotFoundError(f"missing {jd_path}")
    jd = json.loads(jd_path.read_text(encoding="utf-8"))
    title = jd.get("title") or ""
    company = jd.get("company") or ""
    profile = load_profile(root) or {}
    name = profile.get("name") or "〔姓名〕"
    email = (profile.get("links") or {}).get("email") or "〔邮箱〕"
    bullets = _pick_bullets(root, job_id)
    band = ""
    match_path = root / "jobs" / job_id / "match.json"
    if match_path.is_file():
        m = json.loads(match_path.read_text(encoding="utf-8"))
        band = str((m.get("match_explain") or {}).get("recommendation") or "")

    angle = (angle or "why").lower()
    angle_line = {
        "why": f"我对{company or '贵司'}的{title or '该岗位'}感兴趣，因为我的交付可直接对齐岗位硬性要求。",
        "problems": f"从 JD 可见你们关注正确性与稳定性；我过往交付正是围绕这些痛点展开。",
        "approach": "我会用证据门禁方式沟通：只陈述可回溯到 evidence_id 的成果，避免空话。",
        "tone": "语气务实、可核对；若需要一页简历或补充材料，我可立即提供。",
    }.get(angle, "")

    bullet_md = "\n".join(
        f"- **{b['title']}**"
        + (f"：{b['metric']}" if b.get("metric") else "")
        + f"（`{b['evidence_id']}`）"
        + (f" — 对齐：{b['requirement']}" if b.get("requirement") else "")
        for b in bullets
    ) or "- （请先运行 match-explain，确保有 direct/partial 证据行）"

    if lang.startswith("en"):
        body = f"""Dear Hiring Team,

I am applying for {title or "the role"} at {company or "your company"}.
{angle_line}

Evidence-backed fit:
{bullet_md}

I would welcome a short conversation. Thank you for your time.

Best regards,
{name}
{email}
"""
    else:
        body = f"""尊敬的招聘团队：

我申请{company or '贵司'}的「{title or '该岗位'}」。
{angle_line}

与岗位对齐的可验证经历：
{bullet_md}

如需一页简历或补充材料，我可随时提供。感谢审阅。

此致
{name}
{email}
"""

    md = f"""# Cover letter — {job_id}

> Draft-only · evidence-gated · never auto-send  
> angle: `{angle}` · match band: `{band or "—"}`

---

{body.strip()}

---

## Checklist before send

- [ ] 每条经历可在 evidence 中打开核对
- [ ] 未写入 match 中标记为 gap 的技能
- [ ] 收件人 / 公司名已人工确认
"""
    out_dir = root / "jobs" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "cover_letter.md"
    path.write_text(md, encoding="utf-8")
    data = {
        "job_id": job_id,
        "company": company,
        "title": title,
        "angle": angle,
        "band": band,
        "bullets": bullets,
        "path": str(path),
        "disclaimer": "draft_only_evidence_gated",
    }
    (out_dir / "cover_letter.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data
