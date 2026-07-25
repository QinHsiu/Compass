"""Resume key metrics (jsonresume.org Round 10)."""

from __future__ import annotations

import json
import re
from datetime import date


def calculate_key_metrics(resume: dict) -> dict:
    """Derive years_experience, companies, projects, skills, highest_degree."""
    years: list[int] = []
    companies: set[str] = set()
    for it in resume.get("experience") or []:
        name = str(it.get("org") or it.get("company") or "").strip()
        if name:
            companies.add(name)
        for field in ("start", "end", "dates", "period"):
            for m in re.finditer(r"(?:19|20)\d{2}", str(it.get(field) or "")):
                years.append(int(m.group(0)))
        for b in it.get("bullets") or []:
            for m in re.finditer(r"(?:19|20)\d{2}", b):
                years.append(int(m.group(0)))

    projects = resume.get("projects") or []
    skills = resume.get("skills") or []
    edu = resume.get("education") or []
    degree_rank = {
        "phd": 4,
        "博士": 4,
        "master": 3,
        "硕士": 3,
        "bachelor": 2,
        "本科": 2,
        "associate": 1,
        "专科": 1,
    }
    highest = ""
    best = 0
    for e in edu:
        blob = json.dumps(e, ensure_ascii=False).lower()
        for k, rank in degree_rank.items():
            if k in blob and rank > best:
                best = rank
                highest = k

    years_exp = 0
    if years:
        uniq = sorted(set(years))
        if len(uniq) >= 2:
            years_exp = max(0, uniq[-1] - uniq[0])
        else:
            years_exp = max(0, date.today().year - uniq[0])

    return {
        "years_experience": years_exp,
        "companies": len(companies),
        "company_names": sorted(companies)[:12],
        "projects": len(projects),
        "skills": len(skills),
        "highest_degree": highest or "unknown",
    }
