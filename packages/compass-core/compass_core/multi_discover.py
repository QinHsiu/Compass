"""JobSpy-style multi-source discover — compliant sources only (ATS/feeds/career/companies)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ats_scan import collect_ats, load_portals
from .career_recommend import crawl_career_depth, recommend_jobs
from .feeds import collect_feeds
from .observability import audit_event
from .warehouse import ingest_rows


COMPLIANT_SOURCES = ("ats", "feeds", "companies", "career")


def discover_multi(
    root: Path,
    *,
    sources: list[str] | None = None,
    keyword: str | None = None,
    location: str | None = None,
    board: str | None = None,
    feed: str | None = None,
    career_url: str | None = None,
    limit: int = 20,
    match: bool = True,
    workers: int = 4,
    depth: int = 0,
    fetch_fn=None,
    fetch_html_fn=None,
) -> dict:
    """
    Fan-in discovery like JobSpy, but only Compass-allowed sources.
    ``depth>=1`` enables list→detail crawl on career/companies pages.
    """
    root = Path(root)
    srcs = [s.strip().lower() for s in (sources or list(COMPLIANT_SOURCES)) if s.strip()]
    srcs = [s for s in srcs if s in COMPLIANT_SOURCES]
    if not srcs:
        return {"error": f"no valid sources; use {COMPLIANT_SOURCES}", "jobs": []}

    buckets: dict[str, Any] = {}
    jobs: list[dict] = []
    errors: list[dict] = []

    per = max(3, limit // max(len(srcs), 1) + 2)

    if "ats" in srcs:
        try:
            from .ats_scan import scan_board

            specs = [board] if board else load_portals(root)
            rows = []
            raw_jobs = []
            if specs:
                for spec in specs:
                    scanned = scan_board(spec, limit=per if not board else limit, fetch_fn=fetch_fn)
                    raw_jobs.extend(scanned)
                    if match:
                        rows.extend(
                            collect_ats(
                                root,
                                board=spec,
                                limit=per if not board else limit,
                                match=True,
                                fetch_fn=fetch_fn,
                            )
                        )
            else:
                buckets["ats"] = {"skipped": "no --board and empty portals.yml"}
            if raw_jobs and not match:
                ingest_rows(
                    root,
                    [
                        {
                            "title": j.get("title"),
                            "company": j.get("company"),
                            "url": j.get("url") or "",
                            "raw": (j.get("text") or "")[:8000],
                            "source": f"ats:{j.get('ats')}",
                        }
                        for j in raw_jobs
                    ],
                    source="multi",
                )
                for j in raw_jobs:
                    jobs.append(
                        {
                            "title": j.get("title"),
                            "company": j.get("company"),
                            "url": j.get("url"),
                            "source": f"ats:{j.get('ats') or 'board'}",
                        }
                    )
            else:
                for r in rows:
                    jobs.append(
                        {
                            "title": r.get("title"),
                            "company": r.get("company"),
                            "url": r.get("url"),
                            "source": f"ats:{r.get('ats') or 'board'}",
                            "job_id": r.get("job_id"),
                            "score": r.get("score"),
                            "letter": r.get("letter"),
                        }
                    )
            buckets["ats"] = {"n": len(rows) or len(raw_jobs)}
        except Exception as e:
            errors.append({"source": "ats", "error": str(e)})

    if "feeds" in srcs:
        try:
            out = collect_feeds(
                root,
                feed=feed,
                limit=per,
                match=False,
                fetch_fn=fetch_fn,
            )
            for j in out.get("jobs") or []:
                jobs.append(
                    {
                        "title": j.get("title"),
                        "company": j.get("company"),
                        "url": j.get("url"),
                        "location": j.get("location"),
                        "source": j.get("source") or "feed",
                        "job_id": j.get("job_id"),
                    }
                )
            buckets["feeds"] = {"n": len(out.get("jobs") or []), "errors": out.get("errors")}
        except Exception as e:
            errors.append({"source": "feeds", "error": str(e)})

    if "companies" in srcs:
        try:
            if depth >= 1:
                from .companies import load_companies

                cos = load_companies(root)
                crawled = []
                for c in cos[: max(1, workers * 2)]:
                    crawled.extend(
                        crawl_career_depth(
                            c,
                            limit=max(3, per // max(len(cos), 1) + 2),
                            depth=depth,
                            fetch_html_fn=fetch_html_fn,
                            fetch_fn=fetch_fn,
                        )
                    )
                # filter keyword/location
                kws = [k.strip().lower() for k in (keyword or "").replace("|", ",").split(",") if k.strip()]
                locs = [x.strip().lower() for x in (location or "").replace("|", ",").split(",") if x.strip()]

                def _ok(j: dict) -> bool:
                    blob = f"{j.get('title')} {j.get('text')} {j.get('company')}".lower()
                    if kws and not any(k in blob for k in kws):
                        return False
                    if locs and not any(loc in blob for loc in locs):
                        return False
                    return True

                filtered = [j for j in crawled if _ok(j)][:per]
                ingest_rows(
                    root,
                    [
                        {
                            "title": j.get("title"),
                            "company": j.get("company"),
                            "location": j.get("location") or "",
                            "url": j.get("url") or "",
                            "raw": (j.get("text") or "")[:8000],
                            "source": j.get("source") or "multi_career",
                        }
                        for j in filtered
                    ],
                    source="multi",
                ) if filtered else None
                for j in filtered:
                    jobs.append(
                        {
                            "title": j.get("title"),
                            "company": j.get("company"),
                            "url": j.get("url"),
                            "source": j.get("source") or "companies",
                            "depth": j.get("depth"),
                        }
                    )
                buckets["companies"] = {"n": len(filtered), "mode": "depth"}
            else:
                out = recommend_jobs(
                    root,
                    keyword=keyword,
                    location=location,
                    limit=per,
                    match=False,
                    workers=workers,
                    fetch_fn=fetch_fn,
                    fetch_html_fn=fetch_html_fn,
                )
                for j in out.get("recommended") or []:
                    jobs.append(
                        {
                            "title": j.get("title"),
                            "company": j.get("company"),
                            "url": j.get("url"),
                            "source": j.get("source") or "companies",
                            "job_id": j.get("job_id"),
                            "score_100": j.get("score_100"),
                        }
                    )
                buckets["companies"] = {"n": len(out.get("recommended") or []), "mode": "recommend"}
        except Exception as e:
            errors.append({"source": "companies", "error": str(e)})

    if "career" in srcs and career_url:
        try:
            from .collectors import assert_url_allowed, fetch_url
            from .career_recommend import parse_career_page

            assert_url_allowed(career_url)
            if depth >= 1:
                co = {"name": "career", "career_url": career_url}
                crawled = crawl_career_depth(
                    co, limit=per, depth=depth, fetch_html_fn=fetch_html_fn or fetch_url, fetch_fn=fetch_fn
                )
                for j in crawled:
                    jobs.append(
                        {
                            "title": j.get("title"),
                            "company": j.get("company"),
                            "url": j.get("url"),
                            "source": j.get("source") or "career",
                            "depth": j.get("depth"),
                        }
                    )
                buckets["career"] = {"n": len(crawled), "mode": "depth"}
            else:
                html = (fetch_html_fn or fetch_url)(career_url)
                parsed = parse_career_page(html, base_url=career_url, company="career", limit=per)
                ingest_rows(
                    root,
                    [
                        {
                            "title": j.get("title"),
                            "company": j.get("company"),
                            "url": j.get("url") or "",
                            "raw": (j.get("text") or "")[:8000],
                            "source": "multi_career_url",
                        }
                        for j in parsed
                    ],
                    source="multi",
                )
                for j in parsed:
                    jobs.append(
                        {
                            "title": j.get("title"),
                            "company": j.get("company"),
                            "url": j.get("url"),
                            "source": "career",
                        }
                    )
                buckets["career"] = {"n": len(parsed), "mode": "list"}
        except Exception as e:
            errors.append({"source": "career", "error": str(e)})
    elif "career" in srcs and not career_url:
        buckets["career"] = {"skipped": "pass --url for career list page"}

    # keyword filter on fan-in
    kws = [k.strip().lower() for k in (keyword or "").replace("|", ",").split(",") if k.strip()]
    locs = [x.strip().lower() for x in (location or "").replace("|", ",").split(",") if x.strip()]
    if kws or locs:
        filtered = []
        for j in jobs:
            blob = f"{j.get('title')} {j.get('company')} {j.get('location')}".lower()
            if kws and not any(k in blob for k in kws):
                continue
            if locs and not any(loc in blob for loc in locs):
                continue
            filtered.append(j)
        jobs = filtered

    # optional match top-N (only those without job_id yet and with text elsewhere — skip if no text)
    matched = 0
    if match:
        from .match import match_and_save
        from .warehouse import search_jobs

        for j in jobs[:limit]:
            if j.get("job_id"):
                matched += 1
                continue
            # try warehouse raw by url
            text = ""
            url = j.get("url") or ""
            if url:
                hits = search_jobs(root, url[:40], limit=3)
                for h in hits:
                    if (h.get("url") or "") == url and h.get("raw"):
                        text = h["raw"]
                        break
            if not text:
                title = j.get("title") or ""
                company = j.get("company") or ""
                if title:
                    text = f"# {title}\n**Company**: {company}\n**URL**: {url}\n\n## Description\n(from multi discover)"
            if text:
                try:
                    m = match_and_save(root, text)
                    g = m.grade or {}
                    j["job_id"] = m.job_id
                    j["score"] = m.score
                    j["letter"] = g.get("letter")
                    j["score_100"] = g.get("score_100")
                    matched += 1
                except Exception as e:
                    j["match_error"] = str(e)

    jobs = jobs[:limit]
    out = {
        "mode": "multi",
        "sources": srcs,
        "buckets": buckets,
        "count": len(jobs),
        "matched": matched,
        "jobs": jobs,
        "errors": errors,
        "note": "Compliant sources only — not LinkedIn/Indeed/Boss (see COMPLIANCE.md)",
    }
    out_dir = root / "recommendations"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "multi_latest.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["path"] = str(path)
    try:
        audit_event(root, "discover_multi", count=len(jobs), sources=",".join(srcs))
    except Exception:
        pass
    return out
