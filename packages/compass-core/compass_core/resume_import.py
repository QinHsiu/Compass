"""Heuristic PDF/text → JSON Resume subset (compas.txt P0 / open-resume)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .ingest import extract_text

_SECTION_HINTS = {
    "experience": ("experience", "work", "employment", "工作经历", "经历", "任职"),
    "projects": ("project", "projects", "项目经历", "项目"),
    "education": ("education", "学历", "教育"),
    "skills": ("skills", "技能", "技术栈", "tech stack"),
    "summary": ("summary", "profile", "简介", "自我评价", "概述"),
}


def _detect_section(line: str) -> str | None:
    low = line.strip().lower().rstrip(":")
    if len(low) > 40:
        return None
    for key, hints in _SECTION_HINTS.items():
        if any(h == low or low.startswith(h) for h in hints):
            return key
    return None


def parse_resume_text(text: str) -> dict:
    """Split plain resume text into a JSON Resume-ish dict."""
    lines = [ln.strip() for ln in (text or "").splitlines()]
    lines = [ln for ln in lines if ln]
    basics: dict = {"name": "", "summary": "", "email": "", "label": ""}
    experience: list[dict] = []
    projects: list[dict] = []
    education: list[dict] = []
    skills: list[str] = []

    # Contact / name heuristics from first lines
    for ln in lines[:8]:
        if re.search(r"[\w.+-]+@[\w.-]+\.\w+", ln):
            basics["email"] = re.search(r"[\w.+-]+@[\w.-]+\.\w+", ln).group(0)
        if re.search(r"1\d{10}|\+\d[\d\s-]{8,}", ln):
            basics["phone"] = re.search(r"1\d{10}|\+\d[\w\s-]{8,}", ln).group(0)
        if not basics["name"] and 2 <= len(ln) <= 20 and "：" not in ln and "@" not in ln:
            if not _detect_section(ln):
                basics["name"] = ln

    section = "summary"
    buf: list[str] = []
    current_item: dict | None = None

    def flush_buf():
        nonlocal buf, current_item, section
        if not buf:
            return
        if section == "skills":
            blob = " ".join(buf)
            for part in re.split(r"[,，、;/|]", blob):
                p = part.strip()
                if p and p not in skills:
                    skills.append(p)
        elif section == "summary":
            basics["summary"] = (basics.get("summary") or "") + " ".join(buf)
        elif section in ("experience", "projects", "education"):
            if current_item is None:
                current_item = {"name": buf[0][:80], "bullets": []}
            for b in buf:
                if b.startswith(("-", "•", "*", "·")) or re.match(r"^\d+[\.\)]", b):
                    current_item.setdefault("bullets", []).append(
                        re.sub(r"^[-•*·\d\.\)\s]+", "", b).strip()
                    )
                elif not current_item.get("org") and section == "experience":
                    current_item["org"] = b[:80]
                    current_item["name"] = current_item.get("name") or b[:80]
                elif "dates" not in current_item and re.search(r"20\d{2}", b):
                    current_item["dates"] = b[:40]
                else:
                    current_item.setdefault("bullets", []).append(b)
            target = {
                "experience": experience,
                "projects": projects,
                "education": education,
            }[section]
            if current_item not in target:
                target.append(current_item)
        buf = []

    for ln in lines:
        sec = _detect_section(ln)
        if sec:
            flush_buf()
            if current_item and section in ("experience", "projects", "education"):
                pass
            current_item = None
            section = sec
            continue
        # new experience block: blank-line-ish titles with year
        if section in ("experience", "projects") and re.search(r"20\d{2}", ln) and len(ln) < 60:
            flush_buf()
            current_item = {"name": ln[:80], "dates": ln[:40], "bullets": []}
            if section == "experience":
                experience.append(current_item)
            else:
                projects.append(current_item)
            continue
        buf.append(ln)
    flush_buf()

    if not basics.get("summary") and lines:
        basics["summary"] = " ".join(lines[:3])[:400]

    return {
        "basics": basics,
        "work": [
            {
                "name": it.get("org") or it.get("name") or "",
                "position": it.get("name") or "",
                "startDate": "",
                "endDate": "",
                "summary": "",
                "highlights": it.get("bullets") or [],
            }
            for it in experience
        ],
        "experience": experience,  # Compass-native
        "projects": [
            {"name": it.get("name") or "", "bullets": it.get("bullets") or [], "dates": it.get("dates")}
            for it in projects
        ],
        "education": education,
        "skills": skills[:40],
        "meta": {"imported": True, "needs_evidence_gate": True},
    }


def import_resume_file(
    root: Path,
    file_path: str | Path,
    *,
    job_id: str | None = None,
) -> dict:
    """Extract + parse + save resume.json under content/resumes/."""
    root = Path(root)
    path = Path(file_path)
    extracted = extract_text(path)
    text = extracted.get("text") or ""
    resume = parse_resume_text(text)
    resume["meta"] = {
        **(resume.get("meta") or {}),
        "source_file": str(path.name),
        "format": extracted.get("format"),
        "warnings": extracted.get("warnings") or [],
    }
    if job_id:
        out_dir = root / "resumes" / job_id
    else:
        out_dir = root / "resumes" / "_imported"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "resume.json"
    out_path.write_text(json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(out_path), "resume": resume, "warnings": extracted.get("warnings") or []}
