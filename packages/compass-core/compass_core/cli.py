"""Compass CLI."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .collectors import collect_ats_board, collect_career_html, collect_paste, collect_rss
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
    if args.source == "ats":
        board = getattr(args, "board", None)
        if not board:
            from .ats_scan import load_portals

            portals = load_portals(root)
            if not portals:
                print(
                    json.dumps(
                        {"error": "ats requires --board greenhouse:slug or content/portals.yml"},
                        ensure_ascii=False,
                    )
                )
                return 1
            from .ats_scan import collect_ats

            rows = []
            for spec in portals:
                rows.extend(collect_ats(root, board=spec, limit=args.limit, match=True))
            print(json.dumps(rows, ensure_ascii=False, indent=2))
            return 0
        rows = collect_ats_board(root, board, limit=args.limit)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if args.source == "companies":
        from .career_recommend import recommend_jobs
        from .observability import audit_event, span

        with span(root, "recommend"):
            out = recommend_jobs(
                root,
                keyword=getattr(args, "keyword", None),
                location=getattr(args, "location", None),
                limit=args.limit or 20,
                match=not getattr(args, "no_match", False),
                workers=getattr(args, "workers", 4) or 4,
            )
        audit_event(root, "recommend", count=len(out.get("recommended") or []))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(f"unknown source {args.source}", file=sys.stderr)
    return 1


def cmd_recommend(args) -> int:
    from .career_recommend import recommend_jobs
    from .observability import audit_event, span

    root = _root(args)
    with span(root, "recommend"):
        out = recommend_jobs(
            root,
            keyword=args.keyword,
            location=args.location,
            limit=args.limit or 20,
            match=not args.no_match,
            workers=args.workers or 4,
        )
    audit_event(root, "recommend", count=len(out.get("recommended") or []))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_grade(args) -> int:
    from .grade import compute_grade
    from .match import MatchResult as MR

    root = _root(args)
    path = root / "jobs" / args.job_id / "match.json"
    if not path.is_file():
        print(json.dumps({"error": f"missing {path}"}, ensure_ascii=False))
        return 1
    data = json.loads(path.read_text(encoding="utf-8"))
    mr = MR.from_dict(data)
    g = compute_grade(
        matrix_score=float((mr.match_explain or {}).get("matrix_score") or 0),
        coverage=mr.coverage,
        fatal_count=int((mr.match_explain or {}).get("fatal_count") or 0),
        recommendation=str((mr.match_explain or {}).get("recommendation") or ""),
        evidence_hit_n=len(mr.evidence_hits or []),
        skill_gap=mr.skill_gap,
        profile_fit=mr.profile_fit,
        posting_liveness=mr.posting_liveness,
        match_explain=mr.match_explain,
    )
    data["grade"] = g
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(g, ensure_ascii=False, indent=2))
    return 0


def cmd_scout(args) -> int:
    from .observability import audit_event
    from .scout import scout

    root = _root(args)
    boards = list(args.board or [])
    try:
        summary = scout(
            root,
            keyword=args.keyword,
            location=args.location,
            boards=boards or None,
            limit=args.limit,
            match=not args.no_match,
        )
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        return 1
    audit_event(root, "scout", count=summary.get("count"), keyword=args.keyword)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def cmd_resume_import(args) -> int:
    from .resume_import import import_resume_file

    out = import_resume_file(_root(args), args.file, job_id=args.job_id)
    print(json.dumps({"path": out["path"], "warnings": out["warnings"], "skills": (out["resume"].get("skills") or [])[:12]}, ensure_ascii=False, indent=2))
    return 0


def cmd_batch_match(args) -> int:
    from .batch_match import (
        batch_from_ats,
        batch_from_jobs_file,
        format_batch_board,
        list_batches,
        match_existing_jobs,
        save_batch,
    )
    from .observability import audit_event, span

    root = _root(args)
    if getattr(args, "batch_action", None) == "board":
        rows = list_batches(root, limit=getattr(args, "limit", 20) or 20)
        print(format_batch_board(rows))
        print(json.dumps({"count": len(rows), "batches": rows}, ensure_ascii=False, indent=2))
        return 0
    with span(root, "batch"):
        if getattr(args, "jobs", None):
            rows = batch_from_jobs_file(root, args.jobs, workers=getattr(args, "workers", 5) or 5)
            label = "url"
        elif getattr(args, "from_ats", None):
            rows = batch_from_ats(root, args.from_ats, limit=args.limit)
            label = "ats"
        elif getattr(args, "all_jobs", False):
            rows = match_existing_jobs(root, workers=args.workers)
            label = "all"
        else:
            print(
                json.dumps(
                    {
                        "error": "need batch board | --jobs urls.txt | --all-jobs | --from-ats",
                    },
                    ensure_ascii=False,
                )
            )
            return 1
        summary = save_batch(root, rows, label=label)
        audit_event(root, "batch", count=len(rows), batch_id=summary.get("batch_id"), label=label)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def cmd_research(args) -> int:
    from .company_research import build_research
    from .observability import audit_event

    root = _root(args)
    if not args.company and not args.job_id:
        print(json.dumps({"error": "need --company or --job-id"}, ensure_ascii=False))
        return 1
    out = build_research(root, company=args.company, job_id=args.job_id)
    audit_event(root, "research", company=out.get("company"), job_id=args.job_id)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_obs(args) -> int:
    from .observability import compute_slo, evaluate_alerts, export_prometheus, status, tail_audit

    root = _root(args)
    action = args.obs_action
    if action == "status":
        print(json.dumps(status(root), ensure_ascii=False, indent=2))
        return 0
    if action == "tail":
        print(json.dumps(tail_audit(root, n=args.n or 20), ensure_ascii=False, indent=2))
        return 0
    if action == "alerts":
        print(json.dumps(evaluate_alerts(root), ensure_ascii=False, indent=2))
        return 0
    if action == "export-prom":
        text = export_prometheus(root)
        out = getattr(args, "out", None)
        if out:
            Path(out).write_text(text, encoding="utf-8")
            print(json.dumps({"path": out, "bytes": len(text)}, ensure_ascii=False))
        else:
            print(text, end="")
        return 0
    if action == "slo":
        print(json.dumps(compute_slo(root), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
    return 1


def cmd_anki(args) -> int:
    from .anki_export import export_anki

    root = _root(args)
    out = export_anki(root, job_id=getattr(args, "job_id", None), label=getattr(args, "label", None))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_experience(args) -> int:
    from .experience_bank import complete_experience, search_experience

    action = getattr(args, "experience_action", "search")
    if action == "complete":
        hits = complete_experience(
            query=getattr(args, "query", None),
            company=getattr(args, "company", None),
            topic=getattr(args, "topic", None),
            limit=getattr(args, "limit", 10) or 10,
            id=getattr(args, "id", None),
        )
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return 0
    hits = search_experience(
        query=getattr(args, "query", None),
        company=getattr(args, "company", None),
        topic=getattr(args, "topic", None),
        limit=getattr(args, "limit", 10) or 10,
    )
    print(json.dumps(hits, ensure_ascii=False, indent=2))
    return 0


def cmd_train(args) -> int:
    from .train import train_advance, train_complete, train_goto, train_next, train_status

    root = _root(args)
    job_id = args.job_id
    action = args.train_action
    if action == "status":
        print(json.dumps(train_status(root, job_id), ensure_ascii=False, indent=2))
        return 0
    if action == "next":
        print(json.dumps(train_next(root, job_id), ensure_ascii=False, indent=2))
        return 0
    if action == "complete":
        print(json.dumps(train_complete(root, job_id, note=args.note or ""), ensure_ascii=False, indent=2))
        return 0
    if action == "advance":
        print(json.dumps(train_advance(root, job_id), ensure_ascii=False, indent=2))
        return 0
    if action == "goto":
        print(json.dumps(train_goto(root, job_id, args.stage), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
    return 1


def cmd_intel(args) -> int:
    from .job_intel import build_dossier, verify_salary_claim

    root = _root(args)
    action = args.intel_action
    if action == "verify-salary":
        out = verify_salary_claim(
            claimed=args.claimed,
            years=args.years,
            degree=args.degree or "",
            title=args.title or "",
            level=args.level or "",
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("accepted") else 2
    if action == "dossier":
        out = build_dossier(
            root,
            company=args.company or "",
            title=args.title or "",
            job_id=args.job_id,
            years=args.years,
            degree=args.degree or "",
            claimed_salary=args.claimed,
            live=bool(args.live),
            accept_tos_risk=bool(args.i_accept_tos_risk),
            min_sources=args.min_sources or 2,
        )
        # slim stdout
        slim = {
            "summary": out.get("summary"),
            "path": out.get("path"),
            "md": out.get("md"),
            "rejected_salary_samples": out.get("rejected_salary_samples"),
        }
        print(json.dumps(slim, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
    return 1


def cmd_comp(args) -> int:
    from .comp_bench import coach_script, lookup_comp, lookup_comp_merged

    root = _root(args)
    action = getattr(args, "comp_action", "lookup")
    if action == "ingest-live":
        from .comp_live import ingest_live_file

        out = ingest_live_file(root, args.file, source=args.source or "offershow_capture")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if action == "refresh":
        from .comp_live import live_lookup

        srcs = [s.strip() for s in (args.sources or "offershow,http,jobs").split(",") if s.strip()]
        out = live_lookup(
            root,
            query=args.query or args.title or "",
            title=args.title or "",
            company=args.company or "",
            location=args.location or "",
            level=args.level or "",
            sources=srcs,
            accept_tos_risk=bool(args.i_accept_tos_risk),
            use_cache=False,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    # lookup
    if getattr(args, "live", False):
        srcs = None
        if getattr(args, "sources", None):
            srcs = [s.strip() for s in args.sources.split(",") if s.strip()]
        out = lookup_comp_merged(
            root,
            title=args.title or "",
            level=args.level or "",
            location=args.location or "",
            company=getattr(args, "company", None) or "",
            query=getattr(args, "query", None) or "",
            limit=args.limit or 10,
            live=True,
            sources=srcs,
            accept_tos_risk=bool(getattr(args, "i_accept_tos_risk", False)),
        )
    else:
        out = lookup_comp(
            root,
            title=args.title or getattr(args, "query", None) or "",
            level=args.level or "",
            location=args.location or "",
            limit=args.limit or 10,
        )
    out["coach"] = coach_script(out, your_cash=args.cash)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_resume_pick(args) -> int:
    from .resume_pick import apply_picks, list_pickable_bullets

    root = _root(args)
    action = args.resume_pick_action
    if action == "list":
        items = list_pickable_bullets(root, args.job_id)
        slim = [
            {"pick_id": i["pick_id"], "jd_hits": i.get("jd_hits"), "text": (i.get("text") or "")[:120], "title": i.get("title")}
            for i in items[: args.limit or 40]
        ]
        print(json.dumps(slim, ensure_ascii=False, indent=2))
        return 0
    if action == "apply":
        ids = [x.strip() for x in (args.picks or "").split(",") if x.strip()]
        if args.picks_file:
            raw = Path(args.picks_file).read_text(encoding="utf-8")
            try:
                data = json.loads(raw)
                ids = data if isinstance(data, list) else data.get("pick_ids") or ids
            except json.JSONDecodeError:
                ids = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.startswith("#")]
        if not ids:
            print(json.dumps({"error": "need --picks or --picks-file"}, ensure_ascii=False))
            return 1
        out = apply_picks(root, ids, job_id=args.job_id, name=args.name or "")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
    return 1


def cmd_pipeline(args) -> int:
    root = _root(args)
    if getattr(args, "pipeline_action", None) == "board":
        from .pipeline_board import format_pipeline_board, pipeline_board

        data = pipeline_board(root)
        print(format_pipeline_board(data))
        if getattr(args, "as_json", False):
            print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    if not getattr(args, "text_file", None):
        print(json.dumps({"error": "need pipeline board | --text-file"}, ensure_ascii=False))
        return 1
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


def cmd_session(args) -> int:
    from .auth_session import import_session, session_status

    root = _root(args)
    action = args.session_action
    if action == "import":
        out = import_session(root, args.path, name=args.name or "default")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if action == "status":
        print(json.dumps(session_status(root, args.name or "default"), ensure_ascii=False, indent=2))
        return 0
    if action == "scout-html":
        from .auth_collect import scout_auth_html

        out = scout_auth_html(
            root,
            fixture=getattr(args, "fixture", None),
            html=Path(args.file).read_text(encoding="utf-8") if getattr(args, "file", None) else None,
            accept_tos_risk=bool(getattr(args, "i_accept_tos_risk", False)),
            list_url=getattr(args, "url", None),
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
    return 1


def cmd_warehouse(args) -> int:
    from .observability import span
    from .warehouse import ingest_jsonl, search_jobs, seed_fixture, warehouse_stats

    root = _root(args)
    action = args.warehouse_action
    if action == "stats":
        print(json.dumps(warehouse_stats(root), ensure_ascii=False, indent=2))
        return 0
    if action == "ingest":
        with span(root, "warehouse_ingest"):
            out = ingest_jsonl(root, args.file)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if action == "search":
        hits = search_jobs(root, args.q or "", location=args.location, limit=args.limit or 20)
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return 0
    if action == "seed":
        out = seed_fixture(root, n=args.n or 100)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
    return 1


def cmd_storybank(args) -> int:
    from .storybank import load_storybank, rebuild_storybank, top_stories
    from .story_vault import import_json_storybank, list_stories, recommend_stories

    root = _root(args)
    action = args.storybank_action
    if action == "rebuild":
        idx = rebuild_storybank(root)
        n = import_json_storybank(root)
        print(json.dumps({"count": idx["count"], "vault_seeded": n}, ensure_ascii=False, indent=2))
        return 0
    if action == "list":
        vault = list_stories(root, limit=50)
        if vault:
            slim = [
                {"id": i["id"], "strength": i.get("strength"), "tags": i.get("tags"), "source": i.get("source")}
                for i in vault
            ]
            print(json.dumps(slim, ensure_ascii=False, indent=2))
            return 0
        idx = load_storybank(root)
        slim = [{"id": i["id"], "title": i.get("title"), "strength": i.get("strength")} for i in (idx.get("items") or [])]
        print(json.dumps(slim, ensure_ascii=False, indent=2))
        return 0
    if action == "show":
        items = list_stories(root, limit=200)
        hit = next((i for i in items if i.get("id") == args.id), None)
        if not hit:
            bank = load_storybank(root).get("items") or []
            hit = next((i for i in bank if i.get("id") == args.id), None)
        if not hit:
            hit = (top_stories(root, limit=1) or [None])[0]
        print(json.dumps(hit, ensure_ascii=False, indent=2))
        return 0 if hit else 1
    if action == "recommend":
        hits = recommend_stories(root, job_id=args.job_id, limit=args.limit or 5)
        print(json.dumps(hits, ensure_ascii=False, indent=2))
        return 0
    if action == "compose":
        from .story_compose import compose_stories

        if not args.job_id:
            print(json.dumps({"error": "compose needs --job-id"}, ensure_ascii=False))
            return 1
        out = compose_stories(root, args.job_id, limit=args.limit or 5)
        print(json.dumps({k: out[k] for k in out if k != "stories"}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
    return 1


def cmd_transcript_import(args) -> int:
    from .transcript import import_transcript

    root = _root(args)
    text = Path(args.file).read_text(encoding="utf-8") if args.file else (args.text or "")
    if not text.strip():
        print(json.dumps({"error": "need --file or --text"}, ensure_ascii=False))
        return 1
    out = import_transcript(root, args.job_id, text, sync_scorecard=not args.no_scorecard)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_offer(args) -> int:
    from .offer_compare import compare_offers, empty_offer, load_offer, save_offer

    root = _root(args)
    action = args.offer_action
    if action == "init":
        o = empty_offer(args.id, title=args.title or "", company=args.company or "")
        if getattr(args, "cash", None) is not None:
            o["cash"] = args.cash
        if getattr(args, "equity", None) is not None:
            o["equity"] = args.equity
        if getattr(args, "level", None):
            o["level"] = args.level
        if getattr(args, "market_p50", None) is not None:
            o["market_p50"] = args.market_p50
        if getattr(args, "job_id", None):
            o["job_id"] = args.job_id
        path = save_offer(root, o)
        print(json.dumps({"path": str(path), "offer": o}, ensure_ascii=False, indent=2))
        return 0
    if action == "show":
        print(json.dumps(load_offer(root, args.id), ensure_ascii=False, indent=2))
        return 0
    if action == "compare":
        ids = [x.strip() for x in (args.ids or "").split(",") if x.strip()]
        if len(ids) < 1:
            print(json.dumps({"error": "need --ids a,b"}, ensure_ascii=False))
            return 1
        print(json.dumps(compare_offers(root, ids), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
    return 1


def cmd_negotiate(args) -> int:
    from .negotiate import build_negotiate_pack

    out = build_negotiate_pack(_root(args), job_id=args.job_id)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_calibrate(args) -> int:
    from .calibrate import calibration_report, record_outcome

    root = _root(args)
    action = args.calibrate_action
    if action == "record":
        item = record_outcome(root, args.job_id, args.outcome, note=args.note or "")
        print(json.dumps(item, ensure_ascii=False, indent=2))
        return 0
    if action == "report":
        print(json.dumps(calibration_report(root), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": f"unknown {action}"}, ensure_ascii=False))
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
    company = getattr(args, "company", None)
    industry = getattr(args, "industry", None)
    if company:
        from .company_pack import search_company_pack

        hits = search_company_pack(company, limit=args.limit)
        print(json.dumps({"backend": "company_pack", "hits": hits}, ensure_ascii=False, indent=2))
        return 0
    if industry:
        from .industry_pack import search_industry_pack

        hits = search_industry_pack(industry, limit=args.limit)
        print(json.dumps({"backend": "industry_pack", "industry": industry, "hits": hits}, ensure_ascii=False, indent=2))
        return 0
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
    from .rag_eval import evaluate_queries, load_queries, record_eval_metrics

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
    try:
        record_eval_metrics(root, out, query_file=str(qpath))
    except Exception:
        pass
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
    out = export_report(
        root, job_id, want_pdf=not args.html_only, mentor=bool(getattr(args, "mentor", False))
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_interview(args) -> int:
    out = interview_and_save(_root(args), args.job_id)
    try:
        from .observability import audit_event

        audit_event(_root(args), "interview", job_id=args.job_id, bank_n=out.get("bank_n"))
    except Exception:
        pass
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_practice_stats(args) -> int:
    from .practice_stats import export_practice_center, practice_rollup

    root = _root(args)
    if getattr(args, "export", False):
        print(json.dumps(export_practice_center(root), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(practice_rollup(root), ensure_ascii=False, indent=2))
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
    if action == "roots":
        from .root_cause import diagnose_root_causes

        sc = load_scorecard(root, job_id)
        agg = sc.get("aggregate") or {}
        roots = agg.get("root_causes") or diagnose_root_causes(agg.get("scores") or {})
        print(json.dumps({"job_id": job_id, "root_causes": roots, "scores": agg.get("scores")}, ensure_ascii=False, indent=2))
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
        try:
            from .observability import audit_event

            audit_event(root, "scorecard_record", job_id=job_id, turn=args.turn)
        except Exception:
            pass
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
    if getattr(args, "calibrate", False):
        from .calibrate import calibrate_summary_for_job

        out["calibrate"] = calibrate_summary_for_job(root, job_id)
    try:
        from .observability import audit_event

        audit_event(root, "diagnose", job_id=job_id, actions=out.get("actions"))
    except Exception:
        pass
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
    d.add_argument(
        "--source",
        choices=("paste", "rss", "career", "ats", "companies"),
        required=True,
    )
    d.add_argument("--text", default=None)
    d.add_argument("--text-file", default=None)
    d.add_argument("--url", default=None)
    d.add_argument("--job-id", default=None)
    d.add_argument("--board", default=None, help="greenhouse:slug | lever:slug | ashby:slug")
    d.add_argument("--keyword", default=None, help="for --source companies")
    d.add_argument("--location", default=None)
    d.add_argument("--no-match", action="store_true")
    d.add_argument("--workers", type=int, default=4)
    d.add_argument("--limit", type=int, default=10)
    d.set_defaults(func=cmd_discover)

    rec = sub.add_parser("recommend", parents=[parent], help="crawl company career/ATS → ranked jobs")
    rec_sub = rec.add_subparsers(dest="recommend_action", required=True)
    rec_j = rec_sub.add_parser("jobs", help="official career pages + public ATS boards")
    rec_j.add_argument("--keyword", default=None)
    rec_j.add_argument("--location", default=None)
    rec_j.add_argument("--limit", type=int, default=20)
    rec_j.add_argument("--workers", type=int, default=4)
    rec_j.add_argument("--no-match", action="store_true")
    rec_j.set_defaults(func=cmd_recommend)

    gr = sub.add_parser("grade", parents=[parent], help="A-F / 100-pt grade for a matched job")
    gr.add_argument("--job-id", required=True)
    gr.set_defaults(func=cmd_grade)

    scouting = sub.add_parser(
        "scout",
        parents=[parent],
        help="keyword/location filter over ATS boards → match (discover-and-analyze)",
    )
    scouting.add_argument("--keyword", default=None)
    scouting.add_argument("--location", default=None)
    scouting.add_argument(
        "--board",
        action="append",
        default=None,
        help="repeatable: greenhouse:slug",
    )
    scouting.add_argument("--limit", type=int, default=10)
    scouting.add_argument("--no-match", action="store_true", help="list only, skip match_and_save")
    scouting.set_defaults(func=cmd_scout)

    ri = sub.add_parser("resume-import", parents=[parent], help="PDF/text → resume.json")
    ri.add_argument("--file", required=True)
    ri.add_argument("--job-id", default=None)
    ri.set_defaults(func=cmd_resume_import)

    bm = sub.add_parser("batch-match", parents=[parent], help="batch match jobs / ATS board / urls file")
    bm.add_argument("--all-jobs", action="store_true")
    bm.add_argument("--from-ats", default=None, help="greenhouse:slug")
    bm.add_argument("--jobs", default=None, help="text file: one URL or greenhouse:slug per line")
    bm.add_argument("--limit", type=int, default=10)
    bm.add_argument("--workers", type=int, default=5)
    bm.set_defaults(func=cmd_batch_match)

    bat = sub.add_parser("batch", parents=[parent], help="batch --jobs | batch board")
    bat.add_argument("--jobs", default=None, help="urls.txt / board specs")
    bat.add_argument("--workers", type=int, default=5)
    bat.add_argument("--all-jobs", action="store_true")
    bat.add_argument("--from-ats", default=None)
    bat.add_argument("--limit", type=int, default=10)
    bat.set_defaults(func=cmd_batch_match)
    bat_sub = bat.add_subparsers(dest="batch_action", required=False)
    bat_board = bat_sub.add_parser("board", help="recent batch summaries table")
    bat_board.add_argument("--limit", type=int, default=20)
    bat_board.set_defaults(func=cmd_batch_match)

    res = sub.add_parser("research", parents=[parent], help="company research + contact checklist")
    res.add_argument("--company", default=None)
    res.add_argument("--job-id", default=None)
    res.set_defaults(func=cmd_research)

    ob = sub.add_parser("obs", parents=[parent], help="local audit/metrics/alerts/APM")
    ob_sub = ob.add_subparsers(dest="obs_action", required=True)
    ob_st = ob_sub.add_parser("status")
    ob_st.set_defaults(func=cmd_obs)
    ob_t = ob_sub.add_parser("tail")
    ob_t.add_argument("-n", type=int, default=20)
    ob_t.set_defaults(func=cmd_obs)
    ob_a = ob_sub.add_parser("alerts", help="evaluate alert rules → logs/alerts.json")
    ob_a.set_defaults(func=cmd_obs)
    ob_p = ob_sub.add_parser("export-prom", help="Prometheus text exposition")
    ob_p.add_argument("--out", default=None)
    ob_p.set_defaults(func=cmd_obs)
    ob_slo = ob_sub.add_parser("slo", help="SLO snapshot → logs/slo.json")
    ob_slo.set_defaults(func=cmd_obs)

    an = sub.add_parser("anki", parents=[parent], help="export Anki TSV/JSON cards")
    an_sub = an.add_subparsers(dest="anki_action", required=True)
    an_ex = an_sub.add_parser("export")
    an_ex.add_argument("--job-id", default=None)
    an_ex.add_argument("--all", action="store_true")
    an_ex.add_argument("--label", default=None)
    an_ex.set_defaults(func=cmd_anki)

    exp = sub.add_parser("experience", parents=[parent], help="search local 面经 bank")
    exp_sub = exp.add_subparsers(dest="experience_action", required=True)
    exp_s = exp_sub.add_parser("search")
    exp_s.add_argument("--query", default=None)
    exp_s.add_argument("--company", default=None)
    exp_s.add_argument("--topic", default=None)
    exp_s.add_argument("--limit", type=int, default=10)
    exp_s.set_defaults(func=cmd_experience)
    exp_c = exp_sub.add_parser("complete", help="template-complete answer points")
    exp_c.add_argument("--query", default=None)
    exp_c.add_argument("--company", default=None)
    exp_c.add_argument("--topic", default=None)
    exp_c.add_argument("--id", default=None)
    exp_c.add_argument("--limit", type=int, default=10)
    exp_c.set_defaults(func=cmd_experience)

    tr = sub.add_parser("train", parents=[parent], help="8-stage progressive interview training")
    tr_sub = tr.add_subparsers(dest="train_action", required=True)
    for name in ("status", "next", "advance"):
        p_tr = tr_sub.add_parser(name)
        p_tr.add_argument("--job-id", required=True)
        p_tr.set_defaults(func=cmd_train)
    tr_c = tr_sub.add_parser("complete")
    tr_c.add_argument("--job-id", required=True)
    tr_c.add_argument("--note", default="")
    tr_c.set_defaults(func=cmd_train)
    tr_g = tr_sub.add_parser("goto")
    tr_g.add_argument("--job-id", required=True)
    tr_g.add_argument("--stage", type=int, required=True)
    tr_g.set_defaults(func=cmd_train)

    cmp_ = sub.add_parser("comp", parents=[parent], help="compensation benchmarks + live OfferShow")
    cmp_sub = cmp_.add_subparsers(dest="comp_action", required=True)
    cmp_l = cmp_sub.add_parser("lookup")
    cmp_l.add_argument("--title", default="")
    cmp_l.add_argument("--query", default="")
    cmp_l.add_argument("--company", default="")
    cmp_l.add_argument("--level", default="")
    cmp_l.add_argument("--location", default="")
    cmp_l.add_argument("--cash", type=float, default=None)
    cmp_l.add_argument("--limit", type=int, default=10)
    cmp_l.add_argument("--live", action="store_true", help="query live sources (OfferShow API / JD / cache)")
    cmp_l.add_argument("--sources", default=None, help="comma: offershow,http,levels,jobs,career,extra,cache")
    cmp_l.add_argument("--i-accept-tos-risk", action="store_true")
    cmp_l.set_defaults(func=cmd_comp)
    cmp_r = cmp_sub.add_parser("refresh", help="force live fetch → cache")
    cmp_r.add_argument("--query", default="")
    cmp_r.add_argument("--title", default="")
    cmp_r.add_argument("--company", default="")
    cmp_r.add_argument("--level", default="")
    cmp_r.add_argument("--location", default="")
    cmp_r.add_argument("--sources", default="offershow,http,levels,jobs,career")
    cmp_r.add_argument("--i-accept-tos-risk", action="store_true")
    cmp_r.set_defaults(func=cmd_comp)
    cmp_i = cmp_sub.add_parser("ingest-live", help="import OfferShow/Levels capture JSON/JSONL/CSV")
    cmp_i.add_argument("--file", required=True)
    cmp_i.add_argument("--source", default="offershow_capture")
    cmp_i.set_defaults(func=cmd_comp)

    intel = sub.add_parser("intel", parents=[parent], help="multi-source job intel + rumor filter")
    intel_sub = intel.add_subparsers(dest="intel_action", required=True)
    iv = intel_sub.add_parser("verify-salary", help="reject implausible pay claims")
    iv.add_argument("--claimed", required=True, help="e.g. 年薪1000万 or 500000")
    iv.add_argument("--years", type=float, default=None)
    iv.add_argument("--degree", default="")
    iv.add_argument("--title", default="")
    iv.add_argument("--level", default="")
    iv.set_defaults(func=cmd_intel)
    idos = intel_sub.add_parser("dossier", help="corroborated posting/pay/hours/reputation/landing")
    idos.add_argument("--company", default="")
    idos.add_argument("--title", default="")
    idos.add_argument("--job-id", default=None)
    idos.add_argument("--years", type=float, default=None)
    idos.add_argument("--degree", default="")
    idos.add_argument("--claimed", default=None, help="optional rumor salary to test")
    idos.add_argument("--live", action="store_true")
    idos.add_argument("--i-accept-tos-risk", action="store_true")
    idos.add_argument("--min-sources", type=int, default=2)
    idos.set_defaults(func=cmd_intel)


    rp = sub.add_parser("resume-pick", parents=[parent], help="Pick Don't Edit resume bullets")
    rp_sub = rp.add_subparsers(dest="resume_pick_action", required=True)
    rp_l = rp_sub.add_parser("list")
    rp_l.add_argument("--job-id", required=True)
    rp_l.add_argument("--limit", type=int, default=40)
    rp_l.set_defaults(func=cmd_resume_pick)
    rp_a = rp_sub.add_parser("apply")
    rp_a.add_argument("--job-id", required=True)
    rp_a.add_argument("--picks", default=None, help="comma-separated pick_ids")
    rp_a.add_argument("--picks-file", default=None)
    rp_a.add_argument("--name", default="")
    rp_a.set_defaults(func=cmd_resume_pick)

    sess = sub.add_parser("session", parents=[parent], help="auth session vault (opt-in)")
    sess_sub = sess.add_subparsers(dest="session_action", required=True)
    sess_i = sess_sub.add_parser("import")
    sess_i.add_argument("--path", required=True)
    sess_i.add_argument("--name", default="default")
    sess_i.set_defaults(func=cmd_session)
    sess_st = sess_sub.add_parser("status")
    sess_st.add_argument("--name", default="default")
    sess_st.set_defaults(func=cmd_session)
    sess_sc = sess_sub.add_parser("scout-html", help="parse list HTML/fixture → warehouse")
    sess_sc.add_argument("--fixture", default=None)
    sess_sc.add_argument("--file", default=None)
    sess_sc.add_argument("--url", default=None)
    sess_sc.add_argument("--i-accept-tos-risk", action="store_true")
    sess_sc.set_defaults(func=cmd_session)

    wh = sub.add_parser("warehouse", parents=[parent], help="local job warehouse (100k-ready)")
    wh_sub = wh.add_subparsers(dest="warehouse_action", required=True)
    wh_st = wh_sub.add_parser("stats")
    wh_st.set_defaults(func=cmd_warehouse)
    wh_in = wh_sub.add_parser("ingest")
    wh_in.add_argument("--file", required=True, help="JSONL jobs")
    wh_in.set_defaults(func=cmd_warehouse)
    wh_se = wh_sub.add_parser("search")
    wh_se.add_argument("--q", default="")
    wh_se.add_argument("--location", default=None)
    wh_se.add_argument("--limit", type=int, default=20)
    wh_se.set_defaults(func=cmd_warehouse)
    wh_seed = wh_sub.add_parser("seed", help="synthetic fixture rows")
    wh_seed.add_argument("-n", type=int, default=100)
    wh_seed.set_defaults(func=cmd_warehouse)

    sb = sub.add_parser("storybank", parents=[parent], help="STAR storybank from evidence")
    sb_sub = sb.add_subparsers(dest="storybank_action", required=True)
    sb_r = sb_sub.add_parser("rebuild")
    sb_r.set_defaults(func=cmd_storybank)
    sb_l = sb_sub.add_parser("list")
    sb_l.set_defaults(func=cmd_storybank)
    sb_s = sb_sub.add_parser("show")
    sb_s.add_argument("--id", default=None)
    sb_s.set_defaults(func=cmd_storybank)
    sb_rec = sb_sub.add_parser("recommend")
    sb_rec.add_argument("--job-id", default=None)
    sb_rec.add_argument("--limit", type=int, default=5)
    sb_rec.set_defaults(func=cmd_storybank)
    sb_co = sb_sub.add_parser("compose", help="optimize story combo for JD coverage")
    sb_co.add_argument("--job-id", required=True)
    sb_co.add_argument("--limit", type=int, default=5)
    sb_co.set_defaults(func=cmd_storybank)

    ti = sub.add_parser("transcript-import", parents=[parent], help="import Otter/Zoom-like transcript")
    ti.add_argument("--job-id", required=True)
    ti.add_argument("--file", default=None)
    ti.add_argument("--text", default=None)
    ti.add_argument("--no-scorecard", action="store_true")
    ti.set_defaults(func=cmd_transcript_import)

    of = sub.add_parser("offer", parents=[parent], help="offer six-dim compare")
    of_sub = of.add_subparsers(dest="offer_action", required=True)
    of_i = of_sub.add_parser("init")
    of_i.add_argument("--id", required=True)
    of_i.add_argument("--title", default="")
    of_i.add_argument("--company", default="")
    of_i.add_argument("--job-id", default=None)
    of_i.add_argument("--cash", type=float, default=None)
    of_i.add_argument("--equity", type=float, default=None)
    of_i.add_argument("--level", default="")
    of_i.add_argument("--market-p50", dest="market_p50", type=float, default=None)
    of_i.set_defaults(func=cmd_offer)
    of_sh = of_sub.add_parser("show")
    of_sh.add_argument("--id", required=True)
    of_sh.set_defaults(func=cmd_offer)
    of_c = of_sub.add_parser("compare")
    of_c.add_argument("--ids", required=True, help="comma-separated offer ids")
    of_c.set_defaults(func=cmd_offer)

    ng = sub.add_parser("negotiate", parents=[parent], help="local negotiate pack (no live salary)")
    ng.add_argument("--job-id", default=None)
    ng.set_defaults(func=cmd_negotiate)

    cal = sub.add_parser("calibrate", parents=[parent], help="practice vs real outcome calibration")
    cal_sub = cal.add_subparsers(dest="calibrate_action", required=True)
    cal_r = cal_sub.add_parser("record")
    cal_r.add_argument("--job-id", required=True)
    cal_r.add_argument("--outcome", required=True, choices=("pass", "fail", "offer", "ghosted", "withdrawn"))
    cal_r.add_argument("--note", default="")
    cal_r.set_defaults(func=cmd_calibrate)
    cal_rep = cal_sub.add_parser("report")
    cal_rep.set_defaults(func=cmd_calibrate)

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
    qb.add_argument("--company", default=None, help="company pack e.g. bytedance / 字节")
    qb.add_argument("--industry", default=None, help="industry pack: tech / finance / consulting")
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
    er.add_argument("--mentor", action="store_true", help="also write mentor_report.md/.pdf")
    er.set_defaults(func=cmd_export_report)

    i = sub.add_parser("interview-pack", parents=[parent], help="build interview pack + session")
    i.add_argument("--job-id", required=True)
    i.set_defaults(func=cmd_interview)

    ps = sub.add_parser(
        "practice-stats",
        parents=[parent],
        help="cross-job interview practice rollup (intervAI)",
    )
    ps.add_argument("--export", action="store_true", help="write reports/practice_center.md")
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
    sc_roots = sc_sub.add_parser("roots", help="five-dim root-cause diagnosis")
    sc_roots.add_argument("--job-id", required=True)
    sc_roots.set_defaults(func=cmd_scorecard)
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
    di.add_argument("--calibrate", action="store_true", help="attach narrative_hits calibrate summary")
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
        "pipeline", parents=[parent], help="demo pipeline or board TUI"
    )
    pipe.add_argument("--text-file", default=None)
    pipe.set_defaults(func=cmd_pipeline)
    pipe_sub = pipe.add_subparsers(dest="pipeline_action", required=False)
    pipe_b = pipe_sub.add_parser("board", help="terminal pipeline dashboard")
    pipe_b.add_argument("--json", dest="as_json", action="store_true")
    pipe_b.set_defaults(func=cmd_pipeline)

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
