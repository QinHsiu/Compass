"""Minimal MCP-style stdio JSON-RPC server for Compass artifacts.

Works with or without the `mcp` package: if mcp is installed, uses FastMCP;
otherwise exposes a simple line-protocol demo via `compass_mcp.server:list_tools`.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from compass_core.evidence import build_index, load_evidence
from compass_core.paths import content_root, ensure_dirs
from compass_core.track import load_board, upsert


def _root() -> Path:
    root = content_root(os.environ.get("COMPASS_ROOT"))
    ensure_dirs(root)
    return root


def tool_list_jobs() -> list[dict]:
    root = _root()
    jobs = []
    for d in sorted((root / "jobs").glob("*/match.json")):
        jobs.append(json.loads(d.read_text(encoding="utf-8")))
    return jobs


def tool_get_artifact(kind: str, job_id: str) -> str:
    root = _root()
    mapping = {
        "match": root / "jobs" / job_id / "match.json",
        "jd": root / "jobs" / job_id / "jd.md",
        "resume": root / "resumes" / job_id / "resume.md",
        "interview": root / "interviews" / job_id / "session.md",
        "diagnose": root / "diagnoses" / job_id / "report.md",
        "bridge": root / "diagnoses" / job_id / "bridge_plan.md",
    }
    path = mapping.get(kind)
    if not path or not path.is_file():
        return json.dumps({"error": f"missing {kind}/{job_id}"})
    return path.read_text(encoding="utf-8")


def tool_list_evidence() -> list[dict]:
    root = _root()
    build_index(root)
    return [e.to_dict() for e in load_evidence(root)]


def tool_track(job_id: str, status: str, note: str = "") -> dict:
    return upsert(_root(), job_id, status, note=note)


def tool_overview() -> dict:
    root = _root()
    return {
        "jobs": tool_list_jobs(),
        "evidence_count": len(load_evidence(root)),
        "track": load_board(root).get("items") or [],
    }


def tool_jobs_search(q: str = "", location: str = "", limit: int = 20) -> dict:
    """Search local job warehouse (Four-Leaf / clover-style local index)."""
    from compass_core.warehouse import search_jobs, warehouse_stats

    root = _root()
    hits = search_jobs(root, q or "", location=location or None, limit=limit or 20)
    return {"stats": warehouse_stats(root), "hits": hits}


def tool_jobs_get(job_id: str) -> dict:
    from compass_core.warehouse import search_jobs

    root = _root()
    # exact id lookup via filter
    for row in search_jobs(root, "", limit=200):
        if row.get("job_id") == job_id:
            return row
    path = root / "jobs" / job_id / "match.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"error": f"missing {job_id}"}


def tool_comp_lookup(
    title: str = "",
    level: str = "",
    location: str = "",
    cash: float | None = None,
    live: bool = False,
    query: str = "",
    company: str = "",
) -> dict:
    import os

    from compass_core.comp_bench import coach_script, lookup_comp, lookup_comp_merged

    accept = os.environ.get("COMPASS_ACCEPT_TOS_RISK", "").lower() in ("1", "true", "yes")
    try:
        if live:
            out = lookup_comp_merged(
                _root(),
                title=title,
                level=level,
                location=location,
                company=company,
                query=query or title,
                live=True,
                accept_tos_risk=accept,
            )
        else:
            out = lookup_comp(_root(), title=title or query, level=level, location=location)
    except PermissionError as e:
        return {"error": str(e), "hint": "Set COMPASS_ACCEPT_TOS_RISK=1 for live"}
    out["coach"] = coach_script(out, your_cash=cash)
    return out


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print(
            "mcp package not installed; tools available via compass_mcp.server imports.\n"
            "pip install mcp",
            file=sys.stderr,
        )
        # interactive one-shot
        print(json.dumps(tool_overview(), ensure_ascii=False, indent=2))
        return

    mcp = FastMCP("compass")

    @mcp.tool()
    def list_jobs() -> str:
        """List matched jobs in the Compass content vault."""
        return json.dumps(tool_list_jobs(), ensure_ascii=False, indent=2)

    @mcp.tool()
    def get_artifact(kind: str, job_id: str) -> str:
        """Get artifact: match|jd|resume|interview|diagnose|bridge for job_id."""
        return tool_get_artifact(kind, job_id)

    @mcp.tool()
    def list_evidence() -> str:
        """List evidence items."""
        return json.dumps(tool_list_evidence(), ensure_ascii=False, indent=2)

    @mcp.tool()
    def track_job(job_id: str, status: str, note: str = "") -> str:
        """Update track board status."""
        return json.dumps(tool_track(job_id, status, note), ensure_ascii=False, indent=2)

    @mcp.tool()
    def overview() -> str:
        """Vault overview: jobs, evidence count, track."""
        return json.dumps(tool_overview(), ensure_ascii=False, indent=2)

    @mcp.tool()
    def jobs_search(q: str = "", location: str = "", limit: int = 20) -> str:
        """Search local warehouse (100k-ready FTS). Not a hosted clover dump."""
        return json.dumps(tool_jobs_search(q, location, limit), ensure_ascii=False, indent=2)

    @mcp.tool()
    def jobs_get(job_id: str) -> str:
        """Get one warehouse or matched job by id."""
        return json.dumps(tool_jobs_get(job_id), ensure_ascii=False, indent=2)

    @mcp.tool()
    def comp_lookup(
        title: str = "",
        level: str = "",
        location: str = "",
        cash: float = 0,
        live: bool = False,
        query: str = "",
        company: str = "",
    ) -> str:
        """Compensation lookup. live=True needs COMPASS_ACCEPT_TOS_RISK=1 + OfferShow API or ingest."""
        return json.dumps(
            tool_comp_lookup(
                title, level, location, cash if cash else None, live=live, query=query, company=company
            ),
            ensure_ascii=False,
            indent=2,
        )

    mcp.run()


if __name__ == "__main__":
    main()
