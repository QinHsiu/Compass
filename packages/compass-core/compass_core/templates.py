"""Resume templates: JSON Resume interchange + multi-theme HTML/MD render."""

from __future__ import annotations

import json
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets" / "templates"


def catalog() -> dict:
    return json.loads((ASSETS / "catalog.json").read_text(encoding="utf-8"))


def list_themes() -> list[dict]:
    return list(catalog().get("themes") or [])


def recommend_theme(keywords: list[str] | None = None, role: str = "") -> str:
    """Heuristic theme pick from JD keywords / role."""
    blob = " ".join(keywords or []).lower() + " " + role.lower()
    if any(x in blob for x in ("intern", "校园", "校招", "实习")):
        return "internship_lite"
    if any(x in blob for x in ("research", "phd", "论文", "科研")):
        return "research_cv"
    if any(x in blob for x in ("design", "product", "ui")):
        return "two_column"
    if any(x in blob for x in ("ml", "platform", "kubernetes", "python", "java", "backend")):
        return "tech_single"
    if any(x in blob for x in ("metric", "impact", "slo")):
        return "impact_first"
    return "ats_plain"


def to_json_resume(data: dict) -> dict:
    """Convert Compass resume.json → JSON Resume schema subset."""
    basics = data.get("basics") or {}
    links = basics.get("links") or []
    profiles = []
    for ln in links:
        if isinstance(ln, str):
            profiles.append({"url": ln})
        elif isinstance(ln, dict):
            profiles.append(ln)
    work = []
    for it in data.get("experience") or []:
        work.append(
            {
                "name": it.get("company") or it.get("org") or "",
                "position": it.get("title") or "",
                "summary": "",
                "highlights": it.get("bullets") or [],
                "url": it.get("evidence_id") or "",
            }
        )
    projects = []
    for it in data.get("projects") or []:
        projects.append(
            {
                "name": it.get("name") or it.get("title") or "",
                "description": "",
                "highlights": it.get("bullets") or [],
                "keywords": it.get("skills") or [],
                "url": it.get("evidence_id") or "",
            }
        )
    skills = [{"name": s, "keywords": []} for s in (data.get("skills") or [])]
    education = []
    for it in data.get("education") or []:
        if isinstance(it, str):
            education.append({"institution": it})
        else:
            education.append(it)
    return {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": {
            "name": basics.get("name") or "",
            "summary": basics.get("summary") or "",
            "email": basics.get("email") or "",
            "profiles": profiles,
        },
        "work": work,
        "projects": projects,
        "skills": skills,
        "education": education,
        "meta": {
            "compass": True,
            "theme": data.get("theme") or "ats_plain",
        },
    }


def from_json_resume(jr: dict) -> dict:
    basics = jr.get("basics") or {}
    return {
        "version": 1,
        "basics": {
            "name": basics.get("name") or "",
            "summary": basics.get("summary") or "",
            "email": basics.get("email") or "",
            "links": [p.get("url") for p in (basics.get("profiles") or []) if p.get("url")],
        },
        "skills": [s.get("name") for s in (jr.get("skills") or []) if s.get("name")],
        "experience": [
            {
                "title": w.get("position") or "",
                "company": w.get("name") or "",
                "bullets": w.get("highlights") or [],
                "evidence_id": w.get("url") if str(w.get("url") or "").startswith("ev_") else "",
            }
            for w in (jr.get("work") or [])
        ],
        "projects": [
            {
                "name": p.get("name") or "",
                "bullets": p.get("highlights") or [],
                "skills": p.get("keywords") or [],
                "evidence_id": p.get("url") if str(p.get("url") or "").startswith("ev_") else "",
            }
            for p in (jr.get("projects") or [])
        ],
        "education": jr.get("education") or [],
        "theme": (jr.get("meta") or {}).get("theme") or "ats_plain",
    }


_THEME_CSS = {
    "ats_plain": "body{font-family:Arial,Helvetica,sans-serif;color:#111;max-width:800px;margin:2rem auto;line-height:1.35} h1{font-size:1.6rem;margin:0} h2{border-bottom:1px solid #333;font-size:1.05rem;margin-top:1.2rem} ul{margin:.3rem 0 .6rem 1.2rem}",
    "tech_single": "body{font-family:Segoe UI,Helvetica,sans-serif;color:#1a2332;max-width:820px;margin:2rem auto} h1{color:#0f766e} h2{color:#0f766e;border-bottom:2px solid #0f766e33}",
    "classic_serif": "body{font-family:Georgia,'Times New Roman',serif;color:#222;max-width:780px;margin:2rem auto} h1{font-weight:normal;letter-spacing:.02em} h2{font-variant:small-caps;border-bottom:1px solid #999}",
    "compact_dense": "body{font-family:Arial,sans-serif;font-size:12.5px;max-width:780px;margin:1rem auto;line-height:1.25} h1{font-size:1.3rem;margin:0} h2{font-size:.95rem;margin:.7rem 0 .2rem;border-bottom:1px solid #444} li{margin:0}",
    "timeline": "body{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto} .item{border-left:3px solid #555;padding-left:1rem;margin:.8rem 0}",
    "two_column": "body{font-family:system-ui,sans-serif;margin:0} .wrap{display:grid;grid-template-columns:28% 72%;min-height:100vh} .side{background:#1a2332;color:#f6f3ee;padding:1.5rem} .main{padding:1.5rem 2rem}",
    "modern_teal": "body{font-family:'Segoe UI',sans-serif;color:#102a2a;max-width:840px;margin:2rem auto;background:linear-gradient(180deg,#f3faf8,#fff)} h1,h2{color:#0f766e}",
    "minimal_mono": "body{font-family:Consolas,'Courier New',monospace;color:#111;max-width:800px;margin:2rem auto;font-size:13px} h2{text-transform:uppercase;font-size:12px;letter-spacing:.08em;border-bottom:1px dashed #999}",
    "sidebar_skills": "body{font-family:system-ui,sans-serif;margin:0} .wrap{display:grid;grid-template-columns:32% 68%} .side{background:#eef2f5;padding:1.25rem} .main{padding:1.25rem 1.5rem}",
    "impact_first": "body{font-family:system-ui,sans-serif;max-width:820px;margin:2rem auto} .metric{font-weight:700;color:#0f766e} h2{border-bottom:2px solid #0f766e}",
    "research_cv": "body{font-family:Georgia,serif;max-width:800px;margin:2rem auto} h1{text-align:center} h2{border-bottom:1px solid #000}",
    "internship_lite": "body{font-family:Arial,sans-serif;max-width:760px;margin:1.5rem auto;font-size:14px} h1{font-size:1.4rem} h2{font-size:1rem;color:#333;border-bottom:1px solid #ccc}",
}


def _esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _sections_html(data: dict, theme: str) -> str:
    basics = data.get("basics") or {}
    name = _esc(basics.get("name") or "Resume")
    summary = _esc(basics.get("summary") or "")
    skills = ", ".join(_esc(s) for s in (data.get("skills") or []))
    blocks = []
    if summary:
        blocks.append(f"<h2>Summary</h2><p>{summary}</p>")
    if skills:
        blocks.append(f"<h2>Skills</h2><p>{skills}</p>")
    for label, key in (("Experience", "experience"), ("Projects", "projects"), ("Education", "education")):
        items = data.get(key) or []
        if not items:
            continue
        parts = [f"<h2>{label}</h2>"]
        for it in items:
            if isinstance(it, str):
                parts.append(f"<p>{_esc(it)}</p>")
                continue
            title = _esc(it.get("title") or it.get("name") or "")
            org = _esc(it.get("org") or it.get("company") or "")
            eid = _esc(it.get("evidence_id") or "")
            head = f"{title}" + (f" — {org}" if org else "")
            cls = "item" if theme == "timeline" else "block"
            parts.append(f'<div class="{cls}"><h3>{head}</h3>')
            if eid:
                parts.append(f'<p class="eid"><code>{eid}</code></p>')
            bullets = it.get("bullets") or []
            if bullets:
                parts.append("<ul>")
                for b in bullets:
                    bhtml = _esc(b)
                    if theme == "impact_first":
                        parts.append(f'<li><span class="metric">{bhtml}</span></li>')
                    else:
                        parts.append(f"<li>{bhtml}</li>")
                parts.append("</ul>")
            parts.append("</div>")
        blocks.append("\n".join(parts))
    return "\n".join(blocks), name


def render_html(data: dict, theme: str | None = None) -> str:
    theme = theme or data.get("theme") or "ats_plain"
    ids = {t["id"] for t in list_themes()}
    if theme not in ids:
        theme = "ats_plain"
    body, name = _sections_html(data, theme)
    css = _THEME_CSS.get(theme, _THEME_CSS["ats_plain"])
    footer = (
        f'<footer style="margin-top:2rem;font-size:11px;color:#666">'
        f"Layout: {theme} · Schema: JSON Resume · Compass evidence-gated · "
        f"See assets/templates/SOURCES.md"
        f"</footer>"
    )
    if theme in ("two_column", "sidebar_skills"):
        skills = ", ".join(_esc(s) for s in (data.get("skills") or []))
        return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>{name}</title>
<style>{css}</style></head><body><div class="wrap">
<aside class="side"><h1>{name}</h1><h2>Skills</h2><p>{skills}</p></aside>
<main class="main">{body}</main></div>{footer}</body></html>"""
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>{name}</title>
<style>{css}</style></head><body><h1>{name}</h1>{body}{footer}</body></html>"""


def render_markdown_themed(data: dict, theme: str | None = None) -> str:
    theme = theme or data.get("theme") or "ats_plain"
    from .resume import resume_to_markdown

    md = resume_to_markdown(data)
    return md + f"\n\n---\n_Theme: `{theme}` · JSON Resume compatible · see templates/SOURCES.md_\n"


def render_all(data: dict, out_dir: Path, theme: str | None = None) -> dict:
    theme = theme or data.get("theme") or recommend_theme(data.get("skills") or [])
    data = {**data, "theme": theme}
    out_dir.mkdir(parents=True, exist_ok=True)
    html = render_html(data, theme)
    md = render_markdown_themed(data, theme)
    jr = to_json_resume(data)
    (out_dir / "resume.html").write_text(html, encoding="utf-8")
    (out_dir / "resume.md").write_text(md, encoding="utf-8")
    (out_dir / "resume.jsonresume.json").write_text(
        json.dumps(jr, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "theme.txt").write_text(theme + "\n", encoding="utf-8")
    return {"theme": theme, "html": str(out_dir / "resume.html"), "jsonresume": str(out_dir / "resume.jsonresume.json")}
