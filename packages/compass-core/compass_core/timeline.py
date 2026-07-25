"""Evidence chain timeline / interactive graph visualization."""

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
            x = cx + (8 if i % 2 else -8)
            pos[node["id"]] = (x, y)
    return pos


def _short_label(text: str, n: int = 22) -> str:
    t = (text or "").replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


def render_timeline_html(data: dict) -> str:
    """Interactive self-contained graph: filter, search, detail pane, click edges."""
    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    s = data.get("summary") or {}
    pos = _layout_columns(nodes)
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
        skills = html.escape(",".join(n.get("skills") or []))
        svg_nodes.append(
            f'<g class="node" data-id="{nid}" data-type="{ntype}" data-label="{html.escape(str(n.get("label") or ""))}" '
            f'data-skills="{skills}" transform="translate({x:.1f},{y:.1f})">'
            f'<circle r="16" fill="{fill}" stroke="#fff" stroke-width="2"/>'
            f'<text y="32" text-anchor="middle">{html.escape(label)}</text>'
            f"</g>"
        )

    payload = html.escape(json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False))

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>Compass Evidence Graph</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
:root {{ --blue:#2b6de5; --ink:#1c2434; --muted:#6b7280; --bg:#f5f8fc; --line:#e6ebf2; }}
* {{ box-sizing: border-box; }}
body {{ font-family:"Noto Sans SC",system-ui,sans-serif; background:var(--bg); color:var(--ink); margin:0; padding:16px; }}
h1 {{ color:var(--blue); font-size:1.35rem; margin:0 0 8px; }}
.muted {{ color:var(--muted); font-size:.9rem; }}
.stats span {{ display:inline-block; margin:0 8px 8px 0; background:#eef4ff; padding:4px 10px; border-radius:999px; font-size:.85rem; }}
.toolbar {{ display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin:10px 0 14px; }}
.toolbar label {{ font-size:.88rem; color:var(--muted); display:inline-flex; align-items:center; gap:4px; }}
.toolbar input[type=search] {{ min-width:200px; flex:1; border:1px solid var(--line); border-radius:10px; padding:8px 12px; font:inherit; }}
.wrap {{ display:grid; grid-template-columns:1.35fr 1fr; gap:14px; }}
@media (max-width:820px) {{ .wrap {{ grid-template-columns:1fr; }} }}
.panel {{ background:#fff; border:1px solid var(--line); border-radius:12px; padding:12px; }}
svg {{ width:100%; height:auto; max-height:560px; background:linear-gradient(180deg,#fafcff,#fff); border-radius:10px; }}
.edge {{ stroke:#c9d8f5; stroke-width:2; cursor:pointer; }}
.edge.lit {{ stroke:var(--blue); stroke-width:3; }}
.edge.hid, .node.hid {{ display:none; }}
.node {{ cursor:pointer; }}
.node text {{ font-size:11px; fill:var(--ink); }}
.node.dim {{ opacity:.18; }}
.node.lit circle {{ stroke:var(--blue); stroke-width:3; }}
#detail {{ font-size:.92rem; line-height:1.5; min-height:120px; }}
#detail code {{ background:#eef4ff; padding:1px 6px; border-radius:4px; }}
#detail .rel {{ margin:4px 0; padding:6px 8px; background:#f8faff; border-radius:8px; cursor:pointer; }}
#detail .rel:hover {{ background:#eef4ff; }}
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
<div class="toolbar">
  <label><input type="checkbox" id="fEv" checked/> 证据</label>
  <label><input type="checkbox" id="fRe" checked/> 简历</label>
  <label><input type="checkbox" id="fIv" checked/> 面试</label>
  <label><input type="checkbox" id="fConn"/> 仅显示有边的节点</label>
  <input type="search" id="q" placeholder="搜索 evidence_id / 标题…"/>
</div>
<p class="legend muted">
<span><i class="dot" style="background:#2b6de5"></i>证据</span>
<span><i class="dot" style="background:#0f766e"></i>简历</span>
<span><i class="dot" style="background:#b45309"></i>面试</span>
· 点击节点/边查看详情 · 双击画布清除 · 筛选会记住到 localStorage
</p>
<div class="wrap">
  <div class="panel">
    <svg id="graph" viewBox="0 0 920 520" role="img" aria-label="evidence graph">
      {"".join(svg_edges)}
      {"".join(svg_nodes)}
    </svg>
  </div>
  <div class="panel">
    <h2 style="margin:0 0 8px;font-size:1rem">节点详情</h2>
    <div id="detail" class="muted">点击左侧节点或边，查看 skills 与关联。</div>
  </div>
</div>
<script type="application/json" id="graph-data">{payload}</script>
<script>
(function() {{
  var DATA = JSON.parse(document.getElementById('graph-data').textContent);
  var nodes = document.querySelectorAll('.node');
  var edges = document.querySelectorAll('.edge');
  var detail = document.getElementById('detail');
  var fEv = document.getElementById('fEv');
  var fRe = document.getElementById('fRe');
  var fIv = document.getElementById('fIv');
  var fConn = document.getElementById('fConn');
  var q = document.getElementById('q');
  var LS_KEY = 'compass_timeline_filters_v1';

  function nodeMap() {{
    var m = {{}};
    (DATA.nodes || []).forEach(function(n) {{ m[n.id] = n; }});
    return m;
  }}
  var NMAP = nodeMap();
  var CONNECTED = {{}};
  (DATA.edges || []).forEach(function(e) {{ CONNECTED[e.from] = true; CONNECTED[e.to] = true; }});

  function loadPrefs() {{
    try {{
      var p = JSON.parse(localStorage.getItem(LS_KEY) || '{{}}');
      if (typeof p.ev === 'boolean') fEv.checked = p.ev;
      if (typeof p.re === 'boolean') fRe.checked = p.re;
      if (typeof p.iv === 'boolean') fIv.checked = p.iv;
      if (typeof p.conn === 'boolean') fConn.checked = p.conn;
      if (typeof p.q === 'string') q.value = p.q;
    }} catch (e) {{}}
  }}
  function savePrefs() {{
    try {{
      localStorage.setItem(LS_KEY, JSON.stringify({{
        ev: fEv.checked, re: fRe.checked, iv: fIv.checked, conn: fConn.checked, q: q.value || ''
      }}));
    }} catch (e) {{}}
  }}

  function typeOn(t) {{
    if (t === 'evidence') return fEv.checked;
    if (t === 'resume') return fRe.checked;
    if (t === 'interview') return fIv.checked;
    return true;
  }}
  function matchQ(n) {{
    var s = (q.value || '').trim().toLowerCase();
    if (!s) return true;
    return (n.id || '').toLowerCase().indexOf(s) >= 0 ||
      String(n.label || '').toLowerCase().indexOf(s) >= 0;
  }}
  function applyFilter() {{
    var vis = {{}};
    nodes.forEach(function(el) {{
      var id = el.getAttribute('data-id');
      var t = el.getAttribute('data-type');
      var n = NMAP[id] || {{id:id, type:t, label:el.getAttribute('data-label')}};
      var ok = typeOn(t) && matchQ(n);
      if (fConn.checked && !CONNECTED[id]) ok = false;
      el.classList.toggle('hid', !ok);
      if (ok) vis[id] = true;
    }});
    edges.forEach(function(e) {{
      var f = e.getAttribute('data-from'), t = e.getAttribute('data-to');
      e.classList.toggle('hid', !(vis[f] && vis[t]));
    }});
    savePrefs();
  }}
  function clearHL() {{
    nodes.forEach(function(n) {{ n.classList.remove('lit','dim'); }});
    edges.forEach(function(e) {{ e.classList.remove('lit'); }});
  }}
  function showDetail(id) {{
    var n = NMAP[id];
    if (!n) {{ detail.textContent = '未找到节点'; return; }}
    var rels = (DATA.edges || []).filter(function(e) {{ return e.from === id || e.to === id; }});
    var skills = (n.skills || []).join(', ') || '—';
    var html = '<p><strong>' + esc(n.id) + '</strong><br/><span class="muted">' +
      esc(n.type) + ' · ' + esc(n.label || '') + '</span></p>';
    html += '<p>skills: ' + esc(skills) + '</p><p><strong>关联</strong></p>';
    if (!rels.length) html += '<p class="muted">（无边）</p>';
    rels.forEach(function(e) {{
      var other = e.from === id ? e.to : e.from;
      html += '<div class="rel" data-goto="' + esc(other) + '">' +
        esc(e.rel) + ' → <code>' + esc(other) + '</code></div>';
    }});
    detail.innerHTML = html;
    detail.querySelectorAll('.rel').forEach(function(el) {{
      el.addEventListener('click', function() {{ highlight(el.getAttribute('data-goto')); }});
    }});
  }}
  function esc(s) {{
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }}
  function highlight(id) {{
    clearHL();
    var related = {{}}; related[id] = true;
    edges.forEach(function(e) {{
      if (e.classList.contains('hid')) return;
      var f = e.getAttribute('data-from'), t = e.getAttribute('data-to');
      if (f === id || t === id) {{ e.classList.add('lit'); related[f]=true; related[t]=true; }}
    }});
    nodes.forEach(function(n) {{
      if (n.classList.contains('hid')) return;
      var nid = n.getAttribute('data-id');
      if (related[nid]) n.classList.add('lit'); else n.classList.add('dim');
    }});
    showDetail(id);
  }}
  function highlightEdge(from, to) {{
    clearHL();
    edges.forEach(function(e) {{
      if (e.getAttribute('data-from') === from && e.getAttribute('data-to') === to) e.classList.add('lit');
    }});
    nodes.forEach(function(n) {{
      var nid = n.getAttribute('data-id');
      if (nid === from || nid === to) n.classList.add('lit'); else if (!n.classList.contains('hid')) n.classList.add('dim');
    }});
    detail.innerHTML = '<p>边：<code>' + esc(from) + '</code> → <code>' + esc(to) + '</code></p>' +
      '<div class="rel" data-goto="' + esc(from) + '">查看起点</div>' +
      '<div class="rel" data-goto="' + esc(to) + '">查看终点</div>';
    detail.querySelectorAll('.rel').forEach(function(el) {{
      el.addEventListener('click', function() {{ highlight(el.getAttribute('data-goto')); }});
    }});
  }}
  nodes.forEach(function(n) {{
    n.addEventListener('click', function() {{ highlight(n.getAttribute('data-id')); }});
  }});
  edges.forEach(function(e) {{
    e.addEventListener('click', function(ev) {{
      ev.stopPropagation();
      highlightEdge(e.getAttribute('data-from'), e.getAttribute('data-to'));
    }});
  }});
  document.getElementById('graph').addEventListener('dblclick', function() {{
    clearHL(); detail.textContent = '点击左侧节点或边，查看 skills 与关联。';
  }});
  loadPrefs();
  [fEv, fRe, fIv, fConn].forEach(function(el) {{ el.addEventListener('change', applyFilter); }});
  q.addEventListener('input', applyFilter);
  applyFilter();
}})();
</script>
</body></html>
"""
