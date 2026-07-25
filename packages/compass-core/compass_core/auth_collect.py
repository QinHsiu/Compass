"""Opt-in authenticated HTML list collect (fixtures + user HTML)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

from .auth_session import require_tos_risk
from .warehouse import ingest_rows


def parse_job_list_html(html: str, *, base_url: str = "") -> list[dict]:
    jobs: list[dict] = []
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
    seen = set()
    out = []
    for j in jobs:
        key = (j.get("url"), j.get("title"))
        if key in seen:
            continue
        seen.add(key)
        out.append(j)
    return out


def scout_auth_html(
    root: Path,
    *,
    html: str | None = None,
    fixture: str | Path | None = None,
    accept_tos_risk: bool = False,
    list_url: str | None = None,
) -> dict:
    require_tos_risk(accept_tos_risk)
    if fixture:
        html = Path(fixture).read_text(encoding="utf-8")
        base = "https://example.com/"
    elif html:
        base = list_url or ""
    else:
        raise ValueError("need html or fixture")
    jobs = parse_job_list_html(html, base_url=base)
    wh = ingest_rows(Path(root), jobs, source="auth_html")
    return {"jobs": len(jobs), "warehouse": wh, "sample": jobs[:3]}
