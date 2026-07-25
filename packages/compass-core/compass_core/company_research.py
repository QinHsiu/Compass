"""Company research brief + contact checklist (compas v0.10 / career-ops).

Local-first: no LinkedIn scrape. Produces research checklist for human outreach.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", (name or "company").strip().lower())
    return (s.strip("_") or "company")[:40]


def build_research(
    root: Path,
    *,
    company: str | None = None,
    job_id: str | None = None,
) -> dict:
    root = Path(root)
    title = ""
    ats_hint = ""
    url = ""
    if job_id:
        jd_path = root / "jobs" / job_id / "jd.json"
        if jd_path.is_file():
            jd = json.loads(jd_path.read_text(encoding="utf-8"))
            company = company or jd.get("company") or job_id
            title = jd.get("title") or ""
            url = jd.get("url") or ""
            from .posting_liveness import detect_ats

            ats_hint = detect_ats(url) if url else ""
    company = (company or "Unknown").strip()
    slug = _slug(company)
    out_dir = root / "research" / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    domain_guess = re.sub(r"[^a-z0-9.-]", "", company.lower().replace(" ", "")) + ".com"
    emails = [
        f"jobs@{domain_guess}",
        f"careers@{domain_guess}",
        f"talent@{domain_guess}",
        f"hr@{domain_guess}",
    ]
    checklist = [
        "在公司官网 /Careers 确认岗位仍开放（勿依赖第三方快照）",
        "查公开博客/Tech Talk/开源仓库，准备 1 条公司特定洞察（非空话）",
        "招聘邮箱：优先官网公布的 jobs@ / careers@（下列为猜测模式，需人工验证）",
        "团队公开渠道：公司工程博客评论、会议演讲者邮箱、开源维护者（禁止 LinkedIn 未授权爬取）",
        "内推：仅通过已认识的同事/校友转介；不批量冷邮件骚扰",
        "申请前：用 Compass match/grade 确认 ≥ 探索线，再写简短「研究备注」进 track note",
    ]
    md = f"""# Company research: {company}

> Local checklist. **No LinkedIn scrape.** Verify emails before sending.

## Role context

- company: {company}
- title: {title or "—"}
- job_id: {job_id or "—"}
- posting_url: {url or "—"}
- ats_hint: {ats_hint or "unknown"}

## Public footprint (fill in)

- careers page:
- eng blog / open source:
- recent news (optional):

## Contact mining checklist

{chr(10).join(f"- [ ] {c}" for c in checklist)}

## Guessed recruiting inboxes (verify!)

{chr(10).join(f"- `{e}`" for e in emails)}

## Outreach draft (edit)

Subject: Re {title or "role"} — evidence-backed interest

Hi — I matched this role via Compass (evidence-gated). One concrete fit:
〔cite evidence_id + metric〕. Happy to share a one-pager or chat 15m.
"""
    path = out_dir / "brief.md"
    path.write_text(md, encoding="utf-8")
    data = {
        "company": company,
        "slug": slug,
        "job_id": job_id,
        "title": title,
        "url": url,
        "ats_hint": ats_hint,
        "emails_guess": emails,
        "checklist": checklist,
        "path": str(path),
        "disclaimer": "no_linkedin_scrape",
    }
    (out_dir / "brief.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data
