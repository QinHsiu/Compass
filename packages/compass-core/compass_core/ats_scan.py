"""Public ATS board scan (Greenhouse / Lever / Ashby) — zero-token, no secrets.

compas.txt P0: career-ops-style job discovery via official public JSON APIs.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .collectors import DEFAULT_UA, assert_url_allowed
from .match import match_and_save

ATS_ALLOWLIST = {
    "boards-api.greenhouse.io",
    "api.greenhouse.io",
    "api.lever.co",
    "api.eu.lever.co",
    "api.ashbyhq.com",
}


def _assert_ats_host(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if host not in ATS_ALLOWLIST:
        raise PermissionError(
            f"ATS host {host} not in allowlist {sorted(ATS_ALLOWLIST)}. "
            "Use greenhouse:/lever:/ashby: board specs or paste JD."
        )
    assert_url_allowed(url)


def fetch_json(url: str, timeout: int = 25) -> Any:
    """GET JSON with redirect rejected and ATS host allowlist."""
    _assert_ats_host(url)
    time.sleep(0.3)
    req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA, "Accept": "application/json"})
    # redirect='error' via custom opener
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    # Disable redirects: use a handler that raises

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N803
            raise urllib.error.HTTPError(req.full_url, code, f"redirect blocked → {newurl}", headers, fp)

    opener = urllib.request.build_opener(_NoRedirect())
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def parse_board_spec(spec: str) -> tuple[str, str]:
    """Parse 'greenhouse:acme' or a careers URL → (ats, slug)."""
    s = (spec or "").strip()
    if ":" in s and not s.startswith("http"):
        ats, slug = s.split(":", 1)
        ats = ats.strip().lower()
        slug = slug.strip().strip("/")
        if ats not in ("greenhouse", "lever", "ashby"):
            raise ValueError(f"unknown ats {ats}; use greenhouse|lever|ashby")
        if not slug:
            raise ValueError("empty board slug")
        return ats, slug
    # URL forms
    u = urlparse(s)
    host = (u.hostname or "").lower()
    path = u.path.strip("/")
    parts = path.split("/")
    if "greenhouse" in host:
        # boards.greenhouse.io/acme or boards-api.../v1/boards/acme/jobs
        if "boards" in parts:
            i = parts.index("boards")
            if i + 1 < len(parts):
                return "greenhouse", parts[i + 1]
        if parts:
            return "greenhouse", parts[0]
    if "lever" in host:
        # jobs.lever.co/acme
        if parts:
            return "lever", parts[0]
    if "ashby" in host:
        # jobs.ashbyhq.com/acme/...
        if parts:
            return "ashby", parts[0]
    raise ValueError(f"cannot parse board from {spec!r}; use greenhouse:slug")


def api_url(ats: str, slug: str) -> str:
    if ats == "greenhouse":
        return f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    if ats == "lever":
        return f"https://api.lever.co/v0/postings/{slug}?mode=json"
    if ats == "ashby":
        return f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
    raise ValueError(ats)


def _strip_html(html: str) -> str:
    t = re.sub(r"<[^>]+>", "\n", html or "")
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def normalize_jobs(ats: str, slug: str, payload: Any) -> list[dict]:
    """Normalize provider JSON → [{title, company, url, posted_at, description}]."""
    out: list[dict] = []
    company = slug
    if ats == "greenhouse":
        jobs = (payload or {}).get("jobs") or []
        for j in jobs:
            title = str(j.get("title") or "Untitled")
            abs_url = j.get("absolute_url") or ""
            loc = ""
            if isinstance(j.get("location"), dict):
                loc = str(j["location"].get("name") or "")
            content = _strip_html(str(j.get("content") or ""))
            posted = str(j.get("updated_at") or j.get("created_at") or "")[:10] or None
            body_parts = [
                f"职位：{title}",
                f"公司：{company}",
                f"工作地：{loc}" if loc else "",
                f"发布：{posted}" if posted else "",
                f"链接：{abs_url}" if abs_url else "",
                "",
                content[:6000],
            ]
            out.append(
                {
                    "title": title,
                    "company": company,
                    "url": abs_url,
                    "posted_at": posted,
                    "ats": ats,
                    "board": slug,
                    "text": "\n".join(p for p in body_parts if p is not None),
                }
            )
    elif ats == "lever":
        jobs = payload if isinstance(payload, list) else []
        for j in jobs:
            title = str(j.get("text") or j.get("title") or "Untitled")
            abs_url = str(j.get("hostedUrl") or j.get("applyUrl") or "")
            desc = str(j.get("descriptionPlain") or "") or _strip_html(str(j.get("description") or ""))
            cats = j.get("categories") or {}
            loc = str(cats.get("location") or "")
            posted = str(j.get("createdAt") or "")[:10] or None
            if posted and posted.isdigit():
                posted = None  # ms epoch — skip for simplicity
            body_parts = [
                f"职位：{title}",
                f"公司：{company}",
                f"工作地：{loc}" if loc else "",
                f"链接：{abs_url}" if abs_url else "",
                "",
                desc[:6000],
            ]
            out.append(
                {
                    "title": title,
                    "company": company,
                    "url": abs_url,
                    "posted_at": posted,
                    "ats": ats,
                    "board": slug,
                    "text": "\n".join(p for p in body_parts if p),
                }
            )
    elif ats == "ashby":
        jobs = (payload or {}).get("jobs") or []
        for j in jobs:
            title = str(j.get("title") or "Untitled")
            abs_url = str(j.get("jobUrl") or j.get("applyUrl") or "")
            desc = _strip_html(str(j.get("descriptionHtml") or j.get("descriptionPlain") or ""))
            loc = str(j.get("location") or "")
            posted = str(j.get("publishedAt") or j.get("updatedAt") or "")[:10] or None
            comp = j.get("compensation") or j.get("compensationTierSummary") or ""
            if isinstance(comp, dict):
                comp = json.dumps(comp, ensure_ascii=False)
            elif isinstance(comp, list):
                comp = "; ".join(str(x) for x in comp[:5])
            else:
                comp = str(comp or "")
            body_parts = [
                f"职位：{title}",
                f"公司：{company}",
                f"工作地：{loc}" if loc else "",
                f"发布：{posted}" if posted else "",
                f"链接：{abs_url}" if abs_url else "",
                f"薪资：{comp}" if comp else "",
                "",
                desc[:6000],
            ]
            out.append(
                {
                    "title": title,
                    "company": company,
                    "url": abs_url,
                    "posted_at": posted,
                    "ats": ats,
                    "board": slug,
                    "salary_hint": comp,
                    "text": "\n".join(p for p in body_parts if p),
                }
            )
    return out


def scan_board(spec: str, *, limit: int = 20, fetch_fn=None) -> list[dict]:
    """Fetch and normalize jobs for one board spec. ``fetch_fn`` injectable for tests."""
    ats, slug = parse_board_spec(spec)
    url = api_url(ats, slug)
    fetcher = fetch_fn or fetch_json
    payload = fetcher(url)
    jobs = normalize_jobs(ats, slug, payload)
    return jobs[: max(1, limit)]


def load_portals(root: Path) -> list[str]:
    """Load board specs from content/portals.yml (simple YAML or JSON list)."""
    root = Path(root)
    for name in ("portals.yml", "portals.yaml", "portals.json"):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if name.endswith(".json"):
            data = json.loads(text)
        else:
            # minimal YAML: boards: [a, b] or - greenhouse:x
            data = _parse_simple_portals(text)
        if isinstance(data, dict):
            boards = data.get("boards") or data.get("portals") or []
        else:
            boards = data
        return [str(b).strip() for b in boards if str(b).strip()]
    return []


def _parse_simple_portals(text: str) -> dict:
    boards: list[str] = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        m = re.match(r"^-\s+(.+)$", ln)
        if m:
            boards.append(m.group(1).strip().strip("\"'"))
            continue
        m = re.match(r"^boards\s*:\s*\[(.*)\]\s*$", ln)
        if m:
            inner = m.group(1)
            for part in inner.split(","):
                p = part.strip().strip("\"'")
                if p:
                    boards.append(p)
    return {"boards": boards}


def collect_ats(
    root: Path,
    *,
    board: str | None = None,
    limit: int = 10,
    match: bool = True,
    fetch_fn=None,
) -> list[dict]:
    """Scan board(s) and optionally match_and_save each JD."""
    specs = [board] if board else load_portals(root)
    if not specs:
        raise ValueError(
            "no board; pass --board greenhouse:slug or add content/portals.yml"
        )
    results: list[dict] = []
    per = max(1, limit // max(len(specs), 1))
    for spec in specs:
        jobs = scan_board(spec, limit=per if not board else limit, fetch_fn=fetch_fn)
        for j in jobs:
            row = {
                "title": j["title"],
                "company": j["company"],
                "url": j.get("url"),
                "ats": j.get("ats"),
                "board": j.get("board"),
            }
            if match:
                m = match_and_save(root, j["text"])
                g = m.grade or {}
                row.update(
                    {
                        "job_id": m.job_id,
                        "score": m.score,
                        "recommendation": (m.match_explain or {}).get("recommendation"),
                        "letter": g.get("letter"),
                        "global_1_5": g.get("global_1_5"),
                    }
                )
            else:
                row["text_preview"] = j["text"][:200]
            results.append(row)
            if board and len(results) >= limit:
                return results
    return results[:limit] if board else results
