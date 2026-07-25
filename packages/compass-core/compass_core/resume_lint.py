"""One-page resume density lint (open-resume Round 9)."""

from __future__ import annotations

import json


def lint_resume_density(resume: dict) -> dict:
    """Return pass/warn/fail density flags for ATS one-page budget."""
    bullets: list[str] = []
    for key in ("experience", "projects"):
        for it in resume.get(key) or []:
            bullets.extend(it.get("bullets") or [])
    skills = resume.get("skills") or []
    summary = (resume.get("basics") or {}).get("summary") or ""
    blob = json.dumps(resume, ensure_ascii=False)
    char_n = len(blob)
    bullet_n = len(bullets)
    section_n = sum(1 for k in ("experience", "projects", "education", "skills") if resume.get(k))
    flags: list[str] = []
    status = "pass"

    if bullet_n > 18:
        flags.append(f"too_many_bullets:{bullet_n}>18")
        status = "fail"
    elif bullet_n > 12:
        flags.append(f"bullet_warn:{bullet_n}>12")
        status = "warn" if status == "pass" else status

    if char_n > 12000:
        flags.append(f"char_overflow:{char_n}>12000")
        status = "fail"
    elif char_n > 8000:
        flags.append(f"char_warn:{char_n}>8000")
        status = "warn" if status == "pass" else status

    if len(summary) > 400:
        flags.append("summary_long")
        status = "warn" if status == "pass" else status

    if len(skills) > 25:
        flags.append(f"skills_crowded:{len(skills)}")
        status = "warn" if status == "pass" else status

    if section_n < 2:
        flags.append("sparse_sections")
        status = "warn" if status == "pass" else status

    return {
        "status": status,
        "bullet_count": bullet_n,
        "char_count": char_n,
        "skill_count": len(skills),
        "section_count": section_n,
        "flags": flags,
        "one_page_ok": status != "fail",
    }
