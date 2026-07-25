"""Cross-job practice rollup + report center export (intervAI / compas P1)."""

from __future__ import annotations

import json
from pathlib import Path

# Default minutes per scored answer turn
MINUTES_PER_ANSWER = 4

_DIMS = ("substance", "structure", "relevance", "credibility", "jd_fit")


def practice_rollup(root: Path, *, minutes_per_answer: int = MINUTES_PER_ANSWER) -> dict:
    root = Path(root)
    iv = root / "interviews"
    sessions = []
    total_answers = 0
    jd_fits: list[float] = []
    dim_points: dict[str, list[tuple[str, float]]] = {d: [] for d in _DIMS}
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
            ts = sc.get("updated_at") or ""
            for dim in _DIMS:
                if dim in agg and agg[dim] is not None:
                    dim_points[dim].append((ts, float(agg[dim])))
            sessions.append(
                {
                    "job_id": sc.get("job_id") or d.name,
                    "answers": n,
                    "est_minutes": n * minutes_per_answer,
                    "gate_pass_rate": (sc.get("aggregate") or {}).get("gate_pass_rate"),
                    "jd_fit": jd_fit,
                    "scores": {k: agg.get(k) for k in _DIMS if k in agg},
                    "real_outcome": sc.get("real_outcome"),
                    "updated_at": sc.get("updated_at"),
                }
            )
    sessions.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    avg = round(sum(jd_fits) / len(jd_fits), 2) if jd_fits else 0.0

    # chronological series per dimension (oldest → newest)
    dimension_series: dict[str, list[dict]] = {}
    for dim, pts in dim_points.items():
        pts_sorted = sorted(pts, key=lambda x: str(x[0] or ""))
        dimension_series[dim] = [{"ts": t, "avg": v} for t, v in pts_sorted]

    return {
        "sessions": len(sessions),
        "total_answers": total_answers,
        "est_minutes_total": total_answers * minutes_per_answer,
        "avg_jd_fit": avg,
        "recent": sessions[:10],
        "timeline": sessions[:20],
        "dimension_series": dimension_series,
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
        "## Progress",
        "",
        "| dim | points | first | last | delta |",
        "|-----|--------|-------|------|-------|",
    ]
    series = rollup.get("dimension_series") or {}
    for dim in _DIMS:
        pts = series.get(dim) or []
        if not pts:
            lines.append(f"| {dim} | 0 | — | — | — |")
            continue
        first = pts[0]["avg"]
        last = pts[-1]["avg"]
        delta = round(last - first, 2)
        lines.append(f"| {dim} | {len(pts)} | {first} | {last} | {delta:+} |")
    lines.extend(
        [
            "",
            "## Timeline",
            "",
            "| updated | job_id | answers | jd_fit | outcome |",
            "|---------|--------|---------|--------|---------|",
        ]
    )
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
