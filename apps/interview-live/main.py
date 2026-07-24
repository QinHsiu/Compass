"""Compass Web — FastAPI + WebSocket workbench (replaces Gradio as primary UI)."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

_PKG = Path(__file__).resolve().parents[2] / "packages" / "compass-core"
if _PKG.is_dir() and str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from compass_core.diagnose import diagnose_and_save  # noqa: E402
from compass_core.evidence import build_index, load_evidence  # noqa: E402
from compass_core.export_report import export_report  # noqa: E402
from compass_core.gate import check_claim  # noqa: E402
from compass_core.ingest import extract_text, split_resume_to_evidence_drafts  # noqa: E402
from compass_core.interview import (  # noqa: E402
    interview_and_save,
    next_followup,
    opening_question,
)
from compass_core.life import (  # noqa: E402
    answer_life,
    explore_life,
    export_life_html,
    load_life_report,
    refine_plan,
)
from compass_core.llm import describe_config  # noqa: E402
from compass_core.match import match_and_save  # noqa: E402
from compass_core.paths import content_root, ensure_dirs  # noqa: E402
from compass_core.questions import load_bank, search_questions  # noqa: E402
from compass_core.resume import apply_and_save  # noqa: E402
from compass_core.timeline import build_timeline, render_timeline_html  # noqa: E402
from compass_core.track import upsert  # noqa: E402

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
REPO = HERE.parents[1]

app = FastAPI(title="Compass Web", version="0.7.0")
if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")


def _root() -> Path:
    root = content_root(os.environ.get("COMPASS_ROOT"))
    ensure_dirs(root)
    (root / "questions").mkdir(parents=True, exist_ok=True)
    return root


def _fixture_jd(root: Path) -> Path | None:
    for p in (
        root / "fixtures" / "demo" / "jd.txt",
        REPO / "content" / "fixtures" / "demo" / "jd.txt",
    ):
        if p.is_file():
            return p
    return None


def _ensure_demo_evidence(root: Path) -> None:
    ev = root / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    if any(ev.glob("ev_*.md")):
        return
    for base in (
        root / "fixtures" / "demo" / "evidence",
        REPO / "content" / "fixtures" / "demo" / "evidence",
    ):
        if not base.is_dir():
            continue
        for src in base.glob("*.md"):
            dst = ev / src.name
            if not dst.is_file():
                shutil.copy2(src, dst)
        build_index(root)
        return


def _write_evidence_drafts(root: Path, drafts: list[dict]) -> int:
    ev_dir = root / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for d in drafts:
        eid = d["id"]
        md = (
            f"# {d['title']}\n\n"
            f"- **id**: `{eid}`\n"
            f"- **tags**: {', '.join(d.get('tags') or [])}\n"
            f"- **skills**: {', '.join(d.get('skills') or [])}\n"
            f"- **proof**: uploaded resume extract\n\n"
            f"## Context\n\nUploaded segment.\n\n"
            f"## Actions\n\n{d.get('body', '')[:1500]}\n\n"
            f"## Metrics\n\n(pending user confirmation)\n"
        )
        (ev_dir / f"{eid}.md").write_text(md, encoding="utf-8")
        n += 1
    build_index(root)
    return n


def _run_pipeline(root: Path, jd_text: str, theme: str | None = None, lang: str = "zh") -> dict:
    m = match_and_save(root, jd_text.strip())
    r = apply_and_save(root, m.job_id, theme=theme or None)
    i = interview_and_save(root, m.job_id, lang=lang or "zh")
    d = diagnose_and_save(root, m.job_id)
    upsert(root, m.job_id, "wishlist", note="web pipeline")
    exp = export_report(root, m.job_id, want_pdf=False)
    resume_md = (root / "resumes" / m.job_id / "resume.md").read_text(encoding="utf-8")
    session = (root / "interviews" / m.job_id / "session.md").read_text(encoding="utf-8")
    report = (root / "diagnoses" / m.job_id / "report.md").read_text(encoding="utf-8")
    return {
        "job_id": m.job_id,
        "score": m.score,
        "theme": r.get("theme"),
        "bank_n": i.get("bank_n"),
        "diagnose": d,
        "resume_md": resume_md,
        "session_md": session,
        "report_md": report,
        "graph_path": f"/timeline?job_id={m.job_id}",
        "export_html": exp.get("html"),
        "resume_html": str(root / "resumes" / m.job_id / "resume.html"),
    }


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"ok": True, "root": str(_root()), "ui": "websocket-web", "version": "0.7.0"}


@app.get("/api/life/{session_id}/report")
def api_life_report(session_id: str):
    try:
        return load_life_report(_root(), session_id)
    except FileNotFoundError:
        return JSONResponse({"ok": False, "error": "session not found"}, status_code=404)


@app.get("/api/meta")
def meta():
    return {
        "llm": describe_config(),
        "demo": os.environ.get("COMPASS_DEMO", "").strip() in ("1", "true", "yes"),
        "bank_count": len(load_bank(_root())),
    }


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


@app.get("/api/job/{job_id}")
def job_detail(job_id: str):
    root = _root()
    out = {"job_id": job_id}
    for name, rel in (
        ("match", f"jobs/{job_id}/match.json"),
        ("resume_md", f"resumes/{job_id}/resume.md"),
        ("session_md", f"interviews/{job_id}/session.md"),
        ("report_md", f"diagnoses/{job_id}/report.md"),
    ):
        p = root / rel
        if not p.is_file():
            continue
        if name == "match":
            out["match"] = json.loads(p.read_text(encoding="utf-8"))
        else:
            out[name] = p.read_text(encoding="utf-8")
    out["graph_path"] = f"/timeline?job_id={job_id}"
    return out


@app.get("/api/timeline")
def timeline(job_id: str | None = None):
    return build_timeline(_root(), job_id=job_id)


@app.get("/timeline")
def timeline_page(job_id: str | None = None):
    data = build_timeline(_root(), job_id=job_id)
    return HTMLResponse(render_timeline_html(data))


@app.post("/api/asr")
async def api_asr(file: UploadFile = File(...), language: str = Form("zh")):
    """Optional high-accuracy ASR via faster-whisper (extras [asr])."""
    from compass_core.voice import transcribe_audio

    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        out = transcribe_audio(path, language=language or "zh")
        ok = bool(out.get("text"))
        return {
            "ok": ok,
            "text": out.get("text") or "",
            "warning": out.get("warning") or "",
        }
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@app.post("/api/ingest")
async def api_ingest(file: UploadFile = File(...)):
    root = _root()
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        result = extract_text(path)
        text = result.get("text") or ""
        warnings = result.get("warnings") or []
        if not text.strip():
            return JSONResponse({"ok": False, "warnings": warnings, "count": 0}, status_code=400)
        drafts = split_resume_to_evidence_drafts(text)
        n = _write_evidence_drafts(root, drafts)
        return {"ok": True, "count": n, "preview": text[:3000], "warnings": warnings}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@app.post("/api/life/extract")
async def api_life_extract(file: UploadFile = File(...)):
    """Extract text for /life without writing evidence drafts."""
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        result = extract_text(path)
        text = result.get("text") or ""
        warnings = result.get("warnings") or []
        if not text.strip():
            return JSONResponse({"ok": False, "warnings": warnings}, status_code=400)
        return {"ok": True, "text": text, "preview": text[:8000], "warnings": warnings}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@app.websocket("/ws/app")
async def ws_app(websocket: WebSocket):
    """Primary workbench channel: pipeline / demo / ingest / bank / export."""
    await websocket.accept()
    root = _root()
    await websocket.send_json(
        {
            "type": "ready",
            "demo": os.environ.get("COMPASS_DEMO", "").strip() in ("1", "true", "yes"),
            "llm": describe_config(),
            "bank_count": len(load_bank(root)),
        }
    )
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
            if mtype == "ingest_text":
                text = (msg.get("text") or "").strip()
                if not text:
                    await websocket.send_json({"type": "error", "message": "empty text"})
                    continue
                await websocket.send_json({"type": "progress", "step": "ingest"})
                drafts = split_resume_to_evidence_drafts(text)
                n = _write_evidence_drafts(root, drafts)
                await websocket.send_json(
                    {"type": "ingest_done", "count": n, "preview": text[:3000]}
                )
                continue
            if mtype in ("pipeline", "demo"):
                theme = msg.get("theme") or "tech_single"
                lang = (msg.get("lang") or "zh").lower()[:2]
                if mtype == "demo":
                    _ensure_demo_evidence(root)
                    jd_path = _fixture_jd(root)
                    if not jd_path:
                        await websocket.send_json(
                            {"type": "error", "step": "no_fixture", "message": "demo fixture missing"}
                        )
                        continue
                    jd = jd_path.read_text(encoding="utf-8")
                    await websocket.send_json({"type": "progress", "step": "demo"})
                else:
                    jd = (msg.get("jd") or "").strip()
                    if not jd:
                        await websocket.send_json(
                            {"type": "error", "step": "need_jd", "message": "empty job description"}
                        )
                        continue
                try:
                    await websocket.send_json({"type": "progress", "step": "match"})
                    result = _run_pipeline(root, jd, theme, lang=lang)
                    await websocket.send_json({"type": "pipeline_done", **result})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})
                continue
            if mtype == "search_bank":
                query = msg.get("query") or "llm agent rag"
                limit = int(msg.get("limit") or 12)
                semantic = bool(msg.get("semantic"))
                lang = (msg.get("lang") or "zh").lower()[:2]
                if semantic:
                    from compass_core.rag import semantic_search

                    hits = semantic_search(root, query, k=limit, lang=lang)
                    backend = "semantic"
                else:
                    hits = search_questions(
                        query,
                        keywords=["llm", "agent", "rag"],
                        limit=limit,
                        extra_root=root,
                        lang=lang,
                    )
                    backend = "token"
                await websocket.send_json(
                    {
                        "type": "bank_hits",
                        "backend": backend,
                        "total": len(load_bank(root)),
                        "hits": hits,
                        "lang": lang,
                    }
                )
                continue
            if mtype == "export":
                jid = (msg.get("job_id") or "").strip()
                if not jid:
                    jobs = sorted((root / "jobs").glob("*/match.json"))
                    if not jobs:
                        await websocket.send_json({"type": "error", "message": "无岗位可导出"})
                        continue
                    jid = jobs[-1].parent.name
                out = export_report(root, jid, want_pdf=True)
                await websocket.send_json({"type": "export_done", **out})
                continue
            if mtype == "life_explore":
                text = (msg.get("text") or "").strip()
                sid = (msg.get("session_id") or None) or None
                if not text:
                    await websocket.send_json(
                        {"type": "error", "step": "life", "message": "empty life narrative"}
                    )
                    continue
                try:
                    await websocket.send_json({"type": "progress", "step": "life"})
                    out = explore_life(root, text=text, session_id=sid)
                    await websocket.send_json({"type": "life_done", **out})
                except Exception as e:
                    await websocket.send_json({"type": "error", "step": "life", "message": str(e)})
                continue
            if mtype == "life_answer":
                sid = (msg.get("session_id") or "").strip()
                answers = msg.get("answers") or {}
                if not sid:
                    await websocket.send_json(
                        {"type": "error", "step": "life", "message": "missing session_id"}
                    )
                    continue
                try:
                    await websocket.send_json({"type": "progress", "step": "life_score"})
                    out = answer_life(root, sid, answers)
                    await websocket.send_json({"type": "life_done", **out})
                except Exception as e:
                    await websocket.send_json({"type": "error", "step": "life", "message": str(e)})
                continue
            if mtype == "life_refine":
                sid = (msg.get("session_id") or "").strip()
                message = (msg.get("message") or "").strip()
                if not sid or not message:
                    await websocket.send_json(
                        {"type": "error", "step": "life", "message": "need session_id and message"}
                    )
                    continue
                try:
                    out = refine_plan(root, sid, message)
                    await websocket.send_json({"type": "life_refine_done", **out})
                except Exception as e:
                    await websocket.send_json({"type": "error", "step": "life", "message": str(e)})
                continue
            if mtype == "life_export":
                sid = (msg.get("session_id") or "").strip()
                if not sid:
                    await websocket.send_json(
                        {"type": "error", "step": "life", "message": "missing session_id"}
                    )
                    continue
                try:
                    out = export_life_html(root, sid)
                    await websocket.send_json({"type": "life_export_done", **out})
                except Exception as e:
                    await websocket.send_json({"type": "error", "step": "life", "message": str(e)})
                continue
            await websocket.send_json({"type": "error", "message": f"unknown type {mtype}"})
    except WebSocketDisconnect:
        return


@app.websocket("/ws/interview/{job_id}")
async def ws_interview(websocket: WebSocket, job_id: str):
    await websocket.accept()
    root = _root()
    jid = job_id
    if jid in ("", "latest", "_"):
        jobs = sorted((root / "jobs").glob("*/match.json"))
        if not jobs:
            await websocket.send_json(
                {"type": "error", "message": "no jobs; 请先在「求职流水线」跑一遍"}
            )
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
                                "gate": {
                                    "ok": gate.ok,
                                    "status": gate.status,
                                    "reason": gate.reason,
                                },
                                "evidence_ids": gate.evidence_ids,
                                "turn": turn,
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                try:
                    from compass_core.scorecard import record_answer

                    record_answer(
                        root,
                        jid,
                        turn=turn,
                        question=q,
                        answer=answer,
                        gate_ok=gate.ok,
                        gate_status=gate.status,
                        gate_reason=gate.reason,
                    )
                except Exception:
                    pass
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

    port = int(os.environ.get("COMPASS_LIVE_PORT") or os.environ.get("COMPASS_WEB_PORT") or "8766")
    host = os.environ.get("COMPASS_HOST", "127.0.0.1")
    print(f"[Compass Web] http://{host}:{port}/  (WebSocket workbench)", flush=True)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
