"""Public remote job feeds (Remotive / Arbeitnow) — compliant APIs, not Indeed proxies."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .collectors import DEFAULT_UA, assert_url_allowed, fetch_url
from .match import match_and_save
from .warehouse import ingest_rows

# Built-in public endpoints (override via content/feeds.yml)
BUILTIN_FEEDS: dict[str, dict[str, str]] = {
    "remotive": {
        "url": "https://remotive.com/api/remote-jobs",
        "kind": "remotive_json",
        "note": "public Remotive API",
    },
    "arbeitnow": {
        "url": "https://www.arbeitnow.com/api/job-board-api",
        "kind": "arbeitnow_json",
        "note": "public Arbeitnow job board API",
    },
}

FEED_HOST_ALLOW = {
    "remotive.com",
    "www.remotive.com",
    "arbeitnow.com",
    "www.arbeitnow.com",
}


def _assert_feed_host(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    assert_url_allowed(url)
    # allow built-in + any non-blocklisted (user feeds.yml); soft hint for builtins
    if host not in FEED_HOST_ALLOW and host:
        # still OK if not blocklisted — user-configured public feeds
        pass


def load_feeds_config(root: Path) -> dict[str, dict]:
    """Merge builtin + content/feeds.yml (simple YAML: name: url lines or feeds:)."""
    feeds = {k: dict(v) for k, v in BUILTIN_FEEDS.items()}
    root = Path(root)
    for name in ("feeds.yml", "feeds.yaml", "feeds.json"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if name.endswith(".json"):
            data = json.loads(text)
        else:
            data = _parse_simple_feeds(text)
        if isinstance(data, dict):
            items = data.get("feeds") or data
            if isinstance(items, dict):
                for k, v in items.items():
                    if str(k) in ("feeds",):
                        continue
                    if isinstance(v, str):
                        feeds[str(k)] = {"url": v, "kind": "auto", "note": "user"}
                    elif isinstance(v, dict) and v.get("url"):
                        feeds[str(k)] = {
                            "url": str(v["url"]),
                            "kind": str(v.get("kind") or "auto"),
                            "note": str(v.get("note") or "user"),
                        }
        break
    return feeds


def _parse_simple_feeds(text: str) -> dict:
    feeds: dict[str, str] = {}
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        m = re.match(r"^-\s+(\w+)\s*:\s*(https?://\S+)\s*$", ln)
        if m:
            feeds[m.group(1)] = m.group(2)
            continue
        m = re.match(r"^(\w+)\s*:\s*(https?://\S+)\s*$", ln)
        if m and m.group(1).lower() != "feeds":
            feeds[m.group(1)] = m.group(2)
    return {"feeds": feeds}


def _fetch_json(url: str, *, fetch_fn=None) -> Any:
    _assert_feed_host(url)
    if fetch_fn:
        raw = fetch_fn(url)
        if isinstance(raw, (dict, list)):
            return raw
        return json.loads(raw)
    # reuse collectors.fetch_url then parse
    text = fetch_url(url)
    return json.loads(text)


def normalize_feed_jobs(kind: str, payload: Any, *, source: str) -> list[dict]:
    out: list[dict] = []
    if kind in ("remotive_json", "auto") and isinstance(payload, dict) and "jobs" in payload:
        for j in payload.get("jobs") or []:
            if not isinstance(j, dict):
                continue
            title = str(j.get("title") or "Untitled")
            company = str(j.get("company_name") or j.get("company") or "Remotive")
            url = str(j.get("url") or "")
            loc = str(j.get("candidate_required_location") or j.get("location") or "Remote")
            desc = re.sub(r"<[^>]+>", " ", str(j.get("description") or ""))[:6000]
            cats = j.get("tags") or []
            tag_s = ", ".join(str(t) for t in cats[:8]) if isinstance(cats, list) else ""
            text = (
                f"# {title}\n**Company**: {company}\n**Location**: {loc}\n**URL**: {url}\n"
                f"**Tags**: {tag_s}\n\n## Description\n{desc}"
            )
            out.append(
                {
                    "title": title,
                    "company": company,
                    "url": url,
                    "location": loc,
                    "source": source,
                    "text": text,
                }
            )
        if out:
            return out
    if kind in ("arbeitnow_json", "auto") and isinstance(payload, dict) and "data" in payload:
        for j in payload.get("data") or []:
            if not isinstance(j, dict):
                continue
            title = str(j.get("title") or "Untitled")
            company = str(j.get("company_name") or j.get("company") or "Arbeitnow")
            url = str(j.get("url") or "")
            loc = str(j.get("location") or "")
            desc = re.sub(r"<[^>]+>", " ", str(j.get("description") or ""))[:6000]
            remote = j.get("remote")
            text = (
                f"# {title}\n**Company**: {company}\n**Location**: {loc}\n**URL**: {url}\n"
                f"**Remote**: {remote}\n\n## Description\n{desc}"
            )
            out.append(
                {
                    "title": title,
                    "company": company,
                    "url": url,
                    "location": loc,
                    "source": source,
                    "text": text,
                }
            )
        return out
    # generic list
    if isinstance(payload, list):
        for j in payload:
            if not isinstance(j, dict):
                continue
            title = str(j.get("title") or j.get("name") or "Untitled")
            company = str(j.get("company") or j.get("company_name") or source)
            url = str(j.get("url") or j.get("link") or "")
            loc = str(j.get("location") or "")
            desc = str(j.get("description") or j.get("text") or "")[:6000]
            text = f"# {title}\n**Company**: {company}\n**Location**: {loc}\n**URL**: {url}\n\n## Description\n{desc}"
            out.append(
                {
                    "title": title,
                    "company": company,
                    "url": url,
                    "location": loc,
                    "source": source,
                    "text": text,
                }
            )
    return out


def collect_feeds(
    root: Path,
    *,
    feed: str | None = None,
    limit: int = 15,
    match: bool = True,
    fetch_fn=None,
) -> dict:
    """Fetch public remote job feeds → warehouse + optional match."""
    root = Path(root)
    cfg = load_feeds_config(root)
    names = [feed] if feed else list(cfg.keys())
    collected: list[dict] = []
    errors: list[dict] = []
    for name in names:
        meta = cfg.get(name)
        if not meta:
            errors.append({"feed": name, "error": "unknown feed"})
            continue
        url = meta["url"]
        kind = meta.get("kind") or "auto"
        try:
            payload = _fetch_json(url, fetch_fn=fetch_fn)
            jobs = normalize_feed_jobs(kind, payload, source=f"feed:{name}")
            collected.extend(jobs)
        except Exception as e:
            errors.append({"feed": name, "error": str(e), "url": url})

    collected = collected[: max(1, limit)]
    wh = ingest_rows(
        root,
        [
            {
                "title": j.get("title"),
                "company": j.get("company"),
                "location": j.get("location") or "",
                "url": j.get("url") or "",
                "raw": (j.get("text") or "")[:8000],
                "source": j.get("source") or "feed",
            }
            for j in collected
        ],
        source="feeds",
    ) if collected else {"ingested": 0}

    results: list[dict] = []
    for j in collected:
        row = {
            "title": j.get("title"),
            "company": j.get("company"),
            "url": j.get("url"),
            "source": j.get("source"),
            "location": j.get("location"),
        }
        if match and j.get("text"):
            try:
                m = match_and_save(root, j["text"])
                g = m.grade or {}
                row.update(
                    {
                        "job_id": m.job_id,
                        "score": m.score,
                        "letter": g.get("letter"),
                        "score_100": g.get("score_100"),
                    }
                )
            except Exception as e:
                row["match_error"] = str(e)
        results.append(row)

    return {
        "feeds": names,
        "crawled": len(collected),
        "jobs": results,
        "warehouse": wh,
        "errors": errors,
        "ua": DEFAULT_UA,
    }
