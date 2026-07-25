"""Pick, Don't Edit — select verified bullets into a targeted resume (no rewrite)."""

from __future__ import annotations

import json
from pathlib import Path

from .evidence import load_evidence
from .resume import empty_resume, load_resume, resume_to_markdown


def list_pickable_bullets(root: Path, job_id: str | None = None) -> list[dict]:
    """Flatten evidence + existing resume bullets as pick candidates."""
    root = Path(root)
    items: list[dict] = []
    for e in load_evidence(root):
        d = e.to_dict() if hasattr(e, "to_dict") else dict(e)
        eid = d.get("id") or d.get("evidence_id")
        title = d.get("title") or ""
        chunks = []
        for key in ("metrics", "actions", "context", "proof", "body"):
            val = d.get(key)
            if val:
                chunks.append(str(val))
        for i, b in enumerate(d.get("bullets") or d.get("claims") or chunks):
            items.append(
                {
                    "pick_id": f"ev:{eid}:{i}",
                    "source": "evidence",
                    "evidence_id": eid,
                    "text": b if isinstance(b, str) else str(b),
                    "title": title,
                }
            )
    # resume base
    base_path = root / "resumes" / "base.json"
    if job_id:
        jp = root / "resumes" / job_id / "resume.json"
        if jp.is_file():
            base_path = jp
    if base_path.is_file():
        data = load_resume(base_path)
        for section in ("experience", "projects"):
            for j, it in enumerate(data.get(section) or []):
                for k, b in enumerate(it.get("bullets") or []):
                    items.append(
                        {
                            "pick_id": f"rs:{section}:{j}:{k}",
                            "source": "resume",
                            "evidence_id": it.get("evidence_id"),
                            "text": b,
                            "title": it.get("title") or it.get("name") or section,
                        }
                    )
    # JD keyword hint scores
    kws: list[str] = []
    if job_id:
        jd = root / "jobs" / job_id / "jd.json"
        if jd.is_file():
            kws = [str(x).lower() for x in (json.loads(jd.read_text(encoding="utf-8")).get("keywords") or [])]
    for it in items:
        blob = (it.get("text") or "").lower()
        it["jd_hits"] = sum(1 for k in kws if k and k in blob)
    items.sort(key=lambda x: (-int(x.get("jd_hits") or 0), x.get("pick_id") or ""))
    return items


def apply_picks(
    root: Path,
    pick_ids: list[str],
    *,
    job_id: str,
    name: str = "",
) -> dict:
    """Build resume from selected pick_ids only — no LLM rewrite."""
    root = Path(root)
    catalog = {p["pick_id"]: p for p in list_pickable_bullets(root, job_id)}
    chosen = []
    missing = []
    for pid in pick_ids:
        if pid in catalog:
            chosen.append(catalog[pid])
        else:
            missing.append(pid)
    resume = empty_resume(name=name or "Candidate")
    # group by evidence into experience entries
    by_ev: dict[str, list] = {}
    for c in chosen:
        key = c.get("evidence_id") or c.get("title") or "picked"
        by_ev.setdefault(str(key), []).append(c)
    for key, group in by_ev.items():
        resume["experience"].append(
            {
                "title": group[0].get("title") or key,
                "org": "",
                "evidence_id": group[0].get("evidence_id"),
                "bullets": [g["text"] for g in group],
                "pick_ids": [g["pick_id"] for g in group],
            }
        )
    resume["skills"] = sorted(
        {
            w
            for c in chosen
            for w in (c.get("text") or "").replace(",", " ").split()
            if len(w) > 2 and w.isalpha()
        }
    )[:24]
    resume["meta"] = {"mode": "pick_dont_edit", "job_id": job_id, "picks": pick_ids}
    out_dir = root / "resumes" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "resume.json").write_text(
        json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = resume_to_markdown(resume)
    (out_dir / "resume.md").write_text(md, encoding="utf-8")
    picks_path = out_dir / "picks.json"
    picks_path.write_text(
        json.dumps({"pick_ids": pick_ids, "chosen": chosen, "missing": missing}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "job_id": job_id,
        "picked": len(chosen),
        "missing": missing,
        "path": str(out_dir / "resume.json"),
        "md": str(out_dir / "resume.md"),
        "mode": "pick_dont_edit",
    }
