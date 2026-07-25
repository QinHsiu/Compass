"""Compass CLI."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .collectors import collect_career_html, collect_paste, collect_rss
from .diagnose import diagnose_and_save
from .evidence import build_index, load_evidence
from .gate import check_claims
from .intake import load_profile, save_profile
from .interview import interview_and_save
from .jd import ParsedJD, parse_jd
from .match import match_and_save
from .paths import content_root, ensure_dirs
from .resume import apply_and_save
from .skill_gap import classify_jd, extract_jd_skills, profile_skill_list
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


def cmd_skill_gap(args) -> int:
    """Zero-LLM JD skill-gap preflight (existing / supported_by_evidence / gap)."""
    root = _root(args)
    evidence = load_evidence(root)
    profile = load_profile(root)
    named = profile_skill_list(profile)

    if args.job_id:
        jd_path = root / "jobs" / args.job_id / "jd.json"
        if not jd_path.is_file():
            print(json.dumps({"error": f"missing {jd_path}"}, ensure_ascii=False))
            return 1
        jd_data = json.loads(jd_path.read_text(encoding="utf-8"))
        jd = ParsedJD(**{k: jd_data[k] for k in ParsedJD.__dataclass_fields__ if k in jd_data})
    elif args.jd_file:
        text = Path(args.jd_file).read_text(encoding="utf-8")
        jd = parse_jd(text)
    elif args.text:
        jd = parse_jd(args.text)
    else:
        print(json.dumps({"error": "need --job-id, --jd-file, or --text"}, ensure_ascii=False))
        return 1

    tokens = extract_jd_skills(jd)
    gap = classify_jd(jd, evidence, profile_skills=named)
    out = {
        "job_id": jd.job_id,
        "title": jd.title,
        "tokens": tokens,
        "skill_gap": gap.to_dict(),
        "injectable": gap.injectable,
    }
    # Persist onto match.json when job already matched
    if args.job_id:
        match_path = root / "jobs" / args.job_id / "match.json"
        if match_path.is_file():
            match_data = json.loads(match_path.read_text(encoding="utf-8"))
            match_data["skill_gap"] = gap.to_dict()
            match_path.write_text(
                json.dumps(match_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            out["updated_match"] = str(match_path)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_match_explain(args) -> int:
    """Rebuild requirement matrix + match_explain.md for an existing job."""
    from .match_explain import (
        build_requirement_matrix,
        render_match_explain_md,
        summarize_matrix,
    )

    root = _root(args)
    job_dir = root / "jobs" / args.job_id
    jd_path = job_dir / "jd.json"
    if not jd_path.is_file():
        print(json.dumps({"error": f"missing {jd_path}"}, ensure_ascii=False))
        return 1
    jd_data = json.loads(jd_path.read_text(encoding="utf-8"))
    jd = ParsedJD(**{k: jd_data[k] for k in ParsedJD.__dataclass_fields__ if k in jd_data})
    evidence = load_evidence(root)
    rows = build_requirement_matrix(jd, evidence)
    summary = summarize_matrix(rows, evidence_count=len(evidence))
    match_path = job_dir / "match.json"
    profile_fit = {"status": "pass", "blockers": [], "warnings": []}
    if match_path.is_file():
        match_data = json.loads(match_path.read_text(encoding="utf-8"))
        match_data["requirement_matrix"] = [r.to_dict() for r in rows]
        match_data["match_explain"] = summary
        # refresh profile_fit if possible
        from .intake import load_profile
        from .profile_fit import apply_to_explain, assess_profile_fit

        fit = assess_profile_fit(jd, load_profile(root))
        summary = apply_to_explain(summary, fit)
        match_data["match_explain"] = summary
        match_data["profile_fit"] = fit
        profile_fit = fit
        match_path.write_text(json.dumps(match_data, ensure_ascii=False, indent=2), encoding="utf-8")
    (job_dir / "match_explain.md").write_text(
        render_match_explain_md(jd, rows, summary, profile_fit=profile_fit), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "job_id": args.job_id,
                "match_explain": summary,
                "rows": len(rows),
                "path": str(job_dir / "match_explain.md"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


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
    lang = getattr(args, "lang", None) or "zh"
    if getattr(args, "semantic", False):
        from .rag import semantic_search

        hits = semantic_search(root, query, k=args.limit, lang=lang)
        backend = "semantic"
    else:
        hits = search_questions(
            query,
            keywords=kws,
            topics=topics,
            limit=args.limit,
            extra_root=root,
            lang=lang,
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


def cmd_rag_eval(args) -> int:
    from .rag_eval import evaluate_queries, load_queries

    root = _root(args)
    qpath = Path(args.query_file) if args.query_file else None
    if not qpath or not qpath.is_file():
        # prefer fixtures next to content root / repo fixtures
        for cand in (
            root / "fixtures" / "demo" / "rag_queries.jsonl",
            Path(__file__).resolve().parents[3] / "content" / "fixtures" / "demo" / "rag_queries.jsonl",
        ):
            if cand.is_file():
                qpath = cand
                break
    if not qpath or not qpath.is_file():
        print("query file not found; pass --query-file", file=sys.stderr)
        return 1
    queries = load_queries(qpath)
    out = evaluate_queries(root, queries, k=args.k, semantic=not args.token)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_llm_info(args) -> int:
    from .llm import describe_config, load_config

    cfg = load_config(provider=args.provider, model=args.model, base_url=args.base_url)
    print(json.dumps(describe_config(cfg), ensure_ascii=False, indent=2))
    return 0


def cmd_live(args) -> int:
    """Launch Compass Web (WebSocket workbench) — primary UI."""
    import os
    import runpy

    repo = Path(__file__).resolve().parents[3]
    live = repo / "apps" / "interview-live" / "main.py"
    if not live.is_file():
        print(f"Compass Web not found at {live}", file=sys.stderr)
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


def cmd_export_report(args) -> int:
    from .export_report import export_report

    root = _root(args)
    job_id = args.job_id
    if not job_id:
        jobs = sorted((root / "jobs").glob("*/match.json"))
        if not jobs:
            print("no jobs; pass --job-id", file=sys.stderr)
            return 1
        job_id = jobs[-1].parent.name
    out = export_report(root, job_id, want_pdf=not args.html_only)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_interview(args) -> int:
    out = interview_and_save(_root(args), args.job_id)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_practice_stats(args) -> int:
    from .practice_stats import practice_rollup

    print(json.dumps(practice_rollup(_root(args)), ensure_ascii=False, indent=2))
    return 0


def cmd_resume_metrics(args) -> int:
    from .resume_lint import lint_resume_density
    from .resume_metrics import calculate_key_metrics

    root = _root(args)
    if not args.resume and not args.job_id:
        print(json.dumps({"error": "need --job-id or --resume"}, ensure_ascii=False))
        return 1
    path = Path(args.resume) if args.resume else root / "resumes" / args.job_id / "resume.json"
    if not path.is_file():
        print(json.dumps({"error": f"missing {path}"}, ensure_ascii=False))
        return 1
    resume = json.loads(path.read_text(encoding="utf-8"))
    out = {
        "path": str(path),
        "metrics": calculate_key_metrics(resume),
        "density": lint_resume_density(resume),
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_scorecard(args) -> int:
    from .scorecard import import_oral_log, load_scorecard, record_answer, sync_session_md

    root = _root(args)
    action = args.scorecard_action
    job_id = args.job_id
    if action == "show":
        print(json.dumps(load_scorecard(root, job_id), ensure_ascii=False, indent=2))
        return 0
    if action == "sync":
        path = sync_session_md(root, job_id)
        print(json.dumps({"synced": str(path) if path else None}, ensure_ascii=False))
        return 0 if path else 1
    if action == "import-oral":
        data = import_oral_log(root, job_id)
        print(json.dumps({"answers": len(data.get("answers") or []), "aggregate": data.get("aggregate")}, ensure_ascii=False, indent=2))
        return 0
    if action == "record":
        answer = args.answer or ""
        if args.answer_file:
            answer = Path(args.answer_file).read_text(encoding="utf-8")
        scores = None
        if args.scores:
            scores = json.loads(args.scores)
        reqs = [r.strip() for r in (args.requirement_ids or "").split(",") if r.strip()]
        data = record_answer(
            root,
            job_id,
            turn=args.turn,
            question=args.question or "",
            answer=answer,
            scores=scores,
            requirement_ids=reqs,
            notes=args.note or "",
        )
        print(json.dumps({"aggregate": data.get("aggregate"), "answers": len(data.get("answers") or [])}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown scorecard action {action}"}, ensure_ascii=False))
    return 2


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
    from .track import list_due, seed_from_match, upsert

    root = _root(args)
    if getattr(args, "list_due", False):
        items = list_due(root)
        print(json.dumps({"due": items, "count": len(items)}, ensure_ascii=False, indent=2))
        return 0
    if getattr(args, "seed_from_match", False):
        if not args.job_id:
            print(json.dumps({"error": "--job-id required with --seed-from-match"}, ensure_ascii=False))
            return 1
        item = seed_from_match(root, args.job_id)
        print(json.dumps(item, ensure_ascii=False, indent=2))
        return 0
    if not args.job_id or not args.status:
        print(json.dumps({"error": "need --job-id and --status (or --list-due / --seed-from-match)"}, ensure_ascii=False))
        return 1
    item = upsert(
        root,
        args.job_id,
        args.status,
        note=args.note or "",
        follow_up_due=getattr(args, "follow_up_due", None),
    )
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


def cmd_life(args) -> int:
    from .life import answer_life, explore_life, export_life_html, load_life_report, refine_plan

    root = _root(args)
    action = args.life_action
    if action == "explore":
        text = None
        if args.text:
            text = args.text
        elif args.text_file:
            text = Path(args.text_file).read_text(encoding="utf-8")
        out = explore_life(root, text=text, file_path=args.file, session_id=args.session)
        # trim questions in CLI noise unless assessment needed
        if out.get("ready") and "questions" in out:
            out = {k: v for k, v in out.items() if k != "questions"}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if action == "answer":
        answers = json.loads(Path(args.answers_file).read_text(encoding="utf-8"))
        out = answer_life(root, args.session, answers)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if action == "refine":
        out = refine_plan(root, args.session, args.message or "")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if action == "export":
        out = export_life_html(root, args.session)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if action == "show":
        out = load_life_report(root, args.session)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown life action {action}"}, ensure_ascii=False))
    return 2


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

    sg = sub.add_parser(
        "skill-gap",
        parents=[parent],
        help="JD skill-gap preflight: existing / supported_by_evidence / gap",
    )
    sg.add_argument("--job-id", default=None)
    sg.add_argument("--jd-file", default=None)
    sg.add_argument("--text", default=None)
    sg.set_defaults(func=cmd_skill_gap)

    mx = sub.add_parser(
        "match-explain",
        parents=[parent],
        help="rebuild JD requirement matrix (direct/partial/gap) + match_explain.md",
    )
    mx.add_argument("--job-id", required=True)
    mx.set_defaults(func=cmd_match_explain)

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
    qb.add_argument("--lang", default="zh", help="ui language for bilingual bank hits (zh/en/ja/es)")
    qb.set_defaults(func=cmd_questions)

    rag = sub.add_parser("rag-index", parents=[parent], help="build local question vector index")
    rag.set_defaults(func=cmd_rag_index)

    reval = sub.add_parser("rag-eval", parents=[parent], help="evaluate RAG hit@k on a query set")
    reval.add_argument("--query-file", default=None, help="jsonl with query + expect_ids")
    reval.add_argument("--k", type=int, default=3)
    reval.add_argument("--token", action="store_true", help="use token search instead of semantic")
    reval.set_defaults(func=cmd_rag_eval)

    llm = sub.add_parser("llm-info", parents=[parent], help="show LLM provider config")
    llm.add_argument("--provider", default=None)
    llm.add_argument("--model", default=None)
    llm.add_argument("--base-url", default=None)
    llm.set_defaults(func=cmd_llm_info)

    live = sub.add_parser("live", parents=[parent], help="launch Compass Web (WebSocket UI)")
    live.add_argument("--port", type=int, default=8766)
    live.set_defaults(func=cmd_live)
    web = sub.add_parser("web", parents=[parent], help="alias for live — primary WebSocket UI")
    web.add_argument("--port", type=int, default=8766)
    web.set_defaults(func=cmd_live)

    tl = sub.add_parser("timeline", parents=[parent], help="evidence chain graph JSON/HTML")
    tl.add_argument("--job-id", default=None)
    tl.add_argument("--html", default=None, help="write HTML graph file path")
    tl.set_defaults(func=cmd_timeline)

    er = sub.add_parser("export-report", parents=[parent], help="export diagnose/interview HTML(+PDF)")
    er.add_argument("--job-id", default=None)
    er.add_argument("--html-only", action="store_true", help="skip PDF attempt")
    er.set_defaults(func=cmd_export_report)

    i = sub.add_parser("interview-pack", parents=[parent], help="build interview pack + session")
    i.add_argument("--job-id", required=True)
    i.set_defaults(func=cmd_interview)

    ps = sub.add_parser(
        "practice-stats",
        parents=[parent],
        help="cross-job interview practice rollup (intervAI)",
    )
    ps.set_defaults(func=cmd_practice_stats)

    rm = sub.add_parser(
        "resume-metrics",
        parents=[parent],
        help="resume key metrics + one-page density lint",
    )
    rm.add_argument("--job-id", default=None)
    rm.add_argument("--resume", default=None, help="path to resume.json")
    rm.set_defaults(func=cmd_resume_metrics)

    sc = sub.add_parser("scorecard", parents=[parent], help="interview rubric scorecard")
    sc_sub = sc.add_subparsers(dest="scorecard_action", required=True)
    sc_show = sc_sub.add_parser("show", help="print scorecard.json")
    sc_show.add_argument("--job-id", required=True)
    sc_show.set_defaults(func=cmd_scorecard)
    sc_sync = sc_sub.add_parser("sync", help="fill session.md Scorecard from aggregate")
    sc_sync.add_argument("--job-id", required=True)
    sc_sync.set_defaults(func=cmd_scorecard)
    sc_imp = sc_sub.add_parser("import-oral", help="migrate oral_log.jsonl → scorecard")
    sc_imp.add_argument("--job-id", required=True)
    sc_imp.set_defaults(func=cmd_scorecard)
    sc_rec = sc_sub.add_parser("record", help="record one answered turn")
    sc_rec.add_argument("--job-id", required=True)
    sc_rec.add_argument("--turn", type=int, required=True)
    sc_rec.add_argument("--question", default="")
    sc_rec.add_argument("--answer", default=None)
    sc_rec.add_argument("--answer-file", default=None)
    sc_rec.add_argument("--scores", default=None, help='JSON e.g. {"substance":4}')
    sc_rec.add_argument("--requirement-ids", default="", help="comma-separated hard_01,...")
    sc_rec.add_argument("--note", default="")
    sc_rec.set_defaults(func=cmd_scorecard)

    di = sub.add_parser("diagnose", parents=[parent], help="gap compass report + bridge plan")
    di.add_argument("--job-id", default=None)
    di.add_argument("--fixture", default=None)
    di.set_defaults(func=cmd_diagnose)

    t = sub.add_parser("track", parents=[parent], help="update application board")
    t.add_argument("--job-id", default=None)
    t.add_argument("--status", default=None)
    t.add_argument("--note", default="")
    t.add_argument("--follow-up-due", default=None, help="ISO date YYYY-MM-DD")
    t.add_argument("--seed-from-match", action="store_true", help="seed band + follow_up_due from match_explain")
    t.add_argument("--list-due", action="store_true", help="list items with follow_up_due <= today")
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

    life = sub.add_parser("life", parents=[parent], help="interest explore → career plan (/life)")
    life_sub = life.add_subparsers(dest="life_action", required=True)
    le = life_sub.add_parser("explore", help="ingest narrative + confidence route (+ direct plan)")
    le.add_argument("--text", default=None)
    le.add_argument("--text-file", default=None)
    le.add_argument("--file", default=None, help="pdf/docx/txt/md path")
    le.add_argument("--session", default=None)
    le.set_defaults(func=cmd_life)
    la = life_sub.add_parser("answer", help="submit RIASEC answers JSON")
    la.add_argument("--session", required=True)
    la.add_argument("--answers-file", required=True, help='JSON {qid:1-5} or [{"id","value"}]')
    la.set_defaults(func=cmd_life)
    lr = life_sub.add_parser("refine", help="interactive follow-up on a plan")
    lr.add_argument("--session", required=True)
    lr.add_argument("--message", required=True)
    lr.set_defaults(func=cmd_life)
    lx = life_sub.add_parser("export", help="write HTML radar report")
    lx.add_argument("--session", required=True)
    lx.set_defaults(func=cmd_life)
    ls = life_sub.add_parser("show", help="load saved life report")
    ls.add_argument("--session", required=True)
    ls.set_defaults(func=cmd_life)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
