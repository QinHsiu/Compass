"""Local job warehouse — SQLite FTS, 100k-scale architecture (Four-Leaf / clover parity)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def warehouse_path(root: Path) -> Path:
    d = Path(root) / "warehouse"
    d.mkdir(parents=True, exist_ok=True)
    return d / "jobs.sqlite"


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _conn(root: Path) -> sqlite3.Connection:
    path = warehouse_path(root)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT,
            source TEXT,
            fetched_at TEXT,
            raw TEXT
        )
        """
    )
    con.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
            job_id, title, company, location, raw,
            content='jobs', content_rowid='rowid'
        )
        """
    )
    # triggers for fts sync (idempotent-ish: ignore errors on re-create)
    try:
        con.execute(
            """
            CREATE TRIGGER IF NOT EXISTS jobs_ai AFTER INSERT ON jobs BEGIN
              INSERT INTO jobs_fts(rowid, job_id, title, company, location, raw)
              VALUES (new.rowid, new.job_id, new.title, new.company, new.location, new.raw);
            END
            """
        )
        con.execute(
            """
            CREATE TRIGGER IF NOT EXISTS jobs_ad AFTER DELETE ON jobs BEGIN
              INSERT INTO jobs_fts(jobs_fts, rowid, job_id, title, company, location, raw)
              VALUES ('delete', old.rowid, old.job_id, old.title, old.company, old.location, old.raw);
            END
            """
        )
    except sqlite3.OperationalError:
        pass
    con.commit()
    return con


def _job_id(url: str, title: str, company: str) -> str:
    h = hashlib.sha1(f"{url}|{title}|{company}".encode("utf-8")).hexdigest()[:12]
    slug = "".join(c if c.isalnum() else "_" for c in f"{company}_{title}".lower())[:40]
    return f"wh_{slug}_{h}"


def upsert_job(
    root: Path,
    *,
    title: str,
    company: str = "",
    location: str = "",
    url: str = "",
    source: str = "import",
    raw: str = "",
    job_id: str | None = None,
) -> str:
    jid = job_id or _job_id(url, title, company)
    with _conn(root) as con:
        # delete+insert keeps fts simpler across sqlite versions
        con.execute("DELETE FROM jobs WHERE job_id = ?", (jid,))
        con.execute(
            """
            INSERT INTO jobs (job_id, title, company, location, url, source, fetched_at, raw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (jid, title, company, location, url, source, _utcnow(), raw[:20000]),
        )
        con.commit()
    return jid


def ingest_jsonl(root: Path, path: str | Path) -> dict:
    """Ingest JSONL lines with title/company/location/url/raw."""
    root = Path(root)
    p = Path(path)
    n = 0
    errors = 0
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            row = json.loads(ln)
            upsert_job(
                root,
                title=str(row.get("title") or "untitled"),
                company=str(row.get("company") or ""),
                location=str(row.get("location") or ""),
                url=str(row.get("url") or ""),
                source=str(row.get("source") or "jsonl"),
                raw=str(row.get("raw") or row.get("text") or ""),
                job_id=row.get("job_id"),
            )
            n += 1
        except Exception:
            errors += 1
    from .observability import audit_event, inc_metric

    audit_event(root, "warehouse_ingest", count=n, errors=errors, path=str(p))
    if errors:
        inc_metric(root, "warehouse_ingest_error", errors)
    return {"ingested": n, "errors": errors, "path": str(warehouse_path(root))}


def ingest_rows(root: Path, rows: list[dict], *, source: str = "rows") -> dict:
    n = 0
    for row in rows:
        upsert_job(
            root,
            title=str(row.get("title") or "untitled"),
            company=str(row.get("company") or ""),
            location=str(row.get("location") or ""),
            url=str(row.get("url") or ""),
            source=source,
            raw=str(row.get("raw") or row.get("text") or ""),
            job_id=row.get("job_id"),
        )
        n += 1
    from .observability import audit_event

    audit_event(root, "warehouse_ingest", count=n, source=source)
    return {"ingested": n, "path": str(warehouse_path(root))}


def existing_urls(root: Path) -> set[str]:
    """URLs already in warehouse (for watchlist dedupe)."""
    root = Path(root)
    urls: set[str] = set()
    with _conn(root) as con:
        for row in con.execute("SELECT url FROM jobs WHERE url IS NOT NULL AND url != ''"):
            u = (row["url"] or "").strip()
            if u:
                urls.add(u)
    return urls


def search_jobs(
    root: Path,
    q: str = "",
    *,
    location: str | None = None,
    limit: int = 20,
) -> list[dict]:
    root = Path(root)
    limit = max(1, min(int(limit or 20), 200))
    with _conn(root) as con:
        if q.strip():
            # FTS query; fallback LIKE
            try:
                sql = (
                    "SELECT j.* FROM jobs j JOIN jobs_fts f ON j.rowid = f.rowid "
                    "WHERE jobs_fts MATCH ? "
                )
                params: list = [q.strip()]
                if location:
                    sql += "AND j.location LIKE ? "
                    params.append(f"%{location}%")
                sql += "LIMIT ?"
                params.append(limit)
                rows = con.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                rows = con.execute(
                    "SELECT * FROM jobs WHERE title LIKE ? OR company LIKE ? OR raw LIKE ? LIMIT ?",
                    (f"%{q}%", f"%{q}%", f"%{q}%", limit),
                ).fetchall()
        else:
            if location:
                rows = con.execute(
                    "SELECT * FROM jobs WHERE location LIKE ? ORDER BY fetched_at DESC LIMIT ?",
                    (f"%{location}%", limit),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT * FROM jobs ORDER BY fetched_at DESC LIMIT ?", (limit,)
                ).fetchall()
    return [dict(r) for r in rows]


def warehouse_stats(root: Path) -> dict:
    with _conn(root) as con:
        n = con.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
    return {"count": n, "path": str(warehouse_path(root))}


def seed_fixture(root: Path, n: int = 100) -> dict:
    """Synthetic rows for scale/tests (not real postings)."""
    rows = []
    for i in range(n):
        rows.append(
            {
                "job_id": f"wh_fixture_{i:05d}",
                "title": f"ML Engineer {i % 17}",
                "company": f"Acme{i % 50}",
                "location": ["Remote", "Shanghai", "Beijing", "SF"][i % 4],
                "url": f"https://example.com/jobs/{i}",
                "raw": f"Python LLM RAG training inference job {i}",
                "source": "fixture",
            }
        )
    return ingest_rows(root, rows, source="fixture")
