"""Structured resume + JSON Patch + ATS report."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import jsonpatch

from .evidence import load_evidence
from .gate import filter_verified_bullets
from .jd import ParsedJD
from .match import MatchResult


def empty_resume(name: str = "") -> dict:
    return {
        "version": 1,
        "basics": {"name": name, "summary": "", "links": []},
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
    }


def load_resume(path: Path) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return empty_resume()


def resume_to_markdown(data: dict) -> str:
    lines = [f"# {data.get('basics', {}).get('name') or 'Resume'}", ""]
    summary = data.get("basics", {}).get("summary") or ""
    if summary:
        lines += ["## Summary", summary, ""]
    skills = data.get("skills") or []
    if skills:
        lines += ["## Skills", ", ".join(skills), ""]
    for section, key in (("Experience", "experience"), ("Projects", "projects")):
        items = data.get(key) or []
        if not items:
            continue
        lines.append(f"## {section}")
        for it in items:
            title = it.get("title") or it.get("name") or "Item"
            org = it.get("org") or it.get("company") or ""
            lines.append(f"### {title}" + (f" — {org}" if org else ""))
            for b in it.get("bullets") or []:
                eid = it.get("evidence_id") or ""
                suffix = f" [{eid}]" if eid else ""
                lines.append(f"- {b}{suffix}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_targeted_resume(
    base: dict,
    jd: ParsedJD,
    match: MatchResult,
    root: Path,
) -> tuple[dict, list[dict], dict]:
    """
    Produce updated resume, jsonpatch ops, ats_report.
    Only attach evidence-backed bullets from match hits.
    """
    evidence = load_evidence(root)
    updated = deepcopy(base)
    # merge skills from hits + keyword hits
    skill_set = list(dict.fromkeys((updated.get("skills") or []) + match.keyword_hits[:15]))
    updated["skills"] = skill_set

    # ensure projects/experience bullets from top evidence
    projects = list(updated.get("projects") or [])
    existing_eids = {p.get("evidence_id") for p in projects}
    for hit in match.evidence_hits[:5]:
        eid = hit["evidence_id"]
        if eid in existing_eids:
            continue
        ev = next((e for e in evidence if e.id == eid), None)
        if not ev:
            continue
        bullet = (ev.metrics or ev.actions or ev.title).split("\n")[0][:200]
        kept, rejected = filter_verified_bullets([f"{bullet} ({eid})"], evidence)
        if not kept:
            continue
        projects.append(
            {
                "name": ev.title,
                "evidence_id": eid,
                "bullets": kept,
                "skills": ev.skills,
            }
        )
    updated["projects"] = projects

    # summary: narrative only from hits
    if match.evidence_hits and not (updated.get("basics") or {}).get("summary"):
        tops = ", ".join(h["evidence_id"] for h in match.evidence_hits[:3])
        updated.setdefault("basics", {})["summary"] = (
            f"Targeting {jd.title} @ {jd.company}. Anchored on evidence: {tops}."
        )

    patch = jsonpatch.make_patch(base, updated)
    ops = list(patch)
    ats = ats_report(updated, jd, match)
    return updated, ops, ats


def ats_report(resume: dict, jd: ParsedJD, match: MatchResult) -> dict:
    text = json.dumps(resume, ensure_ascii=False).lower()
    present = [k for k in jd.keywords if k.lower() in text]
    missing = [k for k in jd.keywords if k.lower() not in text]
    bullets = []
    for key in ("experience", "projects"):
        for it in resume.get(key) or []:
            bullets.extend(it.get("bullets") or [])
    unverified = [b for b in bullets if "UNVERIFIED" in b.upper()]
    return {
        "keyword_coverage": round(len(present) / max(len(jd.keywords), 1), 3),
        "keywords_present": present,
        "keywords_missing": missing,
        "hard_gaps_remaining": match.hard_gaps,
        "bullet_count": len(bullets),
        "unverified_bullets": unverified,
        "match_score": match.score,
            "checklist": {
                "has_skills_section": bool(resume.get("skills")),
                "has_evidence_citations": "ev_" in json.dumps(resume),
                "no_unverified_as_fact": len(unverified) == 0,
            },
        }


def apply_and_save(
    root: Path,
    job_id: str,
    base: dict | None = None,
    theme: str | None = None,
) -> dict:
    job_dir = root / "jobs" / job_id
    jd_data = json.loads((job_dir / "jd.json").read_text(encoding="utf-8"))
    match_data = json.loads((job_dir / "match.json").read_text(encoding="utf-8"))
    from .jd import ParsedJD
    from .match import MatchResult
    from .templates import recommend_theme, render_all

    jd = ParsedJD(**{k: jd_data[k] for k in ParsedJD.__dataclass_fields__})
    match = MatchResult(**{k: match_data[k] for k in MatchResult.__dataclass_fields__})

    out_dir = root / "resumes" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    resume_path = out_dir / "resume.json"
    base_resume = base if base is not None else load_resume(resume_path)
    # keep prior as before
    before = deepcopy(base_resume)
    updated, ops, ats = build_targeted_resume(base_resume, jd, match, root)
    picked = theme or recommend_theme(jd.keywords, role=jd.title)
    updated["theme"] = picked

    (out_dir / "resume.before.json").write_text(
        json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    resume_path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "patch.json").write_text(
        json.dumps(ops, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # unified-ish diff summary
    diff_lines = [f"--- resume.before.json", f"+++ resume.json", f"@@ patch ops: {len(ops)} @@"]
    for op in ops[:50]:
        diff_lines.append(f"{op.get('op')} {op.get('path')} {json.dumps(op.get('value', ''), ensure_ascii=False)[:120]}")
    (out_dir / "patch.diff").write_text("\n".join(diff_lines) + "\n", encoding="utf-8")
    (out_dir / "ats_report.json").write_text(
        json.dumps(ats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rendered = render_all(updated, out_dir, theme=picked)
    return {
        "job_id": job_id,
        "ops": len(ops),
        "ats": ats,
        "theme": picked,
        "render": rendered,
        "path": str(out_dir),
    }
