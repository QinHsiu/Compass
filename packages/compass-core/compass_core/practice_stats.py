"""Cross-job practice rollup (intervAI Round 11)."""

from __future__ import annotations

import json
from pathlib import Path


def practice_rollup(root: Path) -> dict:
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
                    "gate_pass_rate": (sc.get("aggregate") or {}).get("gate_pass_rate"),
                    "jd_fit": jd_fit,
                    "updated_at": sc.get("updated_at"),
                }
            )
    sessions.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    avg = round(sum(jd_fits) / len(jd_fits), 2) if jd_fits else 0.0
    return {
        "sessions": len(sessions),
        "total_answers": total_answers,
        "avg_jd_fit": avg,
        "recent": sessions[:10],
    }
