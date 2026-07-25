"""Compliance-gated job collectors: paste / rss / career_html."""

from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .match import match_and_save

# Resolve blocklist relative to repo collectors/ or package
DEFAULT_UA = "CompassBot/0.1 (+https://github.com/local/compass; personal job search)"


def _repo_collectors_dir() -> Path:
    # compass_core -> packages/compass-core -> packages -> Compass
    return Path(__file__).resolve().parents[3] / "collectors"


def load_blocklist() -> set[str]:
    path = _repo_collectors_dir() / "blocklist.json"
    if not path.is_file():
        return {
            "zhipin.com",
            "www.zhipin.com",
            "liepin.com",
            "lagou.com",
            "linkedin.com",
            "www.linkedin.com",
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("blocked_hosts") or [])


def assert_url_allowed(url: str) -> None:
    host = urlparse(url).hostname or ""
    host = host.lower()
    blocked = load_blocklist()
    for b in blocked:
        if host == b or host.endswith("." + b):
            raise PermissionError(
                f"Host {host} is blocklisted for deep scrape (login/ToS risk). "
                "Paste the JD text instead. See docs/COMPLIANCE.md"
            )


def fetch_url(url: str, timeout: int = 20) -> str:
    assert_url_allowed(url)
    time.sleep(0.5)  # polite delay
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def collect_paste(root: Path, text: str, job_id: str | None = None):
    return match_and_save(root, text, job_id=job_id)


def collect_rss(root: Path, url: str, limit: int = 10) -> list[dict]:
    import feedparser

    assert_url_allowed(url)
    parsed = feedparser.parse(url)
    results = []
    for entry in (parsed.entries or [])[:limit]:
        title = getattr(entry, "title", "RSS Job")
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        link = getattr(entry, "link", "")
        company = urlparse(link).hostname or "RSS"
        body = f"职位：{title}\n公司：{company}\n链接：{link}\n\n{BeautifulSoup(summary, 'lxml').get_text('\\n', strip=True)}"
        m = match_and_save(root, body)
        results.append({"job_id": m.job_id, "title": m.title, "score": m.score})
    return results


def collect_career_html(root: Path, url: str, limit: int = 10) -> list[dict]:
    from .career_recommend import html_to_jd_markdown, parse_career_page

    html = fetch_url(url)
    host = urlparse(url).hostname or "career"
    jobs = parse_career_page(html, base_url=url, company=host, limit=limit)
    if not jobs:
        md = html_to_jd_markdown(html, base_url=url, company=host)
        m = match_and_save(root, md)
        return [{"job_id": m.job_id, "title": m.title, "score": m.score}]

    results = []
    for j in jobs[:limit]:
        text = j.get("text") or html_to_jd_markdown(html, base_url=j.get("url") or url, company=j.get("company") or host)
        m = match_and_save(root, text)
        results.append({"job_id": m.job_id, "title": m.title, "score": m.score, "url": j.get("url")})
    return results


def collect_ats_board(root: Path, board: str, limit: int = 10) -> list[dict]:
    """Public Greenhouse/Lever/Ashby/SmartRecruiters board → match_and_save."""
    from .ats_scan import collect_ats

    return collect_ats(root, board=board, limit=limit, match=True)
