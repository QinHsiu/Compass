"""Live compensation lookup — OfferShow-compatible APIs, user captures, JD salary.

OfferShow's official product is WeChat mini-program and asks third parties not to
bulk-scrape. Compass therefore:

1. Calls **user-configured** live HTTP endpoints (COMPASS_OFFERSHOW_API / sources.yml).
2. Ingests **user-exported** JSON/CSV captures from OfferShow / OfferHero / Levels.
3. Extracts salary bands already present on matched job postings (real posting pay).

Network live mode requires ``--i-accept-tos-risk`` (or COMPASS_ACCEPT_TOS_RISK=1).
"""

from __future__ import annotations

import json
import os
import re
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .auth_session import require_tos_risk

UA = "CompassComp/0.15 (+https://github.com/QinHsiu/Compass; personal negotiation research)"
FetchFn = Callable[[str, dict | None], Any]

_SALARY_RE = re.compile(
    r"(?P<a>\d+(?:\.\d+)?)\s*[-~—至到]\s*(?P<b>\d+(?:\.\d+)?)\s*(?P<u>k|K|千|万|w|W)?",
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _comp_dir(root: Path) -> Path:
    d = Path(root) / "comp"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_dir(root: Path) -> Path:
    d = _comp_dir(root) / "live_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_sources(root: Path | None) -> dict:
    """Merge env + content/comp/sources.json|yml-ish JSON."""
    cfg: dict[str, Any] = {
        "offershow": {
            "base_url": os.environ.get("COMPASS_OFFERSHOW_API") or "",
            "token": os.environ.get("COMPASS_OFFERSHOW_TOKEN") or "",
            "search_path": os.environ.get("COMPASS_OFFERSHOW_SEARCH_PATH") or "/salary/query",
            "method": "POST",
        },
        "http": {
            "url": os.environ.get("COMPASS_COMP_LIVE_URL") or "",
            "method": os.environ.get("COMPASS_COMP_LIVE_METHOD") or "GET",
        },
        "levels": {
            "url": os.environ.get("COMPASS_LEVELS_API") or "",
            "method": os.environ.get("COMPASS_LEVELS_METHOD") or "GET",
        },
        "extra_endpoints": [],
        "ttl_seconds": int(os.environ.get("COMPASS_COMP_LIVE_TTL") or 3600),
    }
    if root:
        for name in ("sources.json", "sources.yml"):
            path = _comp_dir(root) / name
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # minimal yaml: key: value lines under offershow:
                data = _parse_simple_sources(text)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                        cfg[k].update(v)
                    else:
                        cfg[k] = v
            break
    return cfg


def _parse_simple_sources(text: str) -> dict:
    out: dict[str, Any] = {}
    section = None
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.endswith(":") and " " not in s.strip(":"):
            section = s[:-1].strip()
            out.setdefault(section, {})
            continue
        if ":" in s and section:
            k, v = s.split(":", 1)
            out[section][k.strip()] = v.strip().strip("\"'")
    return out


def default_fetch(url: str, payload: dict | None = None, *, method: str = "GET", headers: dict | None = None) -> Any:
    time.sleep(0.4)
    hdrs = {"User-Agent": UA, "Accept": "application/json,text/plain,*/*"}
    if headers:
        hdrs.update(headers)
    data = None
    if payload is not None and method.upper() != "GET":
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    elif payload is not None and method.upper() == "GET":
        q = urllib.parse.urlencode({k: v for k, v in payload.items() if v is not None})
        url = url + ("&" if "?" in url else "?") + q
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        text = raw.decode(charset, errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text[:5000]}


def parse_salary_token(text: str) -> tuple[float | None, float | None, str]:
    """Return (low, high, currency_hint) annual-ish CNY when possible."""
    if not text:
        return None, None, "CNY"
    m = _SALARY_RE.search(text.replace(",", ""))
    if not m:
        # single number + k
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*([kKwW万千])", text)
        if not m2:
            return None, None, "CNY"
        v = float(m2.group(1))
        u = m2.group(2)
        if u in "kK千":
            v *= 1000
        elif u in "wW万":
            v *= 10000
        # assume monthly if < 100000
        if v < 100000:
            v *= 12
        return v, v, "CNY"
    a, b = float(m.group("a")), float(m.group("b"))
    u = (m.group("u") or "").lower()
    if u in ("k",) or m.group("u") in ("K", "千"):
        a, b = a * 1000, b * 1000
    elif u in ("w",) or m.group("u") in ("W", "万"):
        a, b = a * 10000, b * 10000
    # monthly k ranges common in CN JDs
    if max(a, b) < 200000:
        a, b = a * 12, b * 12
    return a, b, "CNY"


def normalize_offer_row(row: dict, *, source: str) -> dict | None:
    """Map heterogeneous OfferShow / Levels / capture rows → Compass sample."""
    if not isinstance(row, dict):
        return None
    company = row.get("company") or row.get("company_name") or row.get("corp") or ""
    title = row.get("title") or row.get("job") or row.get("position") or row.get("job_name") or ""
    location = row.get("location") or row.get("city") or row.get("work_city") or ""
    level = row.get("level") or row.get("rank") or row.get("grade") or ""
    # money fields
    cash = row.get("p50") or row.get("total") or row.get("tc") or row.get("package") or row.get("salary")
    low = row.get("p25") or row.get("base") or row.get("salary_min") or row.get("min")
    high = row.get("p75") or row.get("salary_max") or row.get("max")
    currency = row.get("currency") or "CNY"
    if isinstance(cash, str):
        lo, hi, currency = parse_salary_token(cash)
        cash = ((lo or 0) + (hi or 0)) / 2 if lo or hi else None
        low = low or lo
        high = high or hi
    if isinstance(low, str):
        lo, _, _ = parse_salary_token(low)
        low = lo
    if isinstance(high, str):
        _, hi, _ = parse_salary_token(high)
        high = hi
    try:
        cash_f = float(cash) if cash is not None else None
    except (TypeError, ValueError):
        cash_f = None
    try:
        low_f = float(low) if low is not None else None
        high_f = float(high) if high is not None else None
    except (TypeError, ValueError):
        low_f = high_f = None
    if cash_f is None and low_f is not None and high_f is not None:
        cash_f = (low_f + high_f) / 2
    if cash_f is None and not title and not company:
        return None
    return {
        "company": str(company),
        "title": str(title),
        "location": str(location),
        "level": str(level),
        "p25": low_f,
        "p50": cash_f,
        "p75": high_f,
        "currency": currency,
        "source": source,
        "raw_id": row.get("id") or row.get("uuid") or row.get("offer_id"),
        "fetched_at": _utcnow(),
        "tags": list(row.get("tags") or []),
    }


def extract_rows_from_payload(data: Any, *, source: str) -> list[dict]:
    if data is None:
        return []
    if isinstance(data, list):
        return [n for r in data if (n := normalize_offer_row(r, source=source))]
    if not isinstance(data, dict):
        return []
    for key in ("data", "results", "rows", "offers", "items", "list", "salary_list", "hits"):
        if isinstance(data.get(key), list):
            return [n for r in data[key] if (n := normalize_offer_row(r, source=source))]
    # single object
    one = normalize_offer_row(data, source=source)
    return [one] if one else []


def aggregate_samples(samples: list[dict], *, title: str = "", location: str = "", level: str = "") -> dict:
    vals = [float(s["p50"]) for s in samples if s.get("p50") is not None]
    if not vals:
        return {
            "title": title,
            "location": location,
            "level": level,
            "sample_n": 0,
            "p25": None,
            "p50": None,
            "p75": None,
            "currency": "CNY",
            "source": "live_aggregate",
        }
    vals_sorted = sorted(vals)
    def pct(p: float) -> float:
        if len(vals_sorted) == 1:
            return vals_sorted[0]
        k = (len(vals_sorted) - 1) * p
        f = int(k)
        c = min(f + 1, len(vals_sorted) - 1)
        return vals_sorted[f] + (vals_sorted[c] - vals_sorted[f]) * (k - f)

    return {
        "title": title or (samples[0].get("title") or "live"),
        "location": location or (samples[0].get("location") or ""),
        "level": level or (samples[0].get("level") or ""),
        "sample_n": len(vals),
        "p25": round(pct(0.25), 0),
        "p50": round(pct(0.50), 0),
        "p75": round(pct(0.75), 0),
        "mean": round(statistics.mean(vals), 0),
        "currency": samples[0].get("currency") or "CNY",
        "source": "live_aggregate",
        "family": "live",
        "tags": ["live"],
    }


def salary_from_jobs(root: Path, *, query: str = "", limit: int = 30) -> list[dict]:
    """Extract salary strings from local matched JDs (posting-real)."""
    root = Path(root)
    samples: list[dict] = []
    q = (query or "").lower()
    jobs_dir = root / "jobs"
    if jobs_dir.is_dir():
        for d in jobs_dir.iterdir():
            if not d.is_dir():
                continue
            jd_path = d / "jd.json"
            if not jd_path.is_file():
                continue
            jd = json.loads(jd_path.read_text(encoding="utf-8"))
            blob = " ".join(
                [
                    str(jd.get("title") or ""),
                    str(jd.get("company") or ""),
                    str(jd.get("raw_text") or ""),
                    " ".join(jd.get("hard_requirements") or []),
                ]
            )
            if q and q not in blob.lower():
                continue
            lo, hi, cur = parse_salary_token(blob)
            if lo is None and hi is None:
                continue
            mid = ((lo or 0) + (hi or 0)) / 2 if (lo or hi) else None
            samples.append(
                {
                    "company": jd.get("company") or "",
                    "title": jd.get("title") or "",
                    "location": "",
                    "level": "",
                    "p25": lo,
                    "p50": mid,
                    "p75": hi,
                    "currency": cur,
                    "source": "job_posting",
                    "fetched_at": _utcnow(),
                    "tags": ["jd"],
                }
            )
            if len(samples) >= limit:
                break
    return samples


def salary_from_warehouse(root: Path, *, query: str = "", limit: int = 40) -> list[dict]:
    """Pull salary hints from warehouse raw text (career / ATS crawls)."""
    from .warehouse import search_jobs

    samples = []
    rows = search_jobs(Path(root), query or "", limit=limit)
    for r in rows:
        blob = f"{r.get('title')} {r.get('raw')}"
        lo, hi, cur = parse_salary_token(blob)
        if lo is None and hi is None:
            continue
        mid = ((lo or 0) + (hi or 0)) / 2 if (lo or hi) else None
        samples.append(
            {
                "company": r.get("company") or "",
                "title": r.get("title") or "",
                "location": r.get("location") or "",
                "level": "",
                "p25": lo,
                "p50": mid,
                "p75": hi,
                "currency": cur,
                "source": "warehouse_career",
                "fetched_at": _utcnow(),
                "tags": ["career", "ats"],
            }
        )
    return samples


def fetch_levels(
    cfg: dict,
    *,
    query: str,
    fetch_fn: FetchFn | None = None,
) -> list[dict]:
    """Levels.fyi-compatible JSON endpoint (user-configured; no built-in decrypt scrape)."""
    url = cfg.get("url") or os.environ.get("COMPASS_LEVELS_API") or ""
    if not url:
        return []
    method = (cfg.get("method") or "GET").upper()
    payload = {"q": query, "query": query, "search": query}
    if fetch_fn:
        data = fetch_fn(url, payload)
    else:
        data = default_fetch(url, payload, method=method)
    return extract_rows_from_payload(data, source="levels")


def fetch_extra_endpoints(
    endpoints: list,
    *,
    query: str,
    fetch_fn: FetchFn | None = None,
) -> list[dict]:
    """Arbitrary extra salary JSON endpoints from sources.json."""
    samples = []
    for ep in endpoints or []:
        if isinstance(ep, str):
            ep = {"url": ep, "name": "extra"}
        if not isinstance(ep, dict) or not ep.get("url"):
            continue
        name = str(ep.get("name") or "extra")
        method = (ep.get("method") or "GET").upper()
        payload = {"q": query, "query": query}
        try:
            if fetch_fn:
                data = fetch_fn(ep["url"], payload)
            else:
                data = default_fetch(ep["url"], payload, method=method)
            samples.extend(extract_rows_from_payload(data, source=name))
        except Exception:
            continue
    return samples


def fetch_offershow(
    cfg: dict,
    *,
    query: str,
    company: str = "",
    location: str = "",
    title: str = "",
    fetch_fn: FetchFn | None = None,
) -> list[dict]:
    base = (cfg.get("base_url") or "").rstrip("/")
    if not base:
        return []
    path = cfg.get("search_path") or "/salary/query"
    url = base + (path if path.startswith("/") else "/" + path)
    token = cfg.get("token") or ""
    payload = {
        "keyword": query or " ".join(x for x in (company, title, location) if x),
        "company": company or None,
        "city": location or None,
        "job": title or None,
        "access_token": token or None,
        "token": token or None,
    }
    payload = {k: v for k, v in payload.items() if v}
    method = (cfg.get("method") or "POST").upper()
    if fetch_fn:
        data = fetch_fn(url, payload)
    else:
        data = default_fetch(url, payload, method=method)
    return extract_rows_from_payload(data, source="offershow")


def fetch_http_live(
    cfg: dict,
    *,
    query: str,
    fetch_fn: FetchFn | None = None,
) -> list[dict]:
    url = cfg.get("url") or ""
    if not url:
        return []
    method = (cfg.get("method") or "GET").upper()
    payload = {"q": query, "query": query}
    if fetch_fn:
        data = fetch_fn(url, payload)
    else:
        data = default_fetch(url, payload, method=method)
    return extract_rows_from_payload(data, source="http_live")


def save_live_cache(root: Path, samples: list[dict], *, label: str = "live") -> Path:
    path = _cache_dir(root) / f"{label}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    # also append rolling live.jsonl
    roll = _cache_dir(root) / "latest.jsonl"
    with roll.open("a", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    return path


def load_live_cache(root: Path, *, max_age_sec: int = 3600, limit: int = 200) -> list[dict]:
    roll = _cache_dir(root) / "latest.jsonl"
    if not roll.is_file():
        return []
    age = time.time() - roll.stat().st_mtime
    if age > max_age_sec:
        return []
    out = []
    for ln in roll.read_text(encoding="utf-8").splitlines()[-limit:]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def ingest_live_file(root: Path, path: str | Path, *, source: str = "offershow_capture") -> dict:
    """Import user-exported OfferShow/Levels JSON/JSONL/CSV-ish salary rows."""
    root = Path(root)
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    samples: list[dict] = []
    if p.suffix.lower() == ".jsonl" or "\n{" in text[:200]:
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            samples.extend(extract_rows_from_payload(row if isinstance(row, list) else [row], source=source))
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # CSV header company,title,city,salary
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if not lines:
                return {"ingested": 0}
            headers = [h.strip() for h in lines[0].split(",")]
            for ln in lines[1:]:
                cols = [c.strip() for c in ln.split(",")]
                row = dict(zip(headers, cols))
                n = normalize_offer_row(row, source=source)
                if n:
                    samples.append(n)
        else:
            samples = extract_rows_from_payload(data, source=source)
    cache_path = save_live_cache(root, samples, label=source)
    # merge aggregate into user benchmarks
    if samples:
        agg = aggregate_samples(samples)
        bpath = _comp_dir(root) / "benchmarks.jsonl"
        with bpath.open("a", encoding="utf-8") as f:
            f.write(json.dumps(agg, ensure_ascii=False) + "\n")
    return {"ingested": len(samples), "cache": str(cache_path), "aggregate": aggregate_samples(samples) if samples else None}


def live_lookup(
    root: Path,
    *,
    query: str = "",
    title: str = "",
    company: str = "",
    location: str = "",
    level: str = "",
    sources: list[str] | None = None,
    accept_tos_risk: bool = False,
    use_cache: bool = True,
    fetch_fn: FetchFn | None = None,
    limit: int = 50,
) -> dict:
    """Fetch live samples and return aggregate + raw hits."""
    root = Path(root)
    srcs = sources or ["offershow", "http", "levels", "jobs", "career", "cache"]
    need_net = any(s in ("offershow", "http", "levels", "extra") for s in srcs)
    if need_net:
        require_tos_risk(accept_tos_risk)
    cfg = load_sources(root)
    q = query or " ".join(x for x in (company, title, location, level) if x)
    samples: list[dict] = []
    errors: list[dict] = []
    used: list[str] = []

    if "cache" in srcs and use_cache:
        cached = load_live_cache(root, max_age_sec=int(cfg.get("ttl_seconds") or 3600))
        if cached:
            samples.extend(cached)
            used.append("cache")

    if "jobs" in srcs:
        js = salary_from_jobs(root, query=q or title, limit=limit)
        if js:
            samples.extend(js)
            used.append("jobs")

    if "career" in srcs or "ats" in srcs or "warehouse" in srcs:
        try:
            ws = salary_from_warehouse(root, query=q or title, limit=limit)
            if ws:
                samples.extend(ws)
                used.append("career")
        except Exception as e:
            errors.append({"source": "career", "error": str(e)})

    if "offershow" in srcs:
        try:
            rows = fetch_offershow(
                cfg.get("offershow") or {},
                query=q,
                company=company,
                location=location,
                title=title,
                fetch_fn=fetch_fn,
            )
            if rows:
                samples.extend(rows)
                used.append("offershow")
            elif not (cfg.get("offershow") or {}).get("base_url"):
                errors.append(
                    {
                        "source": "offershow",
                        "error": "not_configured",
                        "hint": "Set COMPASS_OFFERSHOW_API or content/comp/sources.json; "
                        "or `comp ingest-live --file`. Official OfferShow is WeChat-only.",
                    }
                )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, PermissionError, OSError) as e:
            errors.append({"source": "offershow", "error": str(e)})

    if "http" in srcs:
        try:
            rows = fetch_http_live(cfg.get("http") or {}, query=q, fetch_fn=fetch_fn)
            if rows:
                samples.extend(rows)
                used.append("http")
            elif not (cfg.get("http") or {}).get("url"):
                errors.append(
                    {
                        "source": "http",
                        "error": "not_configured",
                        "hint": "Set COMPASS_COMP_LIVE_URL to a JSON search endpoint",
                    }
                )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            errors.append({"source": "http", "error": str(e)})

    if "levels" in srcs:
        try:
            rows = fetch_levels(cfg.get("levels") or {}, query=q, fetch_fn=fetch_fn)
            if rows:
                samples.extend(rows)
                used.append("levels")
            elif not (cfg.get("levels") or {}).get("url"):
                errors.append(
                    {
                        "source": "levels",
                        "error": "not_configured",
                        "hint": "Set COMPASS_LEVELS_API to a Levels-compatible JSON API",
                    }
                )
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            errors.append({"source": "levels", "error": str(e)})

    if "extra" in srcs:
        extras = fetch_extra_endpoints(cfg.get("extra_endpoints") or [], query=q, fetch_fn=fetch_fn)
        if extras:
            samples.extend(extras)
            used.append("extra")

    # filter by tokens
    def _ok(s: dict) -> bool:
        blob = f"{s.get('title')} {s.get('company')} {s.get('location')} {s.get('level')}".lower()
        for tok in (title, company, location, level):
            if tok and tok.lower() not in blob and tok.lower() not in q.lower():
                if q and any(t in blob for t in q.lower().split() if len(t) > 1):
                    continue
                if tok.lower() not in blob:
                    return False
        return True

    filtered = [s for s in samples if _ok(s)] or samples
    # multi-source plausibility: drop fabricated outliers (e.g. 1000万 rumor)
    from .plausibility import filter_salary_samples

    kept, rejected = filter_salary_samples(filtered)
    filtered = kept[:limit]
    if filtered and any(u in used for u in ("offershow", "http", "levels", "jobs", "career", "extra")):
        save_live_cache(root, filtered, label="query")

    agg = aggregate_samples(filtered, title=title or q, location=location, level=level)
    return {
        "mode": "live",
        "query": q,
        "sources_used": used,
        "errors": errors,
        "sample_n": len(filtered),
        "rejected_implausible_n": len(rejected),
        "rejected_implausible": rejected[:10],
        "aggregate": agg,
        "hits": filtered[:20],
        "disclaimer": "live_multi_source_filtered; rumor_salaries_rejected; company_career_ats_ok",
    }
