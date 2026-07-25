"""Company / portal watchlist rescan — new postings only (Job Seek / JobSignal pattern)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .ats_scan import load_portals, scan_board
from .career_recommend import crawl_company
from .companies import load_companies
from .match import match_and_save
from .observability import audit_event, evaluate_alerts
from .warehouse import existing_urls, ingest_rows


def _utcnow_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def watch_scan(
    root: Path,
    *,
    limit: int = 30,
    match: bool = True,
    dry_run: bool = False,
    workers: int = 4,
    fetch_fn=None,
    fetch_html_fn=None,
) -> dict:
    """Rescan companies.yml + portals.yml; only new URLs (vs warehouse) are matched."""
    root = Path(root)
    known = existing_urls(root)
    collected: list[dict] = []
    errors: list[dict] = []

    # portals
    for spec in load_portals(root):
        try:
            jobs = scan_board(spec, limit=max(5, limit // 2), fetch_fn=fetch_fn)
            for j in jobs:
                j = dict(j)
                j["source"] = f"watch_ats:{j.get('ats')}"
                collected.append(j)
        except Exception as e:
            errors.append({"portal": spec, "error": str(e)})

    # companies
    cos = load_companies(root)
    for c in cos:
        try:
            jobs = crawl_company(
                c,
                limit=max(5, limit // max(len(cos), 1) + 3),
                fetch_fn=fetch_fn,
                fetch_html_fn=fetch_html_fn,
            )
            for j in jobs:
                j = dict(j)
                j.setdefault("source", "watch_career")
                collected.append(j)
        except Exception as e:
            errors.append({"company": c.get("name"), "error": str(e)})

    new_jobs: list[dict] = []
    seen_url: set[str] = set()
    for j in collected:
        url = (j.get("url") or "").strip()
        key = url or f"{j.get('company')}|{j.get('title')}"
        if key in seen_url:
            continue
        seen_url.add(key)
        if url and url in known:
            continue
        if not url and key in known:
            continue
        new_jobs.append(j)

    new_jobs = new_jobs[:limit]
    matched: list[dict] = []
    if not dry_run and new_jobs:
        ingest_rows(
            root,
            [
                {
                    "title": j.get("title"),
                    "company": j.get("company"),
                    "location": j.get("location") or "",
                    "url": j.get("url") or "",
                    "raw": (j.get("text") or "")[:8000],
                    "source": j.get("source") or "watch",
                }
                for j in new_jobs
            ],
            source="watch",
        )
        if match:
            for j in new_jobs:
                row = {
                    "title": j.get("title"),
                    "company": j.get("company"),
                    "url": j.get("url"),
                    "source": j.get("source"),
                }
                if j.get("text"):
                    try:
                        m = match_and_save(root, j["text"])
                        g = m.grade or {}
                        row.update(
                            {
                                "job_id": m.job_id,
                                "score": m.score,
                                "letter": g.get("letter"),
                                "score_100": g.get("score_100"),
                                "recommendation": (m.match_explain or {}).get("recommendation"),
                            }
                        )
                    except Exception as e:
                        row["match_error"] = str(e)
                matched.append(row)

    summary = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scanned": len(collected),
        "known_urls": len(known),
        "new": len(new_jobs),
        "matched": len(matched),
        "dry_run": dry_run,
        "new_jobs": [
            {"title": j.get("title"), "company": j.get("company"), "url": j.get("url"), "source": j.get("source")}
            for j in new_jobs
        ],
        "results": matched,
        "errors": errors,
        "companies": len(cos),
        "portals": len(load_portals(root)),
    }

    out_dir = root / "batches" / f"watch_{_utcnow_slug()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "summary.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["path"] = str(path)

    try:
        audit_event(root, "watch_scan", count=len(new_jobs), scanned=len(collected))
        if not dry_run and new_jobs:
            evaluate_alerts(root)
    except Exception:
        pass

    return summary
