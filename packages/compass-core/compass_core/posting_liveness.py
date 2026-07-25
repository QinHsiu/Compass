"""Posting liveness / ATS source hints (career-ops Round 13 leftover)."""

from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlparse

ATS_HOSTS = {
    "greenhouse.io": "greenhouse",
    "boards.greenhouse.io": "greenhouse",
    "lever.co": "lever",
    "jobs.lever.co": "lever",
    "ashbyhq.com": "ashby",
    "jobs.ashbyhq.com": "ashby",
    "myworkdayjobs.com": "workday",
    "workday.com": "workday",
}


def detect_ats(url: str | None) -> str:
    if not url:
        return "unknown"
    host = (urlparse(url).hostname or "").lower()
    for suffix, name in ATS_HOSTS.items():
        if host.endswith(suffix):
            return name
    return "unknown"


def _parse_date(val: str | None) -> date | None:
    if not val:
        return None
    s = str(val).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.search(r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})", str(val))
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def assess_liveness(
    *,
    url: str | None = None,
    posted_at: str | None = None,
    first_seen: str | None = None,
    stale_days: int = 45,
    as_of: date | None = None,
) -> dict:
    """Return liveness fresh|stale|unknown + ats vendor."""
    as_of = as_of or date.today()
    ats = detect_ats(url)
    posted = _parse_date(posted_at) or _parse_date(first_seen)
    if posted is None:
        status = "unknown"
        age = None
    else:
        age = (as_of - posted).days
        status = "stale" if age > stale_days else "fresh"
    return {
        "status": status,
        "ats": ats,
        "posted_at": posted.isoformat() if posted else None,
        "age_days": age,
        "stale_days_threshold": stale_days,
    }


def apply_liveness_to_explain(explain: dict, liveness: dict) -> dict:
    out = dict(explain or {})
    if (liveness or {}).get("status") == "stale":
        band = out.get("recommendation") or "exploratory"
        if band in ("strong", "plausible"):
            out["recommendation"] = "exploratory"
            out["liveness_override"] = f"stale→cap({band}→exploratory)"
    return out
