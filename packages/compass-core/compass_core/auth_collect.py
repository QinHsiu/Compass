"""Opt-in authenticated / user-exported HTML list collect (fixtures + user HTML).

Does NOT automate login or CDP. User pastes/saves HTML themselves, then:
  session scout-html --file board.html --i-accept-tos-risk
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .auth_session import require_tos_risk
from .warehouse import ingest_rows


def _content_hash(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def fit_list_markdown(html: str, *, base_url: str = "") -> str:
    """Strip chrome; keep job-ish main content (Crawl4AI fit-markdown pattern)."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "aside"]):
        tag.decompose()
    # prefer main / role=main / job list containers
    main = (
        soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.find(class_=re.compile(r"job|career|listing|result|posting", re.I))
        or soup.body
        or soup
    )
    text = main.get_text("\n", strip=True) if main else soup.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)[:12000]
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    return f"# {title or 'Job list'}\n**URL**: {base_url}\n\n{text}"


def parse_job_list_html(html: str, *, base_url: str = "") -> list[dict]:
    """Extract jobs from saved HTML: JSON-LD, data-* attrs, cards, anchors."""
    jobs: list[dict] = []
    # JSON-LD JobPosting
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.I | re.S,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for it in items:
            if not isinstance(it, dict):
                continue
            types = it.get("@type")
            ok = "JobPosting" in types if isinstance(types, list) else types == "JobPosting"
            if not ok:
                continue
            org = it.get("hiringOrganization") or {}
            company = org.get("name") if isinstance(org, dict) else ""
            loc = ""
            jl = it.get("jobLocation") or {}
            if isinstance(jl, dict):
                addr = jl.get("address") or {}
                if isinstance(addr, dict):
                    loc = addr.get("addressLocality") or addr.get("addressRegion") or ""
            desc = it.get("description") or ""
            jobs.append(
                {
                    "title": it.get("title") or "",
                    "company": company or "",
                    "location": loc,
                    "url": it.get("url") or base_url,
                    "raw": re.sub(r"<[^>]+>", " ", str(desc))[:5000],
                    "source": "auth_html_jsonld",
                }
            )
    # data-job-title attrs
    for m in re.finditer(
        r'data-job-title=["\']([^"\']+)["\'][^>]*data-company=["\']([^"\']+)["\'][^>]*href=["\']([^"\']+)["\']',
        html,
        re.I,
    ):
        jobs.append(
            {
                "title": m.group(1),
                "company": m.group(2),
                "location": "",
                "url": urljoin(base_url, m.group(3)),
                "raw": f"{m.group(1)} @ {m.group(2)}",
                "source": "auth_html_attr",
            }
        )
    # reverse attr order
    for m in re.finditer(
        r'href=["\']([^"\']+)["\'][^>]*data-job-title=["\']([^"\']+)["\'][^>]*data-company=["\']([^"\']+)["\']',
        html,
        re.I,
    ):
        jobs.append(
            {
                "title": m.group(2),
                "company": m.group(3),
                "location": "",
                "url": urljoin(base_url, m.group(1)),
                "raw": f"{m.group(2)} @ {m.group(3)}",
                "source": "auth_html_attr",
            }
        )

    soup = BeautifulSoup(html, "lxml")
    # card containers
    for card in soup.select(
        "[class*='job-card'], [class*='jobCard'], [class*='job-item'], "
        "[class*='JobCard'], [data-job-id], li.job, article.job"
    ):
        a = card.find("a", href=True)
        title_el = card.find(["h2", "h3", "h4", "a"])
        title = (title_el.get_text(" ", strip=True) if title_el else "")[:160]
        if len(title) < 3:
            continue
        href = a["href"] if a else ""
        company_el = card.find(class_=re.compile(r"company|employer", re.I))
        company = company_el.get_text(" ", strip=True) if company_el else ""
        loc_el = card.find(class_=re.compile(r"location|city", re.I))
        loc = loc_el.get_text(" ", strip=True) if loc_el else ""
        raw = card.get_text(" ", strip=True)[:3000]
        jobs.append(
            {
                "title": title,
                "company": company,
                "location": loc,
                "url": urljoin(base_url, href) if href else base_url,
                "raw": raw,
                "source": "auth_html_card",
            }
        )

    # generic job-like anchors
    for a in soup.find_all("a", href=True):
        label = a.get_text(" ", strip=True)
        href = a["href"]
        if len(label) < 4:
            continue
        if not re.search(r"job|career|position|opening|岗位|职位|招聘|/jobs/", label + href, re.I):
            continue
        if re.search(r"login|signin|cookie|privacy|javascript:", href, re.I):
            continue
        jobs.append(
            {
                "title": label[:120],
                "company": "",
                "location": "",
                "url": urljoin(base_url, href),
                "raw": label,
                "source": "auth_html_anchor",
            }
        )

    seen = set()
    out = []
    for j in jobs:
        key = ((j.get("url") or "").rstrip("/"), (j.get("title") or "").strip().lower())
        if not key[1] or key in seen:
            continue
        seen.add(key)
        j["content_hash"] = _content_hash(f"{key[0]}|{key[1]}|{j.get('raw')}")
        out.append(j)
    return out


def scout_auth_html(
    root: Path,
    *,
    html: str | None = None,
    fixture: str | Path | None = None,
    accept_tos_risk: bool = False,
    list_url: str | None = None,
    match: bool = False,
    limit: int = 50,
) -> dict:
    """Parse user-exported board HTML → warehouse. Requires --i-accept-tos-risk."""
    require_tos_risk(accept_tos_risk)
    if fixture:
        html = Path(fixture).read_text(encoding="utf-8")
        base = "https://example.com/"
    elif html:
        base = list_url or ""
    else:
        raise ValueError("need html or fixture")

    jobs = parse_job_list_html(html, base_url=base)[: max(1, limit)]
    fit_md = fit_list_markdown(html, base_url=base)
    # enrich raw with fit markdown when thin
    for j in jobs:
        if len(j.get("raw") or "") < 80:
            j["raw"] = f"{j.get('title')}\n{j.get('company')}\n{fit_md[:2000]}"

    wh = ingest_rows(Path(root), jobs, source="auth_html")
    matched = []
    if match:
        from .match import match_and_save

        for j in jobs[: min(20, len(jobs))]:
            body = (
                f"# {j.get('title')}\n**Company**: {j.get('company')}\n"
                f"**Location**: {j.get('location')}\n**URL**: {j.get('url')}\n\n"
                f"## Description\n{j.get('raw') or ''}"
            )
            try:
                m = match_and_save(Path(root), body)
                matched.append({"job_id": m.job_id, "title": m.title, "score": m.score})
            except Exception as e:
                matched.append({"title": j.get("title"), "error": str(e)})

    # persist parse report under logs
    report = {
        "jobs": len(jobs),
        "warehouse": wh,
        "matched": matched,
        "sample": jobs[:5],
        "fit_markdown_preview": fit_md[:500],
        "content_hashes": [j.get("content_hash") for j in jobs[:20]],
        "note": "User-exported HTML only — no CDP/login automation",
    }
    try:
        logs = Path(root) / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / "auth_html_last.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        report["report_path"] = str(logs / "auth_html_last.json")
    except Exception:
        pass
    return report
