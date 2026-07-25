"""Local compensation benchmarks lookup (clover comp_benchmarks-style, user/local data)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_ASSET = Path(__file__).resolve().parent / "assets" / "comp_benchmarks.jsonl"


@lru_cache(maxsize=1)
def load_benchmarks() -> list[dict]:
    rows = []
    if _ASSET.is_file():
        for ln in _ASSET.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return rows


def load_user_benchmarks(root: Path) -> list[dict]:
    path = Path(root) / "comp" / "benchmarks.jsonl"
    if not path.is_file():
        return []
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return rows


def lookup_comp(
    root: Path | None = None,
    *,
    title: str = "",
    level: str = "",
    location: str = "",
    limit: int = 10,
) -> dict:
    """FTS-ish filter over bundled + user benchmarks. No live scrape."""
    rows = list(load_benchmarks())
    if root:
        rows = load_user_benchmarks(root) + rows
    t = (title or "").lower()
    lv = (level or "").lower()
    loc = (location or "").lower()
    scored = []
    for r in rows:
        blob = " ".join(
            [
                str(r.get("title") or ""),
                str(r.get("family") or ""),
                str(r.get("level") or ""),
                str(r.get("location") or ""),
                " ".join(r.get("tags") or []),
            ]
        ).lower()
        score = 0
        if t and t in blob:
            score += 3
        elif t:
            for tok in t.split():
                if tok and tok in blob:
                    score += 1
        if lv and lv in blob:
            score += 2
        if loc and loc in blob:
            score += 2
        if score > 0 or (not t and not lv and not loc):
            scored.append((score or 1, r))
    scored.sort(key=lambda x: -x[0])
    hits = [r for _, r in scored[:limit]]
    return {
        "count": len(hits),
        "hits": hits,
        "disclaimer": "local_benchmarks_only_no_live_scrape",
        "hint": "Add rows to content/comp/benchmarks.jsonl to override/extend",
    }


def coach_script(lookup: dict, *, your_cash: float | None = None) -> str:
    hits = lookup.get("hits") or []
    if not hits:
        return "无本地分位命中。请在 content/comp/benchmarks.jsonl 自行补充，或填写 offer.market_p50。"
    top = hits[0]
    p50 = top.get("p50")
    lines = [
        f"参考（本地）：{top.get('title')} / {top.get('level')} @ {top.get('location')}",
        f"p25={top.get('p25')} · p50={p50} · p75={top.get('p75')} ({top.get('currency') or 'CNY'})",
    ]
    if your_cash is not None and p50:
        try:
            ratio = float(your_cash) / float(p50)
            band = "高" if ratio >= 1.05 else ("齐" if ratio >= 0.95 else "低")
            lines.append(f"你的现金 {your_cash} vs p50 → **{band}**（{ratio:.2f}x）")
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    lines.append("仅供谈判准备，非实时市场爬取。")
    return "\n".join(lines)
