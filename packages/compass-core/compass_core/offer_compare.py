"""Multi-offer compare with cash/equity/level + user market_p50 (compas v0.9)."""

from __future__ import annotations

import json
from pathlib import Path

DIMS = ("economy", "growth", "platform", "track", "lifestyle", "risk")
DIM_ZH = {
    "economy": "经济价值",
    "growth": "成长价值",
    "platform": "平台价值",
    "track": "赛道价值",
    "lifestyle": "生活质量",
    "risk": "风险可控",
}


def empty_offer(offer_id: str, title: str = "", company: str = "") -> dict:
    return {
        "id": offer_id,
        "title": title,
        "company": company,
        "cash": None,
        "equity": None,
        "level": "",
        "commute": "",
        "track_outlook": "",
        "market_p50": None,  # user-entered; NOT live Level.fyi
        "scores": {d: 3 for d in DIMS},
        "notes": "",
    }


def load_offer(root: Path, offer_id: str) -> dict:
    path = Path(root) / "offers" / f"{offer_id}.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("id", offer_id)
    scores = data.get("scores") or {}
    data["scores"] = {d: float(scores.get(d, 3)) for d in DIMS}
    for k in ("cash", "equity", "market_p50", "level", "commute", "track_outlook"):
        data.setdefault(k, None if k in ("cash", "equity", "market_p50") else "")
    return data


def save_offer(root: Path, offer: dict) -> Path:
    root = Path(root)
    oid = offer.get("id") or "offer"
    out = root / "offers"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{oid}.json"
    path.write_text(json.dumps(offer, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def radar_points(offer: dict) -> list[dict]:
    scores = offer.get("scores") or {}
    return [{"dim": d, "label": DIM_ZH[d], "value": float(scores.get(d, 3))} for d in DIMS]


def vs_market_p50(cash, market_p50) -> str:
    if cash is None or market_p50 is None:
        return "未填"
    try:
        c, p = float(cash), float(market_p50)
    except (TypeError, ValueError):
        return "未填"
    if p <= 0:
        return "未填"
    ratio = c / p
    if ratio >= 1.08:
        return "高"
    if ratio >= 0.95:
        return "齐"
    return "低"


def compare_offers(root: Path, ids: list[str]) -> dict:
    offers = [load_offer(root, i.strip()) for i in ids if i.strip()]
    if len(offers) < 1:
        raise ValueError("need at least one offer id")
    ranked = []
    for o in offers:
        total = sum(float((o.get("scores") or {}).get(d, 3)) for d in DIMS)
        ranked.append(
            {
                "id": o["id"],
                "title": o.get("title"),
                "company": o.get("company"),
                "cash": o.get("cash"),
                "equity": o.get("equity"),
                "level": o.get("level"),
                "commute": o.get("commute"),
                "track_outlook": o.get("track_outlook"),
                "market_p50": o.get("market_p50"),
                "vs_p50": vs_market_p50(o.get("cash"), o.get("market_p50")),
                "total": round(total, 1),
                "avg": round(total / len(DIMS), 2),
                "radar": radar_points(o),
                "scores": o.get("scores"),
            }
        )
    ranked.sort(key=lambda r: r["total"], reverse=True)
    lines = [
        "# Offer compare",
        "",
        "| rank | id | company | level | cash | market_p50 | vs_p50 | total | avg |",
        "|------|----|---------|-------|------|------------|--------|-------|-----|",
    ]
    for i, r in enumerate(ranked, 1):
        lines.append(
            f"| {i} | `{r['id']}` | {r.get('company') or '—'} | {r.get('level') or '—'} | "
            f"{r.get('cash') if r.get('cash') is not None else '—'} | "
            f"{r.get('market_p50') if r.get('market_p50') is not None else '—'} | "
            f"**相对 P50：{r.get('vs_p50')}** | {r['total']} | {r['avg']} |"
        )
    lines.append("")
    lines.append("## Radar scores")
    lines.append("")
    lines.append("| id | " + " | ".join(DIMS) + " |")
    lines.append("|----|" + "|".join(["------"] * len(DIMS)) + "|")
    for r in ranked:
        sc = r["scores"] or {}
        cells = " | ".join(str(sc.get(d, "—")) for d in DIMS)
        lines.append(f"| `{r['id']}` | {cells} |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Scores and `market_p50` are **user-supplied**. No live Level.fyi scrape.")
    lines.append("- `vs_p50`: 高 ≥108% · 齐 95–108% · 低 <95% of your entered P50.")
    lines.append("- Prefer higher `risk` = more controllable / safer offer.")
    md = "\n".join(lines) + "\n"
    out_dir = Path(root) / "offers"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "compare.md"
    md_path.write_text(md, encoding="utf-8")
    summary = {"offers": ranked, "path": str(md_path)}
    (out_dir / "compare.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def find_offer_for_job(root: Path, job_id: str) -> dict | None:
    """Best-effort: offer whose id/job_id/notes mention job_id."""
    d = Path(root) / "offers"
    if not d.is_dir():
        return None
    for p in d.glob("*.json"):
        if p.name.startswith("compare"):
            continue
        try:
            o = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if o.get("job_id") == job_id or o.get("id") == job_id:
            return o
        if job_id and job_id in str(o.get("notes") or ""):
            return o
    return None
