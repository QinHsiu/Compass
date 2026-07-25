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
        "score_100": g.get("score_100"),
        "global_1_5": g.get("global_1_5"),
        "display": g.get("display"),
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
        "| letter | score_100 | score | recommendation | title | company | job_id |",
        "|--------|-----------|-------|----------------|-------|---------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| {r.get('letter') or '—'} | {r.get('score_100') or '—'} | {r.get('score')} | "
            f"{r.get('recommendation') or '—'} | {r.get('title')} | {r.get('company')} | `{r.get('job_id')}` |"
        )
    (out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def _read_job_lines(path: Path) -> list[str]:
    lines = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _process_url_or_spec(root: Path, item: str, *, fetch_fn=None) -> dict:
    """Match one URL, board spec, or raw JD path."""
    from .ats_scan import parse_board_spec, scan_board
    from .collectors import fetch_url

    item = item.strip()
    # local file with JD text
    p = Path(item)
    if p.is_file():
        m = match_and_save(root, p.read_text(encoding="utf-8"))
        row = _row_from_match(m)
        row["source"] = str(p)
        return row

    # board spec greenhouse:slug
    if ":" in item and not item.startswith("http"):
        try:
            parse_board_spec(item)
            jobs = scan_board(item, limit=3, fetch_fn=fetch_fn)
            if not jobs:
                return {"error": f"empty board {item}", "source": item}
            m = match_and_save(root, jobs[0]["text"])
            row = _row_from_match(m)
            row["source"] = item
            return row
        except ValueError:
            pass

    # ATS / career URL
    if item.startswith("http"):
        try:
            # try as board URL first
            try:
                ats, slug = parse_board_spec(item)
                jobs = scan_board(f"{ats}:{slug}", limit=5, fetch_fn=fetch_fn)
                # Prefer exact job URL match if present
                hit = next((j for j in jobs if j.get("url") and j["url"].rstrip("/") in item.rstrip("/")), None)
                if not hit and jobs:
                    # single-job greenhouse URL often contains /jobs/ID
                    hit = jobs[0]
                if hit:
                    m = match_and_save(root, hit["text"])
                    row = _row_from_match(m)
                    row["source"] = item
                    return row
            except (ValueError, PermissionError, Exception):
                pass
            # fallback: fetch HTML page text
            if fetch_fn is None:
                html = fetch_url(item)
            else:
                html = str(fetch_fn(item))
            from bs4 import BeautifulSoup

            text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)[:8000]
            body = f"链接：{item}\n\n{text}"
            m = match_and_save(root, body)
            row = _row_from_match(m)
            row["source"] = item
            return row
        except Exception as e:
            return {"error": str(e), "source": item}

    # treat as pasted JD snippet
    m = match_and_save(root, item)
    row = _row_from_match(m)
    row["source"] = "text"
    return row


def batch_from_jobs_file(
    root: Path,
    jobs_file: str | Path,
    *,
    workers: int = 5,
    fetch_fn=None,
) -> list[dict]:
    """Parallel evaluate URLs / board specs listed in a text file (compas v0.10)."""
    root = Path(root)
    path = Path(jobs_file)
    if not path.is_file():
        raise FileNotFoundError(path)
    items = _read_job_lines(path)
    workers = max(1, min(int(workers or 5), 10))
    rows: list[dict] = []

    def _one(it: str) -> dict:
        return _process_url_or_spec(root, it, fetch_fn=fetch_fn)

    if workers == 1 or len(items) <= 1:
        for it in items:
            rows.append(_one(it))
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_one, it) for it in items]
            for fut in as_completed(futs):
                rows.append(fut.result())
    rows.sort(
        key=lambda r: float(r.get("score_100") or r.get("global_1_5") or r.get("score") or 0),
        reverse=True,
    )
    return rows


def list_batches(root: Path, *, limit: int = 20) -> list[dict]:
    """Recent batch summaries for `batch board` CLI."""
    root = Path(root)
    bdir = root / "batches"
    if not bdir.is_dir():
        return []
    rows = []
    for d in sorted(bdir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        sp = d / "summary.json"
        if not sp.is_file():
            continue
        try:
            s = json.loads(sp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        jobs = s.get("jobs") or []
        top = jobs[0] if jobs else {}
        rows.append(
            {
                "batch_id": s.get("batch_id") or d.name,
                "created_at": s.get("created_at"),
                "count": s.get("count") or len(jobs),
                "top_letter": top.get("letter"),
                "top_score_100": top.get("score_100"),
                "top_title": top.get("title"),
                "path": str(sp),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def format_batch_board(rows: list[dict]) -> str:
    lines = [
        "| created_at | batch_id | count | top_letter | top_100 | top_title |",
        "|------------|----------|-------|------------|---------|-----------|",
    ]
    for r in rows:
        lines.append(
            f"| {r.get('created_at') or '—'} | `{r.get('batch_id')}` | {r.get('count')} | "
            f"{r.get('top_letter') or '—'} | {r.get('top_score_100') or '—'} | {r.get('top_title') or '—'} |"
        )
    if len(lines) == 2:
        lines.append("| — | _(no batches)_ | 0 | — | — | — |")
    return "\n".join(lines) + "\n"
