"""Keyword/location scout over public ATS boards → match (compas v0.9).

Local Job-Spy style: filter Greenhouse/Lever/Ashby boards, then discover-and-match.
"""

from __future__ import annotations

from pathlib import Path

from .ats_scan import load_portals, scan_board
from .batch_match import save_batch
from .match import match_and_save as _match_and_save


def _loc_blob(job: dict) -> str:
    text = job.get("text") or ""
    # first lines often contain 工作地
    return f"{job.get('title', '')} {text[:800]}".lower()


def filter_jobs(
    jobs: list[dict],
    *,
    keyword: str | None = None,
    location: str | None = None,
) -> list[dict]:
    out = jobs
    if keyword:
        kws = [k.strip().lower() for k in keyword.replace("|", ",").split(",") if k.strip()]
        if kws:
            out = [
                j
                for j in out
                if any(k in (j.get("title") or "").lower() or k in (j.get("text") or "").lower() for k in kws)
            ]
    if location:
        locs = [x.strip().lower() for x in location.replace("|", ",").split(",") if x.strip()]
        if locs:
            out = [j for j in out if any(loc in _loc_blob(j) for loc in locs)]
    return out


def scout(
    root: Path,
    *,
    keyword: str | None = None,
    location: str | None = None,
    boards: list[str] | None = None,
    limit: int = 10,
    match: bool = True,
    fetch_fn=None,
) -> dict:
    """Scan boards, filter, optionally match_and_save; return batch summary dict."""
    root = Path(root)
    specs = list(boards or []) or load_portals(root)
    if not specs:
        raise ValueError(
            "no boards; pass --board greenhouse:slug or fill content/portals.yml"
        )
    collected: list[dict] = []
    per = max(limit * 3, 20)  # over-fetch then filter
    for spec in specs:
        jobs = scan_board(spec, limit=per, fetch_fn=fetch_fn)
        jobs = filter_jobs(jobs, keyword=keyword, location=location)
        for j in jobs:
            row = {
                "title": j.get("title"),
                "company": j.get("company"),
                "url": j.get("url"),
                "ats": j.get("ats"),
                "board": j.get("board"),
            }
            if match:
                m = _match_and_save(root, j["text"])
                g = m.grade or {}
                row.update(
                    {
                        "job_id": m.job_id,
                        "score": m.score,
                        "score_100": g.get("score_100"),
                        "letter": g.get("letter"),
                        "global_1_5": g.get("global_1_5"),
                        "display": g.get("display") or g.get("verdict"),
                        "recommendation": (m.match_explain or {}).get("recommendation"),
                    }
                )
            else:
                row["text_preview"] = (j.get("text") or "")[:200]
            collected.append(row)
            if len(collected) >= limit:
                break
        if len(collected) >= limit:
            break
    collected.sort(
        key=lambda r: float(r.get("score_100") or r.get("global_1_5") or r.get("score") or 0),
        reverse=True,
    )
    summary = save_batch(root, collected[:limit], label="scout")
    summary["keyword"] = keyword
    summary["location"] = location
    summary["boards"] = specs
    return summary
