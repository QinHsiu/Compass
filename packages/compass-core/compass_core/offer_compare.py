"""Multi-offer six-dimension compare (compas.txt P1 / CareerForge).

Dimensions: economy / growth / platform / track / lifestyle / risk (1–5).
No live salary APIs — user-supplied scores only.
"""

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
    "risk": "风险可控",  # higher = safer
}


def empty_offer(offer_id: str, title: str = "", company: str = "") -> dict:
    return {
        "id": offer_id,
        "title": title,
        "company": company,
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


def compare_offers(root: Path, ids: list[str]) -> dict:
    offers = [load_offer(root, i.strip()) for i in ids if i.strip()]
    if len(offers) < 1:
        raise ValueError("need at least one offer id")
    # total = sum of dims (risk already "higher=better")
    ranked = []
    for o in offers:
        total = sum(float((o.get("scores") or {}).get(d, 3)) for d in DIMS)
        ranked.append(
            {
                "id": o["id"],
                "title": o.get("title"),
                "company": o.get("company"),
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
        "| rank | id | company | total | avg | " + " | ".join(DIMS) + " |",
        "|------|----|---------|-------|-----|" + "|".join(["------"] * len(DIMS)) + "|",
    ]
    for i, r in enumerate(ranked, 1):
        sc = r["scores"] or {}
        cells = " | ".join(str(sc.get(d, "—")) for d in DIMS)
        lines.append(
            f"| {i} | `{r['id']}` | {r.get('company') or '—'} | {r['total']} | {r['avg']} | {cells} |"
        )
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Scores are **user-supplied** (1–5). No live market percentile.")
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
