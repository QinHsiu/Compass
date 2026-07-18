"""Evidence chain timeline for visualization."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .evidence import load_evidence


def build_timeline(root: Path, job_id: str | None = None) -> dict:
    """Link evidence → resume bullets → interview cites for a job (or all)."""
    evidence = {e.id: e for e in load_evidence(root)}
    nodes = []
    edges = []

    for eid, ev in evidence.items():
        nodes.append(
            {
                "id": eid,
                "type": "evidence",
                "label": ev.title,
                "skills": ev.skills,
            }
        )

    job_ids = []
    if job_id:
        job_ids = [job_id]
    else:
        jobs_dir = root / "jobs"
        if jobs_dir.is_dir():
            job_ids = sorted(p.name for p in jobs_dir.iterdir() if p.is_dir())

    for jid in job_ids:
        resume_path = root / "resumes" / jid / "resume.json"
        if resume_path.is_file():
            data = json.loads(resume_path.read_text(encoding="utf-8"))
            for key in ("projects", "experience"):
                for it in data.get(key) or []:
                    eid = it.get("evidence_id") or ""
                    rid = f"resume:{jid}:{it.get('name') or it.get('title') or 'item'}"
                    nodes.append(
                        {
                            "id": rid,
                            "type": "resume",
                            "label": it.get("name") or it.get("title") or rid,
                            "job_id": jid,
                        }
                    )
                    if eid and eid in evidence:
                        edges.append({"from": eid, "to": rid, "rel": "supports"})
                    blob = json.dumps(it, ensure_ascii=False)
                    for m in re.findall(r"ev_[a-zA-Z0-9_]+", blob):
                        if m in evidence:
                            edges.append({"from": m, "to": rid, "rel": "cited_in"})

        sess = root / "interviews" / jid / "session.md"
        if sess.is_file():
            text = sess.read_text(encoding="utf-8")
            iid = f"interview:{jid}"
            nodes.append({"id": iid, "type": "interview", "label": f"Interview {jid}", "job_id": jid})
            for m in set(re.findall(r"ev_[a-zA-Z0-9_]+", text)):
                if m in evidence:
                    edges.append({"from": m, "to": iid, "rel": "asked_about"})

        # oral log cites
        oral = root / "interviews" / jid / "oral_log.jsonl"
        if oral.is_file():
            for ln in oral.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                try:
                    row = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                for m in set(re.findall(r"ev_[a-zA-Z0-9_]+", row.get("answer") or "")):
                    if m in evidence:
                        edges.append(
                            {
                                "from": m,
                                "to": f"interview:{jid}",
                                "rel": "answered_with",
                            }
                        )

    # dedupe edges
    seen = set()
    uniq_edges = []
    for e in edges:
        key = (e["from"], e["to"], e["rel"])
        if key in seen:
            continue
        seen.add(key)
        uniq_edges.append(e)

    # dedupe nodes by id
    nmap = {n["id"]: n for n in nodes}
    return {
        "job_ids": job_ids,
        "nodes": list(nmap.values()),
        "edges": uniq_edges,
        "summary": {
            "evidence": sum(1 for n in nmap.values() if n["type"] == "evidence"),
            "resume": sum(1 for n in nmap.values() if n["type"] == "resume"),
            "interview": sum(1 for n in nmap.values() if n["type"] == "interview"),
            "links": len(uniq_edges),
        },
    }


def render_timeline_html(data: dict) -> str:
    """Simple self-contained HTML timeline (no CDN required for structure)."""
    items = []
    for n in data.get("nodes") or []:
        if n["type"] != "evidence":
            continue
        linked = [e for e in data.get("edges") or [] if e["from"] == n["id"]]
        targets = ", ".join(f"{e['rel']}→{e['to']}" for e in linked[:6]) or "（尚未关联简历/面试）"
        items.append(
            f"<li><strong>{n['id']}</strong> {n.get('label','')}<br/>"
            f"<span class='muted'>{targets}</span></li>"
        )
    body = "\n".join(items) or "<li>暂无证据</li>"
    s = data.get("summary") or {}
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>Compass Evidence Timeline</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<link rel="manifest" href="/static/manifest.webmanifest"/>
<style>
body{{font-family:"Noto Sans SC",system-ui,sans-serif;background:#f5f8fc;color:#1c2434;margin:0;padding:24px}}
h1{{color:#2b6de5}} .muted{{color:#6b7280;font-size:.9rem}}
ul{{background:#fff;border:1px solid #e6ebf2;border-radius:12px;padding:16px 16px 16px 32px}}
.stats span{{display:inline-block;margin-right:12px;background:#eef4ff;padding:4px 10px;border-radius:999px;font-size:.85rem}}
</style></head><body>
<h1>证据链时间线</h1>
<p class="stats">
<span>证据 {s.get('evidence',0)}</span>
<span>简历条目 {s.get('resume',0)}</span>
<span>面试 {s.get('interview',0)}</span>
<span>关联 {s.get('links',0)}</span>
</p>
<ul>{body}</ul>
</body></html>
"""
