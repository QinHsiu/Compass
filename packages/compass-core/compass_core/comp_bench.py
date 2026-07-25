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
    agg = lookup.get("aggregate")
    if agg and agg.get("p50"):
        top = agg
        live = lookup.get("mode") == "live"
    elif hits:
        top = hits[0]
        live = str(top.get("source") or "").startswith("live") or top.get("source") in (
            "offershow",
            "http_live",
            "job_posting",
            "live_aggregate",
        )
    else:
        return (
            "无薪资命中。可：`comp lookup --live --i-accept-tos-risk`（需配置 COMPASS_OFFERSHOW_API），"
            "或 `comp ingest-live --file capture.json`，或填写 content/comp/benchmarks.jsonl / offer.market_p50。"
        )
    p50 = top.get("p50")
    tag = "实时聚合" if (lookup.get("mode") == "live" or live) else "本地"
    lines = [
        f"参考（{tag}）：{top.get('title')} / {top.get('level') or '—'} @ {top.get('location') or '—'}",
        f"p25={top.get('p25')} · p50={p50} · p75={top.get('p75')} ({top.get('currency') or 'CNY'})"
        + (f" · n={top.get('sample_n')}" if top.get("sample_n") else ""),
    ]
    if your_cash is not None and p50:
        try:
            ratio = float(your_cash) / float(p50)
            band = "高" if ratio >= 1.05 else ("齐" if ratio >= 0.95 else "低")
            lines.append(f"你的现金 {your_cash} vs p50 → **{band}**（{ratio:.2f}x）")
        except (TypeError, ValueError, ZeroDivisionError):
            pass
    if lookup.get("mode") == "live":
        lines.append("实时源：OfferShow 兼容 API / 抓包导入 / 本地 JD 薪资带；遵守平台 ToS。")
    else:
        lines.append("本地基准；加 --live 可拉实时（需配置或 ingest）。")
    return "\n".join(lines)


def lookup_comp_merged(
    root: Path | None = None,
    *,
    title: str = "",
    level: str = "",
    location: str = "",
    company: str = "",
    query: str = "",
    limit: int = 10,
    live: bool = False,
    sources: list[str] | None = None,
    accept_tos_risk: bool = False,
    fetch_fn=None,
) -> dict:
    """Local benchmarks, optionally merged with live OfferShow/HTTP/JD sources."""
    local = lookup_comp(root, title=title or query, level=level, location=location, limit=limit)
    if not live:
        return local
    if root is None:
        return {**local, "errors": [{"error": "live_requires_root"}]}
    from .comp_live import live_lookup

    live_out = live_lookup(
        root,
        query=query or title,
        title=title,
        company=company,
        location=location,
        level=level,
        sources=sources,
        accept_tos_risk=accept_tos_risk,
        fetch_fn=fetch_fn,
        limit=max(limit, 30),
    )
    hits = list(live_out.get("hits") or []) + list(local.get("hits") or [])
    agg = live_out.get("aggregate") or {}
    if agg.get("p50"):
        # put aggregate first for coach
        hits = [agg] + hits
    return {
        "mode": "live",
        "count": len(hits),
        "hits": hits[:limit],
        "aggregate": agg,
        "sources_used": live_out.get("sources_used"),
        "errors": live_out.get("errors"),
        "disclaimer": live_out.get("disclaimer"),
        "query": live_out.get("query"),
        "hint": "Configure COMPASS_OFFERSHOW_API or comp ingest-live; see docs/COMPLIANCE.md",
    }
