"""Compass CLI."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .collectors import collect_career_html, collect_paste, collect_rss
from .diagnose import diagnose_and_save
from .evidence import build_index
from .gate import check_claims
from .intake import save_profile
from .interview import interview_and_save
from .match import match_and_save
from .paths import content_root, ensure_dirs
from .resume import apply_and_save
from .track import upsert


def _root(args) -> Path:
    root = content_root(getattr(args, "root", None))
    ensure_dirs(root)
    return root


def cmd_intake(args) -> int:
    root = _root(args)
    data = {}
    if args.file:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
    if args.name:
        data["name"] = args.name
    if args.roles:
        data["target_roles"] = [r.strip() for r in args.roles.split(",") if r.strip()]
    path = save_profile(root, data)
    print(json.dumps({"path": str(path), "profile": data or "template"}, ensure_ascii=False, indent=2))
    return 0


def cmd_evidence_index(args) -> int:
    idx = build_index(_root(args))
    print(json.dumps({"count": idx["count"], "path": "evidence/index.json"}, ensure_ascii=False))
    return 0


def cmd_gate(args) -> int:
    root = _root(args)
    claims = []
    if args.claim:
        claims.append(args.claim)
    if args.claims_file:
        claims.extend(
            ln.strip()
            for ln in Path(args.claims_file).read_text(encoding="utf-8").splitlines()
            if ln.strip()
        )
    results = check_claims(claims, root)
    out = [
        {
            "ok": r.ok,
            "status": r.status,
            "evidence_ids": r.evidence_ids,
            "reason": r.reason,
            "claim": r.claim[:200],
        }
        for r in results
    ]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if all(r.ok for r in results) else 2


def cmd_discover(args) -> int:
    root = _root(args)
    if args.source == "paste":
        if args.text_file:
            text = Path(args.text_file).read_text(encoding="utf-8")
        elif args.text:
            text = args.text
        else:
            text = sys.stdin.read()
        m = collect_paste(root, text, job_id=args.job_id)
        print(json.dumps(m.to_dict(), ensure_ascii=False, indent=2))
        return 0
    if args.source == "rss":
        if not args.url:
            print("rss requires --url", file=sys.stderr)
            return 1
        rows = collect_rss(root, args.url, limit=args.limit)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if args.source == "career":
        if not args.url:
            print("career requires --url", file=sys.stderr)
            return 1
        rows = collect_career_html(root, args.url, limit=args.limit)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print(f"unknown source {args.source}", file=sys.stderr)
    return 1


def cmd_resume(args) -> int:
    out = apply_and_save(_root(args), args.job_id, theme=getattr(args, "theme", None))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_templates(args) -> int:
    from .templates import list_themes, recommend_theme

    themes = list_themes()
    rec = recommend_theme(args.keywords.split(",") if args.keywords else [], role=args.role or "")
    print(json.dumps({"themes": themes, "recommended": rec, "sources": "assets/templates/SOURCES.md"}, ensure_ascii=False, indent=2))
    return 0


def cmd_questions(args) -> int:
    from .questions import infer_topics, load_bank, search_questions

    root = _root(args)
    kws = [k.strip() for k in (args.keywords or "").split(",") if k.strip()]
    topics = infer_topics(kws) if kws else None
    query = args.query or " ".join(kws)
    if getattr(args, "semantic", False):
        from .rag import semantic_search

        hits = semantic_search(root, query, k=args.limit)
        backend = "semantic"
    else:
        hits = search_questions(
            query,
            keywords=kws,
            topics=topics,
            limit=args.limit,
            extra_root=root,
        )
        backend = "token"
    print(
        json.dumps(
            {
                "backend": backend,
                "count_bank": len(load_bank(root)),
                "hits": hits,
                "sources": "assets/questions/SOURCES.md",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_rag_index(args) -> int:
    from .rag import index_questions

    print(json.dumps(index_questions(_root(args)), ensure_ascii=False, indent=2))
    return 0


def cmd_llm_info(args) -> int:
    from .llm import describe_config, load_config

    cfg = load_config(provider=args.provider, model=args.model, base_url=args.base_url)
    print(json.dumps(describe_config(cfg), ensure_ascii=False, indent=2))
    return 0


def cmd_live(args) -> int:
    import os
    import runpy

    repo = Path(__file__).resolve().parents[3]
    live = repo / "apps" / "interview-live" / "main.py"
    if not live.is_file():
        print(f"interview-live not found at {live}", file=sys.stderr)
        return 1
    if getattr(args, "root", None):
        os.environ["COMPASS_ROOT"] = str(Path(args.root).resolve())
    if getattr(args, "port", None):
        os.environ["COMPASS_LIVE_PORT"] = str(args.port)
    runpy.run_path(str(live), run_name="__main__")
    return 0


def cmd_timeline(args) -> int:
    from .timeline import build_timeline, render_timeline_html

    root = _root(args)
    data = build_timeline(root, job_id=args.job_id)
    if args.html:
        out = Path(args.html)
        out.write_text(render_timeline_html(data), encoding="utf-8")
        print(json.dumps({"path": str(out), "summary": data["summary"]}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def cmd_interview(args) -> int:
    out = interview_and_save(_root(args), args.job_id)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_diagnose(args) -> int:
    root = _root(args)
    if args.fixture:
        _load_fixture(root, Path(args.fixture))
    job_id = args.job_id
    if not job_id:
        jobs = sorted((root / "jobs").glob("*/match.json"))
        if not jobs:
            print("no jobs; pass --job-id or --fixture", file=sys.stderr)
            return 1
        job_id = jobs[-1].parent.name
    out = diagnose_and_save(root, job_id)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def _load_fixture(root: Path, fixture_dir: Path) -> None:
    fixture_dir = fixture_dir.resolve()
    for name in ("profile", "evidence", "jobs"):
        src = fixture_dir / name
        if not src.exists():
            continue
        dest = root / name
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
        else:
            for p in src.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(src)
                    target = dest / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, target)
    build_index(root)


def cmd_track(args) -> int:
    item = upsert(_root(args), args.job_id, args.status, note=args.note or "")
    print(json.dumps(item, ensure_ascii=False, indent=2))
    return 0


def cmd_studio(args) -> int:
    import os
    import runpy

    repo = Path(__file__).resolve().parents[3]
    studio = repo / "apps" / "studio" / "app.py"
    if not studio.is_file():
        print(f"studio app not found at {studio}", file=sys.stderr)
        return 1
    if getattr(args, "root", None):
        os.environ["COMPASS_ROOT"] = str(Path(args.root).resolve())
    if getattr(args, "port", None):
        os.environ["COMPASS_PORT"] = str(args.port)
    runpy.run_path(str(studio), run_name="__main__")
    return 0


def cmd_crawl_llm(args) -> int:
    from .crawl_llm import refresh_llm_agent_bank

    stats = refresh_llm_agent_bank()
    root = _root(args)
    src = Path(stats["path"])
    dst = root / "questions" / "llm_agent.jsonl"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_file():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({**stats, "content_copy": str(dst)}, ensure_ascii=False, indent=2))
    return 0


def cmd_desk(args) -> int:
    from .desk import serve

    serve(root=_root(args), port=args.port, open_browser=not args.no_browser)
    return 0


def cmd_pipeline(args) -> int:
    root = _root(args)
    text = Path(args.text_file).read_text(encoding="utf-8")
    m = match_and_save(root, text)
    r = apply_and_save(root, m.job_id)
    i = interview_and_save(root, m.job_id)
    d = diagnose_and_save(root, m.job_id)
    print(
        json.dumps(
            {
                "steps": 4,
                "job_id": m.job_id,
                "score": m.score,
                "resume_ops": r["ops"],
                "interview": i["path"],
                "diagnose": d["path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--root", default=None, help="content root (or COMPASS_ROOT)")

    p = argparse.ArgumentParser(prog="compass", description="Compass evidence-driven job CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("evidence-index", parents=[parent], help="rebuild evidence/index.json")
    e.set_defaults(func=cmd_evidence_index)

    intake = sub.add_parser("intake", parents=[parent], help="write profile.json")
    intake.add_argument("--file", default=None, help="JSON profile fragment")
    intake.add_argument("--name", default=None)
    intake.add_argument("--roles", default=None, help="comma-separated target roles")
    intake.set_defaults(func=cmd_intake)

    g = sub.add_parser("gate", parents=[parent], help="check claims against evidence")
    g.add_argument("--claim", default=None)
    g.add_argument("--claims-file", default=None)
    g.set_defaults(func=cmd_gate)

    d = sub.add_parser("discover", parents=[parent], help="import jobs")
    d.add_argument("--source", choices=("paste", "rss", "career"), required=True)
    d.add_argument("--text", default=None)
    d.add_argument("--text-file", default=None)
    d.add_argument("--url", default=None)
    d.add_argument("--job-id", default=None)
    d.add_argument("--limit", type=int, default=10)
    d.set_defaults(func=cmd_discover)

    r = sub.add_parser("resume-patch", parents=[parent], help="build evidence-gated resume patch")
    r.add_argument("--job-id", required=True)
    r.add_argument("--theme", default=None, help="template id (see templates command)")
    r.set_defaults(func=cmd_resume)

    tpl = sub.add_parser("templates", parents=[parent], help="list resume themes + attribution")
    tpl.add_argument("--keywords", default="")
    tpl.add_argument("--role", default="")
    tpl.set_defaults(func=cmd_templates)

    qb = sub.add_parser("questions", parents=[parent], help="search interview question bank")
    qb.add_argument("--query", default="")
    qb.add_argument("--keywords", default="")
    qb.add_argument("--limit", type=int, default=12)
    qb.add_argument("--semantic", action="store_true", help="use Chroma RAG when available")
    qb.set_defaults(func=cmd_questions)

    rag = sub.add_parser("rag-index", parents=[parent], help="build local question vector index")
    rag.set_defaults(func=cmd_rag_index)

    llm = sub.add_parser("llm-info", parents=[parent], help="show LLM provider config")
    llm.add_argument("--provider", default=None)
    llm.add_argument("--model", default=None)
    llm.add_argument("--base-url", default=None)
    llm.set_defaults(func=cmd_llm_info)

    live = sub.add_parser("live", parents=[parent], help="launch Interview Live (WebSocket)")
    live.add_argument("--port", type=int, default=8766)
    live.set_defaults(func=cmd_live)

    tl = sub.add_parser("timeline", parents=[parent], help="evidence chain timeline JSON/HTML")
    tl.add_argument("--job-id", default=None)
    tl.add_argument("--html", default=None, help="write HTML file path")
    tl.set_defaults(func=cmd_timeline)

    i = sub.add_parser("interview-pack", parents=[parent], help="build interview pack + session")
    i.add_argument("--job-id", required=True)
    i.set_defaults(func=cmd_interview)
    di = sub.add_parser("diagnose", parents=[parent], help="gap compass report + bridge plan")
    di.add_argument("--job-id", default=None)
    di.add_argument("--fixture", default=None)
    di.set_defaults(func=cmd_diagnose)

    t = sub.add_parser("track", parents=[parent], help="update application board")
    t.add_argument("--job-id", required=True)
    t.add_argument("--status", required=True)
    t.add_argument("--note", default="")
    t.set_defaults(func=cmd_track)

    desk = sub.add_parser("desk", parents=[parent], help="start local desk UI")
    desk.add_argument("--port", type=int, default=8765)
    desk.add_argument("--no-browser", action="store_true")
    desk.set_defaults(func=cmd_desk)

    studio = sub.add_parser("studio", parents=[parent], help="launch Gradio Compass Studio")
    studio.add_argument("--port", type=int, default=7860)
    studio.set_defaults(func=cmd_studio)

    crawl = sub.add_parser("crawl-llm", parents=[parent], help="refresh LLM/Agent question bank")
    crawl.set_defaults(func=cmd_crawl_llm)

    pipe = sub.add_parser(
        "pipeline", parents=[parent], help="4-step demo: discover→resume→interview→diagnose"
    )
    pipe.add_argument("--text-file", required=True)
    pipe.set_defaults(func=cmd_pipeline)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
