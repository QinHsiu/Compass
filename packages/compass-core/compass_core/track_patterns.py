"""Rejection / skip pattern analysis from track board (career-ops patterns parity)."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .track import load_board


def analyze_patterns(root: Path) -> dict:
    """Summarize track outcomes → targeting advice (local-only)."""
    root = Path(root)
    board = load_board(root)
    items = list(board.get("items") or [])
    by_status: Counter[str] = Counter()
    by_band: Counter[str] = Counter()
    rejected_bands: Counter[str] = Counter()
    skipped: list[str] = []
    rejected: list[dict] = []
    for it in items:
        st = str(it.get("status") or "unknown")
        by_status[st] += 1
        band = str(it.get("match_band") or "unknown")
        by_band[band] += 1
        if st == "rejected":
            rejected_bands[band] += 1
            rejected.append(
                {
                    "job_id": it.get("job_id"),
                    "company": it.get("company"),
                    "title": it.get("title"),
                    "match_band": band,
                    "note": (it.get("note") or "")[:160],
                }
            )
        if st == "wishlist" and it.get("suggested_action") == "do_not_apply":
            skipped.append(str(it.get("job_id")))
        if band == "skip":
            skipped.append(str(it.get("job_id")))

    n = len(items) or 1
    advice: list[str] = []
    if by_status.get("rejected", 0) >= 2 and rejected_bands:
        top_band, _ = rejected_bands.most_common(1)[0]
        advice.append(
            f"拒信集中在 match_band=`{top_band}` — 对该档岗位先跑 resume-patch / bridge，再投。"
        )
    if by_band.get("skip", 0) / n > 0.4:
        advice.append("跳过率偏高：收紧 discover 关键词，或先更新 profile.target_roles。")
    if by_status.get("ghosted", 0) >= 2:
        advice.append("多次 ghosted：检查 follow_up_due 与 apply-email 跟进节奏。")
    if by_status.get("applied", 0) + by_status.get("interviewing", 0) == 0 and len(items) >= 3:
        advice.append("看板有意向但未投递：对 strong/plausible 档执行 cover-letter + track applied。")
    if not advice:
        advice.append("样本不足或分布健康：继续记录 outcome（calibrate record）以校准。")

    md = f"""# Track patterns

> Local analysis of `track/board.json` · career-ops-style targeting feedback

## Counts

| Status | N |
|:-------|--:|
{chr(10).join(f"| {k} | {v} |" for k, v in sorted(by_status.items()))}

## Match bands

| Band | N |
|:-----|--:|
{chr(10).join(f"| {k} | {v} |" for k, v in sorted(by_band.items()))}

## Rejected (sample)

{chr(10).join(f"- `{r.get('job_id')}` · {r.get('company')} · band={r.get('match_band')} · {r.get('note')}" for r in rejected[:12]) or "- （无）"}

## Advice

{chr(10).join(f"- {a}" for a in advice)}
"""
    out_dir = root / "track"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "patterns.md"
    path.write_text(md, encoding="utf-8")
    data = {
        "total": len(items),
        "by_status": dict(by_status),
        "by_band": dict(by_band),
        "rejected_bands": dict(rejected_bands),
        "rejected": rejected,
        "skipped_job_ids": sorted(set(skipped)),
        "advice": advice,
        "path": str(path),
    }
    (out_dir / "patterns.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return data
