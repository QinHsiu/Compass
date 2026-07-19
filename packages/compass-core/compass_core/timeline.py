"""Evidence chain timeline / graph visualization."""

from __future__ import annotations

import html
import json
import math
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

    seen = set()
    uniq_edges = []
    for e in edges:
        key = (e["from"], e["to"], e["rel"])
        if key in seen:
            continue
        seen.add(key)
        uniq_edges.append(e)

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


def _layout_columns(nodes: list[dict]) -> dict[str, tuple[float, float]]:
    """Layered layout: evidence | resume | interview."""
    cols = {"evidence": 0, "resume": 1, "interview": 2}
    buckets: dict[str, list[dict]] = {"evidence": [], "resume": [], "interview": []}
    for n in nodes:
        buckets.setdefault(n.get("type") or "evidence", []).append(n)

    width, height = 920.0, 520.0
    margin_x, margin_y = 80.0, 48.0
    col_w = (width - 2 * margin_x) / 2.0
    pos: dict[str, tuple[float, float]] = {}
    for typ, items in buckets.items():
        if not items:
            continue
        cx = margin_x + cols.get(typ, 0) * col_w
        n = len(items)
        for i, node in enumerate(items):
            y = margin_y + (height - 2 * margin_y) * ((i + 0.5) / max(n, 1))
            # slight fan for long labels
            x = cx + (8 if i % 2 else -8)
            pos[node["id"]] = (x, y)
    return pos


def _short_label(text: str, n: int = 22) -> str:
    t = (text or "").replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def render_timeline_html(data: dict) -> str:
    """Self-contained evidence graph HTML (SVG + click highlight, no CDN required)."""
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    s = data.get("summary") or {}
    pos = _layout_columns(nodes)
    # ensure every node has a position
    for i, n in enumerate(nodes):
        if n["id"] not in pos:
            angle = 2 * math.pi * i / max(len(nodes), 1)
            pos[n["id"]] = (460 + 180 * math.cos(angle), 260 + 160 * math.sin(angle))

    colors = {"evidence": "#2b6de5", "resume": "#0f766e", "interview": "#b45309"}
    svg_edges = []
    for e in edges:
        a, b = pos.get(e["from"]), pos.get(e["to"])
        if not a or not b:
            continue
        svg_edges.append(
            f'<line class="edge" data-from="{html.escape(e["from"])}" data-to="{html.escape(e["to"])}" '
            f'data-rel="{html.escape(e.get("rel") or "")}" '
            f'x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" />'
        )

    svg_nodes = []
    for n in nodes:
        x, y = pos[n["id"]]
        fill = colors.get(n.get("type") or "", "#64748b")
        label = _short_label(str(n.get("label") or n["id"]))
        nid = html.escape(n["id"])
        ntype = html.escape(n.get("type") or "")
        svg_nodes.append(
            f'<g class="node" data-id="{nid}" data-type="{ntype}" transform="translate({x:.1f},{y:.1f})">'
            f'<circle r="16" fill="{fill}" stroke="#fff" stroke-width="2"/>'
            f'<text y="32" text-anchor="middle">{html.escape(label)}</text>'
            f'<title>{nid} · {html.escape(str(n.get("label") or ""))}</title>'
            f"</g>"
        )

    list_items = []
    for n in nodes:
        if n.get("type") != "evidence":
            continue
        linked = [e for e in edges if e["from"] == n["id"]]
        targets = ", ".join(f"{e['rel']}→{e['to']}" for e in linked[:6]) or "（尚未关联简历/面试）"
        list_items.append(
            f"<li data-id=\"{html.escape(n['id'])}\"><strong>{html.escape(n['id'])}</strong> "
            f"{html.escape(str(n.get('label') or ''))}<br/>"
            f"<span class='muted'>{html.escape(targets)}</span></li>"
        )
    body = "\n".join(list_items) or "<li>暂无证据</li>"
    payload = html.escape(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False))

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>Compass Evidence Graph</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
:root {{ --blue:#2b6de5; --ink:#1c2434; --muted:#6b7280; --bg:#f5f8fc; --line:#e6ebf2; }}
* {{ box-sizing: border-box; }}
body {{ font-family:"Noto Sans SC",system-ui,sans-serif; background:var(--bg); color:var(--ink); margin:0; padding:16px; }}
h1 {{ color:var(--blue); font-size:1.4rem; margin:0 0 8px; }}
.muted {{ color:var(--muted); font-size:.9rem; }}
.stats span {{ display:inline-block; margin:0 8px 8px 0; background:#eef4ff; padding:4px 10px; border-radius:999px; font-size:.85rem; }}
.wrap {{ display:grid; grid-template-columns:1.4fr 1fr; gap:14px; }}
@media (max-width:720px) {{ .wrap {{ grid-template-columns:1fr; }} }}
.panel {{ background:#fff; border:1px solid var(--line); border-radius:12px; padding:12px; }}
svg {{ width:100%; height:auto; max-height:560px; background:linear-gradient(180deg,#fafcff,#fff); border-radius:10px; }}
.edge {{ stroke:#c9d8f5; stroke-width:2; }}
.edge.lit {{ stroke:var(--blue); stroke-width:3; }}
.node {{ cursor:pointer; }}
.node text {{ font-size:11px; fill:var(--ink); }}
.node.dim {{ opacity:.25; }}
.node.lit circle {{ stroke:var(--blue); stroke-width:3; }}
ul {{ margin:0; padding-left:20px; max-height:480px; overflow:auto; }}
li {{ margin:8px 0; }}
li.active {{ background:#eef4ff; border-radius:8px; padding:6px; }}
.legend span {{ margin-right:12px; font-size:.85rem; }}
.dot {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:4px; }}
</style></head><body>
<h1>证据链图谱</h1>
<p class="stats">
<span>证据 {s.get('evidence',0)}</span>
<span>简历条目 {s.get('resume',0)}</span>
<span>面试 {s.get('interview',0)}</span>
<span>关联 {s.get('links',0)}</span>
</p>
<p class="legend muted">
<span><i class="dot" style="background:#2b6de5"></i>证据</span>
<span><i class="dot" style="background:#0f766e"></i>简历</span>
<span><i class="dot" style="background:#b45309"></i>面试</span>
· 点击节点高亮关联边
</p>
<div class="wrap">
  <div class="panel">
    <svg id="graph" viewBox="0 0 920 520" role="img" aria-label="evidence graph">
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6 Z" fill="#c9d8f5"/>
        </marker>
      </defs>
      {"".join(svg_edges)}
      {"".join(svg_nodes)}
    </svg>
  </div>
  <div class="panel">
    <h2 style="margin:0 0 8px;font-size:1rem">证据清单</h2>
    <ul id="elist">{body}</ul>
  </div>
</div>
<script type="application/json" id="graph-data">{payload}</script>
<script>
(function() {{
  var nodes = document.querySelectorAll('.node');
  var edges = document.querySelectorAll('.edge');
  var items = document.querySelectorAll('#elist li');
  function clear() {{
    nodes.forEach(function(n) {{ n.classList.remove('lit','dim'); }});
    edges.forEach(function(e) {{ e.classList.remove('lit'); }});
    items.forEach(function(li) {{ li.classList.remove('active'); }});
  }}
  function highlight(id) {{
    clear();
    var related = {{}};
    related[id] = true;
    edges.forEach(function(e) {{
      var f = e.getAttribute('data-from'), t = e.getAttribute('data-to');
      if (f === id || t === id) {{ e.classList.add('lit'); related[f]=true; related[t]=true; }}
    }});
    nodes.forEach(function(n) {{
      var nid = n.getAttribute('data-id');
      if (related[nid]) n.classList.add('lit'); else n.classList.add('dim');
    }});
    items.forEach(function(li) {{
      if (li.getAttribute('data-id') === id) li.classList.add('active');
    }});
  }}
  nodes.forEach(function(n) {{
    n.addEventListener('click', function() {{ highlight(n.getAttribute('data-id')); }});
  }});
  items.forEach(function(li) {{
    li.addEventListener('click', function() {{ highlight(li.getAttribute('data-id')); }});
  }});
  document.getElementById('graph').addEventListener('dblclick', clear);
}})();
</script>
</body></html>
"""
