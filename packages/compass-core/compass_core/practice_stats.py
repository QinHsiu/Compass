"""Cross-job practice rollup + report center export (intervAI / compas P1)."""

from __future__ import annotations

import json
from pathlib import Path

# Default minutes per scored answer turn
MINUTES_PER_ANSWER = 4


def practice_rollup(root: Path, *, minutes_per_answer: int = MINUTES_PER_ANSWER) -> dict:
    root = Path(root)
    iv = root / "interviews"
    sessions = []
    total_answers = 0
    jd_fits: list[float] = []
    if iv.is_dir():
        for d in sorted(iv.iterdir()):
            if not d.is_dir():
                continue
            sc_path = d / "scorecard.json"
            if not sc_path.is_file():
                continue
            sc = json.loads(sc_path.read_text(encoding="utf-8"))
            n = len(sc.get("answers") or [])
            total_answers += n
            agg = (sc.get("aggregate") or {}).get("scores") or {}
            jd_fit = float(agg.get("jd_fit") or 0)
            if n:
                jd_fits.append(jd_fit)
            sessions.append(
                {
                    "job_id": sc.get("job_id") or d.name,
                    "answers": n,
                    "est_minutes": n * minutes_per_answer,
                    "gate_pass_rate": (sc.get("aggregate") or {}).get("gate_pass_rate"),
                    "jd_fit": jd_fit,
                    "real_outcome": sc.get("real_outcome"),
                    "updated_at": sc.get("updated_at"),
                }
            )
    sessions.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    avg = round(sum(jd_fits) / len(jd_fits), 2) if jd_fits else 0.0
    return {
        "sessions": len(sessions),
        "total_answers": total_answers,
        "est_minutes_total": total_answers * minutes_per_answer,
        "avg_jd_fit": avg,
        "recent": sessions[:10],
        "timeline": sessions[:20],
    }


def export_practice_center(root: Path) -> dict:
    """Write content/reports/practice_center.md (+ .json)."""
    root = Path(root)
    rollup = practice_rollup(root)
    out_dir = root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Practice center",
        "",
        f"- sessions: **{rollup['sessions']}**",
        f"- total answers: **{rollup['total_answers']}**",
        f"- est. practice minutes: **{rollup['est_minutes_total']}** "
        f"(×{MINUTES_PER_ANSWER} min/answer)",
        f"- avg jd_fit: **{rollup['avg_jd_fit']}**",
        "",
        "## Timeline",
        "",
        "| updated | job_id | answers | jd_fit | outcome |",
        "|---------|--------|---------|--------|---------|",
    ]
    for s in rollup.get("timeline") or []:
        lines.append(
            f"| {s.get('updated_at') or '—'} | `{s.get('job_id')}` | {s.get('answers')} | "
            f"{s.get('jd_fit')} | {s.get('real_outcome') or '—'} |"
        )
    md_path = out_dir / "practice_center.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_path = out_dir / "practice_center.json"
    json_path.write_text(json.dumps(rollup, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(md_path), "json": str(json_path), **rollup}
