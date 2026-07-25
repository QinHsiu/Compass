"""Minimal local desk workbench (stdlib http.server)."""

from __future__ import annotations

import json
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .paths import content_root, ensure_dirs
from .track import VALID, load_board, upsert


HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Compass Desk</title>
<style>
:root { --bg:#f6f3ee; --ink:#1a2332; --accent:#0f766e; --muted:#5c6b7a; --line:#d5d0c8; }
* { box-sizing:border-box; }
body { margin:0; font-family:"Segoe UI", "PingFang SC", sans-serif; background:linear-gradient(160deg,#eef6f4,#f6f3ee 40%,#f0ebe3); color:var(--ink); }
header { padding:1.5rem 2rem; border-bottom:1px solid var(--line); }
header h1 { margin:0; font-size:1.6rem; letter-spacing:-0.02em; color:var(--accent); }
header p { margin:0.35rem 0 0; color:var(--muted); font-size:0.95rem; }
main { display:grid; grid-template-columns:1fr 1fr; gap:1rem; padding:1.25rem 2rem 2rem; }
@media (max-width:900px){ main { grid-template-columns:1fr; } }
section { background:rgba(255,255,255,0.72); border:1px solid var(--line); padding:1rem 1.1rem; }
section h2 { margin:0 0 0.75rem; font-size:1.05rem; }
ul { list-style:none; margin:0; padding:0; }
li { padding:0.55rem 0; border-bottom:1px solid var(--line); font-size:0.92rem; }
li:last-child { border-bottom:none; }
.score { color:var(--accent); font-weight:600; }
.muted { color:var(--muted); font-size:0.85rem; }
a { color:var(--accent); }
code { font-size:0.85em; }
</style>
</head>
<body>
<header>
  <h1>Compass Desk</h1>
  <p>Local-first job board — evidence · jobs · diagnoses · track · templates · question bank</p>
</header>
<main>
  <section>
    <h2>Jobs</h2>
    <ul id="jobs"></ul>
  </section>
  <section>
    <h2>Track</h2>
    <ul id="track"></ul>
  </section>
  <section>
    <h2>Diagnoses</h2>
    <ul id="diag"></ul>
  </section>
  <section>
    <h2>Evidence</h2>
    <ul id="ev"></ul>
  </section>
  <section>
    <h2>Templates</h2>
    <p class="muted" id="bankmeta"></p>
    <ul id="tpl"></ul>
  </section>
</main>
<script>
async function load() {
  const d = await (await fetch('/api/overview')).json();
  document.getElementById('jobs').innerHTML = (d.jobs||[]).map(j =>
    `<li><strong>${j.title}</strong> <span class="muted">@ ${j.company}</span><br/>
     <code>${j.job_id}</code> · <span class="score">${j.score}</span></li>`).join('') || '<li class="muted">暂无</li>';
  document.getElementById('track').innerHTML = (d.track||[]).map(t =>
    `<li><strong>${t.status}</strong> · ${t.title||t.job_id}
     ${t.match_band?` · <span class="score">${t.match_band}</span>`:''}
     ${t.suggested_action?` · <code>${t.suggested_action}</code>`:''}<br/>
     <span class="muted">${t.follow_up_due?('due '+t.follow_up_due+' · '):''}${t.note||''}</span></li>`
  ).join('') || '<li class="muted">暂无</li>';
  document.getElementById('diag').innerHTML = (d.diagnoses||[]).map(x =>
    `<li><code>${x}</code></li>`).join('') || '<li class="muted">暂无</li>';
  document.getElementById('ev').innerHTML = (d.evidence||[]).map(e =>
    `<li><code>${e.id}</code> ${e.title}</li>`).join('') || '<li class="muted">暂无</li>';
  document.getElementById('bankmeta').textContent = `Question bank: ${d.question_bank_size||0} items · see SOURCES.md`;
  document.getElementById('tpl').innerHTML = (d.templates||[]).map(t =>
    `<li><code>${t.id}</code> ${t.name} ${t.ats?'· ATS':''}</li>`).join('') || '<li class="muted">暂无</li>';
}
load();
</script>
</body>
</html>
"""


class DeskHandler(SimpleHTTPRequestHandler):
    root: Path

    def log_message(self, fmt: str, *args) -> None:
        pass

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/overview":
            data = _overview(self.root)
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/metrics":
            from .observability import export_prometheus

            body = export_prometheus(self.root).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/track":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            self.send_error(400, "bad json")
            return
        job_id = payload.get("job_id")
        status = payload.get("status")
        if not job_id or status not in VALID:
            self.send_error(400, "job_id and valid status required")
            return
        item = upsert(self.root, job_id, status, note=payload.get("note", ""))
        body = json.dumps(item, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _overview(root: Path) -> dict:
    jobs = []
    jobs_dir = root / "jobs"
    if jobs_dir.is_dir():
        for d in sorted(jobs_dir.iterdir()):
            if not d.is_dir():
                continue
            mpath = d / "match.json"
            jpath = d / "jd.json"
            if not mpath.is_file():
                continue
            m = json.loads(mpath.read_text(encoding="utf-8"))
            jobs.append(
                {
                    "job_id": m.get("job_id", d.name),
                    "title": m.get("title", ""),
                    "company": m.get("company", ""),
                    "score": m.get("score", 0),
                }
            )
    board = load_board(root)
    evidence = []
    idx = root / "evidence" / "index.json"
    if idx.is_file():
        evidence = json.loads(idx.read_text(encoding="utf-8")).get("items") or []
    diagnoses = []
    ddir = root / "diagnoses"
    if ddir.is_dir():
        diagnoses = sorted(p.name for p in ddir.iterdir() if p.is_dir())
    from .practice_stats import practice_rollup

    return {
        "jobs": jobs,
        "track": board.get("items") or [],
        "evidence": evidence,
        "diagnoses": diagnoses,
        "templates": _templates_meta(),
        "question_bank_size": _bank_size(),
        "practice": practice_rollup(root),
    }


def _templates_meta() -> list[dict]:
    try:
        from .templates import list_themes

        return list_themes()
    except Exception:
        return []


def _bank_size() -> int:
    try:
        from .questions import load_bank

        return len(load_bank())
    except Exception:
        return 0


def serve(root: Path | None = None, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    root = content_root(root)
    ensure_dirs(root)
    handler = partial(DeskHandler)
    # bind root onto class
    DeskHandler.root = root
    httpd = ThreadingHTTPServer((host, port), DeskHandler)
    url = f"http://{host}:{port}/"
    print(f"Compass Desk at {url} (root={root})")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    httpd.serve_forever()
