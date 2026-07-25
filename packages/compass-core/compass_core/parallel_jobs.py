"""Parallel helpers for match-explain / resume-patch (compas v0.21)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .jd import ParsedJD
from .evidence import load_evidence


def rebuild_match_explain(root: Path, job_id: str) -> dict:
    from .match_explain import (
        build_requirement_matrix,
        render_match_explain_md,
        summarize_matrix,
    )

    root = Path(root)
    job_dir = root / "jobs" / job_id
    jd_path = job_dir / "jd.json"
    if not jd_path.is_file():
        return {"job_id": job_id, "error": f"missing {jd_path}"}
    jd_data = json.loads(jd_path.read_text(encoding="utf-8"))
    jd = ParsedJD(**{k: jd_data[k] for k in ParsedJD.__dataclass_fields__ if k in jd_data})
    evidence = load_evidence(root)
    rows = build_requirement_matrix(jd, evidence)
    summary = summarize_matrix(rows, evidence_count=len(evidence))
    match_path = job_dir / "match.json"
    profile_fit = {"status": "pass", "blockers": [], "warnings": []}
    if match_path.is_file():
        match_data = json.loads(match_path.read_text(encoding="utf-8"))
        match_data["requirement_matrix"] = [r.to_dict() for r in rows]
        match_data["match_explain"] = summary
        from .intake import load_profile
        from .profile_fit import apply_to_explain, assess_profile_fit

        fit = assess_profile_fit(jd, load_profile(root))
        summary = apply_to_explain(summary, fit)
        match_data["match_explain"] = summary
        match_data["profile_fit"] = fit
        profile_fit = fit
        match_path.write_text(json.dumps(match_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (job_dir / "match_explain.md").write_text(
        render_match_explain_md(jd, rows, summary, profile_fit=profile_fit), encoding="utf-8"
    )
    return {
        "job_id": job_id,
        "match_explain": summary,
        "rows": len(rows),
        "path": str(job_dir / "match_explain.md"),
    }


def match_explain_many(root: Path, job_ids: list[str], *, workers: int = 4) -> dict:
    workers = max(1, min(int(workers or 4), 8))
    results: list[dict] = []
    if workers == 1 or len(job_ids) <= 1:
        for jid in job_ids:
            results.append(rebuild_match_explain(root, jid))
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(rebuild_match_explain, root, jid): jid for jid in job_ids}
            for fut in as_completed(futs):
                results.append(fut.result())
    return {"count": len(results), "jobs": results, "workers": workers}


def resume_patch_many(root: Path, job_ids: list[str], *, workers: int = 4, theme: str | None = None) -> dict:
    from .resume import apply_and_save

    workers = max(1, min(int(workers or 4), 8))
    results: list[dict] = []

    def _one(jid: str) -> dict:
        try:
            out = apply_and_save(Path(root), jid, theme=theme)
            out["job_id"] = jid
            return out
        except Exception as e:
            return {"job_id": jid, "error": str(e)}

    if workers == 1 or len(job_ids) <= 1:
        for jid in job_ids:
            results.append(_one(jid))
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_one, jid) for jid in job_ids]
            for fut in as_completed(futs):
                results.append(fut.result())
    return {"count": len(results), "jobs": results, "workers": workers}
