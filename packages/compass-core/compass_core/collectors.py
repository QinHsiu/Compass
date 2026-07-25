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
    html = fetch_url(url)
    soup = BeautifulSoup(html, "lxml")
    # Heuristic: job-like anchors / headings
    candidates: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = a["href"]
        if len(text) < 4:
            continue
        if re.search(r"job|career|position|岗位|职位|招聘", text + href, re.I):
            candidates.append((text, href))
    # also page title as single job if few candidates
    if not candidates:
        title = (soup.title.string if soup.title else "Career Page") or "Career Page"
        body = soup.get_text("\n", strip=True)[:4000]
        m = match_and_save(root, f"职位：{title}\n公司：{urlparse(url).hostname}\n\n{body}")
        return [{"job_id": m.job_id, "title": m.title, "score": m.score}]

    results = []
    seen = set()
    for text, href in candidates:
        if text in seen:
            continue
        seen.add(text)
        body = f"职位：{text}\n公司：{urlparse(url).hostname}\n链接：{href}\n来源页：{url}"
        m = match_and_save(root, body)
        results.append({"job_id": m.job_id, "title": m.title, "score": m.score})
        if len(results) >= limit:
            break
    return results


def collect_ats_board(root: Path, board: str, limit: int = 10) -> list[dict]:
    """Public Greenhouse/Lever/Ashby board → match_and_save."""
    from .ats_scan import collect_ats

    return collect_ats(root, board=board, limit=limit, match=True)
