"""Compass Interview Live — FastAPI WebSocket realtime interview."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

_PKG = Path(__file__).resolve().parents[2] / "packages" / "compass-core"
if _PKG.is_dir() and str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from compass_core.evidence import load_evidence  # noqa: E402
from compass_core.gate import check_claim  # noqa: E402
from compass_core.interview import (  # noqa: E402
    interview_and_save,
    next_followup,
    opening_question,
)
from compass_core.paths import content_root, ensure_dirs  # noqa: E402
from compass_core.timeline import build_timeline, render_timeline_html  # noqa: E402

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"

app = FastAPI(title="Compass Interview Live", version="0.4.0")
if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def _root() -> Path:
    root = content_root(os.environ.get("COMPASS_ROOT"))
    ensure_dirs(root)
    return root


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "root": str(_root())}


@app.get("/api/jobs")
def list_jobs():
    root = _root()
    jobs = []
    for p in sorted((root / "jobs").glob("*/match.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        jobs.append(
            {
                "job_id": m.get("job_id") or p.parent.name,
                "title": m.get("title"),
                "company": m.get("company"),
                "score": m.get("score"),
            }
        )
    return {"jobs": jobs}


@app.get("/api/timeline")
def timeline(job_id: str | None = None):
    data = build_timeline(_root(), job_id=job_id)
    return data


@app.get("/timeline")
def timeline_page(job_id: str | None = None):
    data = build_timeline(_root(), job_id=job_id)
    return HTMLResponse(render_timeline_html(data))


@app.websocket("/ws/interview/{job_id}")
async def ws_interview(websocket: WebSocket, job_id: str):
    await websocket.accept()
    root = _root()
    jid = job_id
    if jid in ("", "latest", "_"):
        jobs = sorted((root / "jobs").glob("*/match.json"))
        if not jobs:
            await websocket.send_json({"type": "error", "message": "no jobs; run Studio pipeline first"})
            await websocket.close()
            return
        jid = jobs[-1].parent.name

    pack_path = root / "interviews" / jid / "pack.json"
    if not pack_path.is_file():
        interview_and_save(root, jid)
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    evidence = load_evidence(root)
    turn = 0
    q = opening_question(pack)
    await websocket.send_json(
        {"type": "question", "job_id": jid, "turn": turn, "question": q, "mode": "opening"}
    )

    log_path = root / "interviews" / jid / "oral_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "invalid json"})
                continue
            mtype = msg.get("type")
            if mtype == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            if mtype == "answer":
                answer = (msg.get("text") or "").strip()
                gate = check_claim(answer, evidence)
                with log_path.open("a", encoding="utf-8") as f:
                    f.write(
                        json.dumps(
                            {
                                "q": q,
                                "answer": answer,
                                "gate": gate.status,
                                "evidence_ids": gate.evidence_ids,
                                "turn": turn,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                await websocket.send_json(
                    {
                        "type": "gate",
                        "ok": gate.ok,
                        "status": gate.status,
                        "reason": gate.reason,
                        "evidence_ids": gate.evidence_ids,
                    }
                )
                fu = next_followup(pack, answer, gate.ok, gate.reason, turn=turn)
                turn += 1
                q = fu["question"]
                await websocket.send_json(
                    {
                        "type": "question",
                        "job_id": jid,
                        "turn": turn,
                        "question": q,
                        "mode": fu.get("mode"),
                        "meta": fu.get("meta") or {},
                    }
                )
                continue
            if mtype == "coding_submit":
                code = msg.get("code") or ""
                # Local heuristic review only — no remote exec
                hints = []
                if "def " not in code and "function" not in code:
                    hints.append("未检测到函数定义")
                if "return" not in code:
                    hints.append("未检测到 return")
                await websocket.send_json(
                    {
                        "type": "coding_feedback",
                        "ok": len(hints) == 0,
                        "hints": hints or ["结构看起来完整（本地静态检查，未执行代码）"],
                    }
                )
                continue
            await websocket.send_json({"type": "error", "message": f"unknown type {mtype}"})
    except WebSocketDisconnect:
        return


def main():
    import uvicorn

    port = int(os.environ.get("COMPASS_LIVE_PORT", "8766"))
    host = os.environ.get("COMPASS_HOST", "127.0.0.1")
    print(f"[Interview Live] http://{host}:{port}/", flush=True)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
