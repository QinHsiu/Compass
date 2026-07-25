"""Crawl official company career pages + public ATS → recommend jobs."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .ats_scan import parse_board_spec, scan_board
from .collectors import assert_url_allowed, fetch_url
from .companies import load_companies
from .match import match_and_save
from .warehouse import ingest_rows


_ATS_HINT = re.compile(
    r"(boards\.greenhouse\.io|jobs\.lever\.co|jobs\.ashbyhq\.com|api\.ashbyhq\.com|"
    r"greenhouse\.io/embed|lever\.co/|ashbyhq\.com)",
    re.I,
)


def detect_ats_from_html(html: str, page_url: str = "") -> str | None:
    """Infer greenhouse:slug / lever:slug / ashby:slug / smartrecruiters:id from career HTML."""
    blob = f"{html}\n{page_url}"
    m = re.search(r"boards\.greenhouse\.io/([a-z0-9_-]+)", blob, re.I)
    if m:
        return f"greenhouse:{m.group(1)}"
    m = re.search(r"boards-api\.greenhouse\.io/v1/boards/([a-z0-9_-]+)", blob, re.I)
    if m:
        return f"greenhouse:{m.group(1)}"
    m = re.search(r"jobs\.lever\.co/([a-z0-9_-]+)", blob, re.I)
    if m:
        return f"lever:{m.group(1)}"
    m = re.search(r"jobs\.ashbyhq\.com/([a-z0-9_-]+)", blob, re.I)
    if m:
        return f"ashby:{m.group(1)}"
    m = re.search(r"job-board/([a-z0-9_-]+)", blob, re.I)
    if m and "ashby" in blob.lower():
        return f"ashby:{m.group(1)}"
    m = re.search(r"smartrecruiters\.com/([a-zA-Z0-9_-]+)/?", blob, re.I)
    if m and "api.smartrecruiters" not in blob.lower():
        slug = m.group(1)
        if slug.lower() not in ("www", "api", "app", "careers"):
            return f"smartrecruiters:{slug}"
    m = re.search(r"api\.smartrecruiters\.com/v1/companies/([a-zA-Z0-9_-]+)", blob, re.I)
    if m:
        return f"smartrecruiters:{m.group(1)}"
    return None


def html_to_jd_markdown(
    html: str,
    *,
    base_url: str = "",
    company: str = "",
    fit: bool = True,
) -> str:
    """LLM-friendly clean markdown from career/job HTML (Crawl4AI pattern, no deps)."""
    parts: list[str] = []
    # Prefer JSON-LD JobPosting
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
            title = it.get("title") or "Untitled"
            url = it.get("url") or base_url
            desc = re.sub(r"<[^>]+>", " ", str(it.get("description") or ""))
            desc = re.sub(r"\s+", " ", desc).strip()[:8000]
            loc = ""
            jl = it.get("jobLocation") or {}
            if isinstance(jl, dict):
                addr = jl.get("address") or {}
                if isinstance(addr, dict):
                    loc = addr.get("addressLocality") or addr.get("addressRegion") or ""
            org = it.get("hiringOrganization") or {}
            co = org.get("name") if isinstance(org, dict) else company
            parts.append(f"# {title}")
            parts.append(f"**Company**: {co or company or '—'}")
            if loc:
                parts.append(f"**Location**: {loc}")
            if url:
                parts.append(f"**URL**: {url}")
            parts.append("")
            parts.append("## Description")
            parts.append(desc or "_(empty)_")
            parts.append("")
    if parts:
        return "\n".join(parts).strip()

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    if fit:
        for tag in soup(["nav", "footer", "header", "aside"]):
            tag.decompose()
    main = None
    if fit:
        main = (
            soup.find("main")
            or soup.find(attrs={"role": "main"})
            or soup.find("article")
            or soup.find(class_=re.compile(r"job|posting|description|content", re.I))
        )
    root = main or soup.body or soup
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    h1 = root.find(["h1", "h2"]) if hasattr(root, "find") else None
    if h1:
        title = title or h1.get_text(" ", strip=True)
    body = root.get_text("\n", strip=True) if root else ""
    body = re.sub(r"\n{3,}", "\n\n", body)[:8000]
    out = [f"# {title or 'Career page'}"]
    if company:
        out.append(f"**Company**: {company}")
    if base_url:
        out.append(f"**URL**: {base_url}")
    out.extend(["", "## Description", body or "_(empty)_"])
    return "\n".join(out).strip()


def content_hash(text: str) -> str:
    import hashlib

    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:16]


def same_site(url: str, base: str) -> bool:
    a = urlparse(url)
    b = urlparse(base)
    return bool(a.hostname) and a.hostname == b.hostname


def crawl_career_depth(
    company: dict,
    *,
    limit: int = 15,
    depth: int = 1,
    fetch_fn=None,
    fetch_html_fn=None,
    seen_hashes: set[str] | None = None,
) -> list[dict]:
    """
    List page → optional detail pages (depth=1), same-host only.
    Crawl4AI-style limited crawl without browser stack.
    """
    name = company.get("name") or "unknown"
    depth = max(0, min(int(depth), 2))
    seen_hashes = seen_hashes if seen_hashes is not None else set()

    # depth 0: existing crawl_company path
    if depth == 0:
        return crawl_company(company, limit=limit, fetch_fn=fetch_fn, fetch_html_fn=fetch_html_fn)

    jobs = crawl_company(company, limit=limit, fetch_fn=fetch_fn, fetch_html_fn=fetch_html_fn)
    if depth < 1:
        return jobs

    career_url = company.get("career_url") or ""
    enriched: list[dict] = []
    detail_budget = min(limit, 8)

    for j in jobs:
        j = dict(j)
        j["depth"] = 0
        h = content_hash(j.get("text") or j.get("url") or "")
        j["content_hash"] = h
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        url = (j.get("url") or "").strip()
        # fetch detail when listing text is thin and same-site
        need_detail = (
            depth >= 1
            and url
            and career_url
            and same_site(url, career_url)
            and url.rstrip("/") != career_url.rstrip("/")
            and len(j.get("text") or "") < 800
            and detail_budget > 0
        )
        if need_detail:
            try:
                assert_url_allowed(url)
                html = fetch_html_fn(url) if fetch_html_fn else fetch_url(url)
                md = html_to_jd_markdown(html, base_url=url, company=name, fit=True)
                dh = content_hash(md)
                if dh not in seen_hashes and len(md) > len(j.get("text") or ""):
                    j["text"] = md
                    j["source"] = (j.get("source") or "career") + "+detail"
                    j["depth"] = 1
                    j["content_hash"] = dh
                    seen_hashes.add(dh)
                    detail_budget -= 1
            except Exception:
                pass
        enriched.append(j)
        if len(enriched) >= limit:
            break
    return enriched[:limit]


def parse_career_page(html: str, *, base_url: str, company: str, limit: int = 30) -> list[dict]:
    """Extract job cards from official career HTML (JSON-LD + anchors)."""
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
            title = it.get("title") or ""
            url = it.get("url") or base_url
            # rebuild mini HTML for markdown path
            mini = (
                f'<script type="application/ld+json">{json.dumps(it, ensure_ascii=False)}</script>'
            )
            text = html_to_jd_markdown(mini, base_url=url, company=company)
            if not text or "Description" not in text:
                desc = re.sub(r"<[^>]+>", " ", str(it.get("description") or ""))[:5000]
                loc = ""
                jl = it.get("jobLocation") or {}
                if isinstance(jl, dict):
                    addr = jl.get("address") or {}
                    if isinstance(addr, dict):
                        loc = addr.get("addressLocality") or ""
                org = it.get("hiringOrganization") or {}
                co = org.get("name") if isinstance(org, dict) else company
                text = f"职位：{title}\n公司：{co or company}\n工作地：{loc}\n链接：{url}\n\n{desc}"
            loc = ""
            jl = it.get("jobLocation") or {}
            if isinstance(jl, dict):
                addr = jl.get("address") or {}
                if isinstance(addr, dict):
                    loc = addr.get("addressLocality") or ""
            org = it.get("hiringOrganization") or {}
            co = org.get("name") if isinstance(org, dict) else company
            salary = ""
            base_sal = it.get("baseSalary") or {}
            if isinstance(base_sal, dict):
                val = base_sal.get("value") or {}
                if isinstance(val, dict):
                    salary = f"{val.get('minValue')}-{val.get('maxValue')} {val.get('unitText') or ''}"
                else:
                    salary = str(val)
            jobs.append(
                {
                    "title": title,
                    "company": co or company,
                    "url": url,
                    "location": loc,
                    "salary_hint": salary,
                    "source": "career_jsonld",
                    "text": text,
                }
            )

    soup = BeautifulSoup(html, "lxml")
    seen = {j.get("url") for j in jobs}
    for a in soup.find_all("a", href=True):
        label = a.get_text(" ", strip=True)
        href = a["href"]
        if len(label) < 4:
            continue
        if not re.search(r"job|career|position|opening|岗位|职位|招聘|社招|校招", label + href, re.I):
            continue
        full = urljoin(base_url, href)
        if full in seen:
            continue
        if re.search(r"login|signin|cookie|privacy", full, re.I):
            continue
        seen.add(full)
        text = (
            f"# {label[:120]}\n**Company**: {company}\n**URL**: {full}\n\n"
            f"## Description\nListing from {base_url}"
        )
        jobs.append(
            {
                "title": label[:120],
                "company": company,
                "url": full,
                "location": "",
                "salary_hint": "",
                "source": "career_html",
                "text": text,
            }
        )
        if len(jobs) >= limit:
            break
    return jobs[:limit]


def crawl_company(
    company: dict,
    *,
    limit: int = 15,
    fetch_fn=None,
    fetch_html_fn=None,
) -> list[dict]:
    """Crawl one company: prefer ATS public API, else official career_url HTML."""
    name = company.get("name") or "unknown"
    jobs: list[dict] = []
    ats = company.get("ats")
    career_url = company.get("career_url")

    if ats:
        try:
            parse_board_spec(ats)
            scanned = scan_board(ats, limit=limit, fetch_fn=fetch_fn)
            for j in scanned:
                j = dict(j)
                j["company"] = j.get("company") or name
                j["source"] = f"ats:{j.get('ats')}"
                jobs.append(j)
        except (ValueError, PermissionError, OSError, Exception):
            pass

    if career_url and len(jobs) < limit:
        try:
            assert_url_allowed(career_url)
            if fetch_html_fn:
                html = fetch_html_fn(career_url)
            else:
                html = fetch_url(career_url)
            # try detect ATS from page if no jobs yet
            if not jobs:
                detected = detect_ats_from_html(html, career_url)
                if detected:
                    try:
                        scanned = scan_board(detected, limit=limit, fetch_fn=fetch_fn)
                        for j in scanned:
                            j = dict(j)
                            j["company"] = name
                            j["source"] = f"ats_detected:{detected}"
                            jobs.append(j)
                    except Exception:
                        pass
            if len(jobs) < limit:
                html_jobs = parse_career_page(
                    html, base_url=career_url, company=name, limit=limit - len(jobs)
                )
                jobs.extend(html_jobs)
        except (PermissionError, OSError, Exception):
            pass

    for j in jobs:
        j.setdefault("company", name)
    return jobs[:limit]


def recommend_jobs(
    root: Path,
    *,
    keyword: str | None = None,
    location: str | None = None,
    limit: int = 20,
    match: bool = True,
    workers: int = 4,
    companies: list[dict] | None = None,
    fetch_fn=None,
    fetch_html_fn=None,
    depth: int = 0,
) -> dict:
    """Crawl company official sites / ATS → filter → match → ranked recommendations."""
    root = Path(root)
    cos = companies if companies is not None else load_companies(root)
    if not cos:
        return {"error": "no companies; add content/companies.yml or use seed", "jobs": []}

    collected: list[dict] = []
    errors: list[dict] = []

    def _one(c: dict) -> tuple[str, list[dict], str | None]:
        try:
            if depth >= 1:
                return c.get("name") or "", crawl_career_depth(
                    c,
                    limit=max(8, limit // max(len(cos), 1) + 5),
                    depth=depth,
                    fetch_fn=fetch_fn,
                    fetch_html_fn=fetch_html_fn,
                ), None
            return c.get("name") or "", crawl_company(
                c, limit=max(8, limit // max(len(cos), 1) + 5), fetch_fn=fetch_fn, fetch_html_fn=fetch_html_fn
            ), None
        except Exception as e:
            return c.get("name") or "", [], str(e)

    workers = max(1, min(workers, 8))
    if workers == 1 or len(cos) == 1:
        for c in cos:
            name, jobs, err = _one(c)
            if err:
                errors.append({"company": name, "error": err})
            collected.extend(jobs)
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_one, c) for c in cos]
            for fut in as_completed(futs):
                name, jobs, err = fut.result()
                if err:
                    errors.append({"company": name, "error": err})
                collected.extend(jobs)

    # filter
    kws = [k.strip().lower() for k in (keyword or "").replace("|", ",").split(",") if k.strip()]
    locs = [x.strip().lower() for x in (location or "").replace("|", ",").split(",") if x.strip()]

    def _ok(j: dict) -> bool:
        blob = f"{j.get('title')} {j.get('text')} {j.get('company')}".lower()
        if kws and not any(k in blob for k in kws):
            return False
        if locs and not any(loc in blob for loc in locs):
            return False
        return True

    filtered = [j for j in collected if _ok(j)]
    # ingest warehouse always (discovery)
    wh_rows = [
        {
            "title": j.get("title"),
            "company": j.get("company"),
            "location": j.get("location") or "",
            "url": j.get("url") or "",
            "raw": (j.get("text") or "")[:8000],
            "source": j.get("source") or "career",
        }
        for j in filtered
    ]
    wh = ingest_rows(root, wh_rows, source="recommend") if wh_rows else {"ingested": 0}

    ranked: list[dict] = []
    for j in filtered:
        row = {
            "title": j.get("title"),
            "company": j.get("company"),
            "url": j.get("url"),
            "source": j.get("source"),
            "salary_hint": j.get("salary_hint"),
        }
        if match and j.get("text"):
            try:
                m = match_and_save(root, j["text"])
                g = m.grade or {}
                row.update(
                    {
                        "job_id": m.job_id,
                        "score": m.score,
                        "score_100": g.get("score_100"),
                        "letter": g.get("letter"),
                        "recommendation": (m.match_explain or {}).get("recommendation"),
                        "display": g.get("display"),
                    }
                )
            except Exception as e:
                row["match_error"] = str(e)
        ranked.append(row)

    ranked.sort(
        key=lambda r: float(r.get("score_100") or r.get("score") or 0),
        reverse=True,
    )
    ranked = ranked[:limit]

    out = {
        "companies": len(cos),
        "crawled": len(collected),
        "matched_filter": len(filtered),
        "recommended": ranked,
        "warehouse": wh,
        "errors": errors,
        "keyword": keyword,
        "location": location,
    }
    out_dir = root / "recommendations"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "latest.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["path"] = str(path)
    return out
