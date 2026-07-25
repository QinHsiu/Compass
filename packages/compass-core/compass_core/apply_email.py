"""Application email drafts (career-ops email mode parity).

Modes: recruiter | referral | cold. Draft-only — never sends.
"""

from __future__ import annotations

import json
from pathlib import Path

from .cover_letter import _pick_bullets
from .intake import load_profile


def build_apply_email(
    root: Path,
    job_id: str,
    *,
    mode: str = "recruiter",
    referrer: str = "",
) -> dict:
    root = Path(root)
    jd_path = root / "jobs" / job_id / "jd.json"
    if not jd_path.is_file():
        raise FileNotFoundError(f"missing {jd_path}")
    jd = json.loads(jd_path.read_text(encoding="utf-8"))
    title = jd.get("title") or ""
    company = jd.get("company") or ""
    url = jd.get("url") or ""
    profile = load_profile(root) or {}
    name = profile.get("name") or "〔姓名〕"
    email = (profile.get("links") or {}).get("email") or "〔邮箱〕"
    bullets = _pick_bullets(root, job_id, limit=2)
    fit_lines = [
        f"- {b['title']}"
        + (f"：{b['metric']}" if b.get("metric") else "")
        + f"（{b['evidence_id']}）"
        for b in bullets
    ]
    fit_block = "\n".join(fit_lines) or "- 〔先运行 match-explain 注入证据〕"

    mode = (mode or "recruiter").lower()
    if mode == "referral":
        who = referrer or "〔内推人姓名〕"
        subject = f"内推申请 · {title or '岗位'} · {name}"
        body = f"""Hi {who}，

想请你帮忙内推{company or '公司'}的「{title or '岗位'}」。
我与岗位对齐的两点（均可回溯证据）：

{fit_block}

附件：一页简历（已按 JD 门禁改写）。岗位链接：{url or '〔粘贴 JD URL〕'}
感谢！

{name}
{email}
"""
    elif mode == "cold":
        subject = f"关于 {title or '开放岗位'} — {name}"
        body = f"""您好，

冒昧联系。我关注到{company or '贵司'}的「{title or '岗位'}」，希望自荐。
简要匹配点：

{fit_block}

如方便，可否安排 15 分钟沟通，或告知正式投递渠道？感谢。

{name}
{email}
"""
    else:  # recruiter
        subject = f"Application · {title or 'Role'} · {name}"
        body = f"""您好，

我通过官网/ATS 申请「{title or '该岗位'}」({company or '贵司'})，附上简历供审阅。
与 JD 对齐的可验证点：

{fit_block}

岗位链接：{url or '〔粘贴〕'}
期待您的回复。

{name}
{email}
"""

    md = f"""# Application email — {job_id}

> Draft-only · **never sends / never submits** · mode=`{mode}`

## Subject

`{subject}`

## Body

{body.strip()}

## Attachment checklist

- [ ] 一页简历 PDF/HTML（`resume-patch` 产物）
- [ ] 可选：cover_letter.md
- [ ] 收件人已人工核实（勿群发猜测邮箱）
"""
    out_dir = root / "jobs" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "apply_email.md"
    path.write_text(md, encoding="utf-8")
    data = {
        "job_id": job_id,
        "mode": mode,
        "subject": subject,
        "body": body.strip(),
        "bullets": bullets,
        "path": str(path),
        "disclaimer": "draft_only_never_send",
    }
    (out_dir / "apply_email.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data
