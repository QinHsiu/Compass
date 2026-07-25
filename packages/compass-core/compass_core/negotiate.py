"""Local negotiation pack — no live salary APIs (compas.txt light P2)."""

from __future__ import annotations

import json
from pathlib import Path

from .intake import load_profile


def build_negotiate_pack(root: Path, job_id: str | None = None) -> dict:
    root = Path(root)
    profile = load_profile(root) or {}
    constraints = profile.get("constraints") or {}
    salary = constraints.get("salary") or constraints.get("comp") or profile.get("salary_range")
    title = company = ""
    offer_cash = offer_p50 = None
    if job_id:
        jd_path = root / "jobs" / job_id / "jd.json"
        if jd_path.is_file():
            jd = json.loads(jd_path.read_text(encoding="utf-8"))
            title = jd.get("title") or ""
            company = jd.get("company") or ""
        from .offer_compare import find_offer_for_job

        offr = find_offer_for_job(root, job_id)
        if offr:
            offer_cash = offr.get("cash")
            offer_p50 = offr.get("market_p50")
            if offer_cash is not None:
                salary = salary or offer_cash

    red_flags = [
        "只给期权不给现金底薪、且行权/回购条款不透明",
        "要求先裸辞再谈数字 / 无限期背景调查拖延",
        "口头 offer 长期不发书面、催促立刻签字",
        "总包口径混淆（把加班费/年终「目标」算进保证现金）",
        "竞业范围过宽、补偿过低",
    ]
    questions = [
        "现金底薪 / 签字奖 / 年终结构（保证 vs 目标）分别是多少？",
        "级别与带宽上下限？我若超中位的依据是什么？",
        "期权/RSUs 数量、归属、行权价、回购与税务支持？",
        "入职后第一次调薪窗口？晋升周期？",
        "远程/Hybrid 政策与办公城市补贴？",
    ]
    scripts = [
        f"感谢 offer"
        + (f"（{title} @ {company}）" if title else "")
        + "。我很感兴趣，想对齐总包结构后再回复时间表。",
        "基于我当前区间与市场沟通，更合理的现金底薪落在 "
        + (str(salary) if salary else "〔填写你的区间〕")
        + (
            f"（你录入的 market_p50={offer_p50}）"
            if offer_p50 is not None
            else ""
        )
        + "；若现金有难度，可否用签字奖/年终保证补齐？",
        "我可以在收到书面总包拆分后 N 个工作日内给出决定，避免口头数字误解。",
    ]
    md = f"""# Negotiate pack{" — " + job_id if job_id else ""}

> Local-first template. **No live market percentile** (compas P2 light).
> Fill numbers from your own research; do not invent company comp bands.

## Target role

- title: {title or "—"}
- company: {company or "—"}
- your range hint: {salary or "（在 profile.constraints.salary 填写）"}

## Questions to ask

{chr(10).join(f"- {q}" for q in questions)}

## Red flags

{chr(10).join(f"- {r}" for r in red_flags)}

## Counter scripts

{chr(10).join(f"{i}. {s}" for i, s in enumerate(scripts, 1))}
"""
    out_dir = root / "negotiations"
    if job_id:
        out_dir = out_dir / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "negotiate.md"
    path.write_text(md, encoding="utf-8")
    data = {
        "job_id": job_id,
        "salary_hint": salary,
        "questions": questions,
        "red_flags": red_flags,
        "scripts": scripts,
        "path": str(path),
        "disclaimer": "no_live_market_percentile",
    }
    (out_dir / "negotiate.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data
