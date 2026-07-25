"""Batch match multiple jobs (compas.txt P1 / career-ops batch)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from .ats_scan import collect_ats
from .match import MatchResult, match_and_save


def _utcnow_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _row_from_match(m: MatchResult) -> dict:
    g = m.to_dict().get("grade") or {}
    return {
        "job_id": m.job_id,
        "title": m.title,
        "company": m.company,
        "score": m.score,
        "matrix_score": (m.match_explain or {}).get("matrix_score"),
        "recommendation": (m.match_explain or {}).get("recommendation"),
        "letter": g.get("letter"),
        "global_1_5": g.get("global_1_5"),
        "verdict": g.get("verdict"),
    }


def match_existing_jobs(root: Path, *, workers: int = 4) -> list[dict]:
    """Re-match all jobs/*/jd.json (read raw_text)."""
    root = Path(root)
    jobs_dir = root / "jobs"
    if not jobs_dir.is_dir():
        return []
    paths = sorted(p for p in jobs_dir.iterdir() if p.is_dir() and (p / "jd.json").is_file())

    def _one(p: Path) -> dict:
        data = json.loads((p / "jd.json").read_text(encoding="utf-8"))
        text = data.get("raw_text") or ""
        if not text:
            text = f"职位：{data.get('title')}\n公司：{data.get('company')}\n" + "\n".join(
                data.get("hard_requirements") or []
            )
        m = match_and_save(root, text, job_id=data.get("job_id") or p.name)
        return _row_from_match(m)

    rows: list[dict] = []
    workers = max(1, min(workers, 4))
    if workers == 1 or len(paths) <= 1:
        for p in paths:
            rows.append(_one(p))
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_one, p): p for p in paths}
            for fut in as_completed(futs):
                rows.append(fut.result())
    rows.sort(key=lambda r: float(r.get("global_1_5") or r.get("score") or 0), reverse=True)
    return rows


def batch_from_ats(root: Path, board: str, *, limit: int = 10) -> list[dict]:
    results = collect_ats(root, board=board, limit=limit, match=True)
    # enrich letter if missing (older path)
    for r in results:
        if r.get("letter"):
            continue
        mid = r.get("job_id")
        if not mid:
            continue
        mp = root / "jobs" / mid / "match.json"
        if mp.is_file():
            m = json.loads(mp.read_text(encoding="utf-8"))
            g = m.get("grade") or {}
            r["letter"] = g.get("letter")
            r["global_1_5"] = g.get("global_1_5")
            r["verdict"] = g.get("verdict")
            r["recommendation"] = (m.get("match_explain") or {}).get("recommendation")
    results.sort(key=lambda r: float(r.get("global_1_5") or r.get("score") or 0), reverse=True)
    return results


def save_batch(root: Path, rows: list[dict], *, label: str = "batch") -> dict:
    root = Path(root)
    bid = f"{label}_{_utcnow_slug()}"
    out = root / "batches" / bid
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "batch_id": bid,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "count": len(rows),
        "jobs": rows,
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        f"# Batch {bid}",
        "",
        f"count={len(rows)}",
        "",
        "| letter | global | score | recommendation | title | company | job_id |",
        "|--------|--------|-------|----------------|-------|---------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| {r.get('letter') or '—'} | {r.get('global_1_5') or '—'} | {r.get('score')} | "
            f"{r.get('recommendation') or '—'} | {r.get('title')} | {r.get('company')} | `{r.get('job_id')}` |"
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
