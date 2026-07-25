"""Terminal pipeline board (career-ops Dashboard TUI-lite, stdlib only)."""

from __future__ import annotations

import json
from pathlib import Path

from .practice_stats import practice_rollup
from .track import load_board


def pipeline_board(root: Path) -> dict:
    root = Path(root)
    jobs = []
    jobs_dir = root / "jobs"
    if jobs_dir.is_dir():
        for d in sorted(jobs_dir.iterdir()):
            if not d.is_dir():
                continue
            mpath = d / "match.json"
            if not mpath.is_file():
                continue
            m = json.loads(mpath.read_text(encoding="utf-8"))
            g = m.get("grade") or {}
            jobs.append(
                {
                    "job_id": m.get("job_id") or d.name,
                    "title": m.get("title") or "",
                    "company": m.get("company") or "",
                    "score": m.get("score"),
                    "letter": g.get("letter"),
                    "score_100": g.get("score_100"),
                    "recommendation": (m.get("match_explain") or {}).get("recommendation"),
                }
            )
    jobs.sort(key=lambda j: float(j.get("score_100") or j.get("score") or 0), reverse=True)
    track = load_board(root).get("items") or []
    practice = practice_rollup(root)
    batches = []
    bdir = root / "batches"
    if bdir.is_dir():
        for d in sorted(bdir.iterdir(), reverse=True)[:5]:
            sp = d / "summary.json"
            if sp.is_file():
                try:
                    s = json.loads(sp.read_text(encoding="utf-8"))
                    batches.append(
                        {
                            "batch_id": s.get("batch_id") or d.name,
                            "count": s.get("count"),
                            "created_at": s.get("created_at"),
                        }
                    )
                except json.JSONDecodeError:
                    pass
    return {
        "jobs": jobs[:15],
        "track": track[:15],
        "practice": {
            "sessions": practice.get("sessions"),
            "total_answers": practice.get("total_answers"),
            "avg_jd_fit": practice.get("avg_jd_fit"),
        },
        "batches": batches,
    }


def format_pipeline_board(data: dict) -> str:
    lines = [
        "╔══════════════════════════════════════════════════════════╗",
        "║              Compass Pipeline Board (TUI)                ║",
        "╚══════════════════════════════════════════════════════════╝",
        "",
        f"Practice  sessions={data['practice'].get('sessions')}  "
        f"answers={data['practice'].get('total_answers')}  "
        f"avg_jd_fit={data['practice'].get('avg_jd_fit')}",
        "",
        "── Jobs (top) ──",
        f"{'letter':6} {'100':>4} {'rec':8} {'title':28} {'company':16} job_id",
    ]
    for j in data.get("jobs") or []:
        lines.append(
            f"{str(j.get('letter') or '—'):6} {str(j.get('score_100') or '—'):>4} "
            f"{str(j.get('recommendation') or '—')[:8]:8} "
            f"{str(j.get('title') or '')[:28]:28} "
            f"{str(j.get('company') or '')[:16]:16} {j.get('job_id')}"
        )
    lines += ["", "── Track ──"]
    for t in data.get("track") or []:
        lines.append(
            f"  [{t.get('status')}] {t.get('title') or t.get('job_id')}  "
            f"{t.get('follow_up_due') or ''}"
        )
    if not data.get("track"):
        lines.append("  (empty)")
    lines += ["", "── Recent batches ──"]
    for b in data.get("batches") or []:
        lines.append(f"  {b.get('created_at')}  {b.get('batch_id')}  n={b.get('count')}")
    if not data.get("batches"):
        lines.append("  (none)")
    lines.append("")
    return "\n".join(lines)
