"""Unit tests for compass-core."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass_core.collectors import assert_url_allowed, collect_paste
from compass_core.diagnose import diagnose_and_save
from compass_core.evidence import build_index, load_evidence
from compass_core.gate import check_claim, UNVERIFIED
from compass_core.interview import interview_and_save
from compass_core.jd import parse_jd
from compass_core.match import match_and_save
from compass_core.resume import apply_and_save
from compass_core.track import upsert

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "content" / "fixtures" / "demo"


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    # copy evidence + profile
    ev = tmp_path / "evidence"
    ev.mkdir()
    for p in (FIXTURE / "evidence").glob("*.md"):
        (ev / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    build_index(tmp_path)
    (tmp_path / "profile").mkdir()
    (tmp_path / "profile" / "profile.json").write_text(
        (FIXTURE / "profile" / "profile.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return tmp_path


def test_parse_jd():
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    jd = parse_jd(text)
    assert "python" in jd.keywords or any("Python" in r for r in jd.hard_requirements)
    assert jd.company == "ExampleAI"
    assert "ML Platform" in jd.title or "Engineer" in jd.title


def test_evidence_index(root: Path):
    items = load_evidence(root)
    assert len(items) >= 3
    idx = json.loads((root / "evidence" / "index.json").read_text(encoding="utf-8"))
    assert idx["count"] == len(items)


def test_gate_verified_and_reject(root: Path):
    items = load_evidence(root)
    ok = check_claim("cut p99 latency with redis cache ev_featstore_latency", items)
    assert ok.ok
    bad = check_claim("Became CEO of a Fortune 500 investment bank after an IPO roadshow", items)
    assert not bad.ok
    marked = check_claim(f"Claimed rocket science {UNVERIFIED}", items)
    assert marked.ok and marked.status == "unverified"


def test_match_diagnose_actions_schema(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    assert m.score > 0
    out = diagnose_and_save(root, m.job_id)
    actions = json.loads(
        (root / "diagnoses" / m.job_id / "actions.json").read_text(encoding="utf-8")
    )
    assert actions
    for a in actions:
        assert a["what"] and a["proof"] and a["eta"]
        assert a["quadrant"] in ("evidence", "narrative", "skill", "process")
    report = (root / "diagnoses" / m.job_id / "report.md").read_text(encoding="utf-8")
    assert "Quadrant: Evidence" in report
    assert out["actions"] == len(actions)


def test_resume_patch_evidence_gated(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    r = apply_and_save(root, m.job_id)
    assert r["ops"] >= 0
    resume = json.loads(
        (root / "resumes" / m.job_id / "resume.json").read_text(encoding="utf-8")
    )
    blob = json.dumps(resume)
    assert "ev_" in blob
    ats = json.loads(
        (root / "resumes" / m.job_id / "ats_report.json").read_text(encoding="utf-8")
    )
    assert "keyword_coverage" in ats


def test_interview_cites_evidence(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    out = interview_and_save(root, m.job_id)
    session = (root / "interviews" / m.job_id / "session.md").read_text(encoding="utf-8")
    assert "evidence_id" in session or "ev_" in session
    assert out["bank_n"] >= 1
    assert "检索到的题库题目" in session or "Retrieved bank questions" in session
    assert (root / "interviews" / m.job_id / "bank_hits.json").is_file()
    hits = json.loads((root / "interviews" / m.job_id / "bank_hits.json").read_text(encoding="utf-8"))
    if hits:
        assert hits[0].get("q_zh") or hits[0].get("q_display")


def test_bank_bilingual():
    from compass_core.questions import enrich_hit, format_bank_section, search_questions

    hits = search_questions("RAG agent memory", keywords=["rag", "agent"], limit=3, lang="zh")
    assert hits
    h = enrich_hit(hits[0], lang="zh")
    assert h.get("q_zh")
    assert h.get("q_display")
    section = format_bank_section(hits, lang="zh")
    assert "英文" in section or h["q_zh"] in section


def test_templates_and_json_resume(root: Path):
    from compass_core.templates import list_themes, recommend_theme, render_all, to_json_resume

    themes = list_themes()
    assert len(themes) >= 12
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    r = apply_and_save(root, m.job_id)
    assert r["theme"]
    assert (root / "resumes" / m.job_id / "resume.html").is_file()
    assert (root / "resumes" / m.job_id / "resume.jsonresume.json").is_file()
    data = json.loads((root / "resumes" / m.job_id / "resume.json").read_text(encoding="utf-8"))
    jr = to_json_resume(data)
    assert "basics" in jr and "skills" in jr
    assert recommend_theme(["python", "kubernetes"], "ML Platform") == "tech_single"


def test_question_bank_retrieval():
    from compass_core.questions import load_bank, search_questions

    bank = load_bank()
    assert len(bank) >= 90
    hits = search_questions("python kubernetes feature store GIL", keywords=["python", "kubernetes"], limit=5)
    assert hits
    assert all("source" in h for h in hits)


def test_ingest_text(tmp_path: Path):
    from compass_core.ingest import extract_text, split_resume_to_evidence_drafts

    p = tmp_path / "cv.txt"
    p.write_text("Backend Engineer\n\n- Built APIs\n- Cut latency 50%\n", encoding="utf-8")
    r = extract_text(p)
    assert "Backend" in r["text"]
    drafts = split_resume_to_evidence_drafts(r["text"])
    assert drafts


def test_llm_agent_bank_loaded():
    from compass_core.questions import load_bank, search_questions

    bank = load_bank()
    llmish = [x for x in bank if x.get("topic") in ("llm", "agent") or "agent" in (x.get("tags") or [])]
    assert len(llmish) >= 20
    hits = search_questions("RAG agent tool memory prompt injection", keywords=["rag", "agent"], limit=5)
    assert hits


def test_voice_tts_optional():
    from compass_core.voice import synthesize_speech

    out = synthesize_speech("你好，这是 Compass 面试题。")
    # either path or install warning — must not crash
    assert "path" in out and "warning" in out


def test_followup_rules():
    from compass_core.interview import next_followup, opening_question

    pack = {
        "title": "ML Platform Engineer",
        "gaps": ["必须熟悉 feature store"],
        "keyword_misses": ["rag"],
        "evidence": [{"evidence_id": "ev_featstore_latency", "title": "latency"}],
        "bank_hits": [{"q": "Explain RAG evaluation?"}],
    }
    assert "evidence_id" in opening_question(pack) or "适合" in opening_question(pack)
    weak = next_followup(pack, "我很厉害", gate_ok=False, turn=0)
    assert weak["question"] and weak["mode"] in ("rules", "llm")
    strong = next_followup(pack, "我们把 p99 做到 45ms ev_featstore_latency", gate_ok=True, turn=0)
    assert strong["question"]


def test_llm_describe():
    from compass_core.llm import describe_config

    d = describe_config()
    assert "provider" in d and "model" in d


def test_timeline_builder(root: Path):
    from compass_core.timeline import build_timeline, render_timeline_html

    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    apply_and_save(root, m.job_id)
    interview_and_save(root, m.job_id)
    data = build_timeline(root, job_id=m.job_id)
    assert data["summary"]["evidence"] >= 1
    assert data["summary"]["links"] >= 1
    html = render_timeline_html(data)
    assert "证据链图谱" in html
    assert "<svg" in html
    assert 'class="node"' in html


def test_export_report(root: Path):
    from compass_core.export_report import export_report

    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    apply_and_save(root, m.job_id)
    interview_and_save(root, m.job_id)
    diagnose_and_save(root, m.job_id)
    out = export_report(root, m.job_id, want_pdf=False)
    assert Path(out["html"]).is_file()
    body = Path(out["html"]).read_text(encoding="utf-8")
    assert "四象限" in body
    assert "quadrant-cards" in body
    assert "证据引用" in body


def test_timeline_interactive_html(root: Path):
    from compass_core.timeline import build_timeline, render_timeline_html

    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    apply_and_save(root, m.job_id)
    interview_and_save(root, m.job_id)
    html = render_timeline_html(build_timeline(root, job_id=m.job_id))
    assert 'id="fEv"' in html
    assert 'id="q"' in html
    assert "节点详情" in html


def test_rag_eval_fixtures(root: Path):
    from compass_core.rag_eval import evaluate_queries, load_queries

    qpath = FIXTURE / "rag_queries.jsonl"
    assert qpath.is_file()
    out = evaluate_queries(root, load_queries(qpath), k=3, semantic=False)
    assert out["n"] >= 5
    assert "hit_at_k" in out


def test_rag_fallback(root: Path):
    from compass_core.rag import index_questions, semantic_search

    info = index_questions(root)
    assert "count" in info
    hits = semantic_search(root, "python kubernetes feature store", k=3)
    assert isinstance(hits, list)


def test_diagnose_bank_drills(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    diagnose_and_save(root, m.job_id)
    assert (root / "diagnoses" / m.job_id / "bank_drills.json").is_file()
    drills = json.loads((root / "diagnoses" / m.job_id / "bank_drills.json").read_text(encoding="utf-8"))
    assert isinstance(drills, list)


def test_pipeline_four_steps(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    apply_and_save(root, m.job_id)
    interview_and_save(root, m.job_id)
    diagnose_and_save(root, m.job_id)
    assert (root / "resumes" / m.job_id / "resume.md").is_file()
    assert (root / "interviews" / m.job_id / "session.md").is_file()
    assert (root / "diagnoses" / m.job_id / "report.md").is_file()


def test_track_and_blocklist(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    item = upsert(root, m.job_id, "applied", note="sent")
    assert item["status"] == "applied"
    with pytest.raises(PermissionError):
        assert_url_allowed("https://www.zhipin.com/job_detail/123")


def test_paste_collector(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = collect_paste(root, text)
    assert (root / "jobs" / m.job_id / "match.json").is_file()


def test_rss_and_career_fixtures(root: Path, tmp_path: Path):
    import feedparser
    from bs4 import BeautifulSoup
    from compass_core.match import match_and_save as mas

    # RSS fixture offline parse (no network)
    feed = feedparser.parse((FIXTURE / "jobs.rss").read_text(encoding="utf-8"))
    assert len(feed.entries) >= 2
    for entry in feed.entries[:2]:
        body = f"职位：{entry.title}\n\n{entry.description}"
        mas(root, body)

    html = (FIXTURE / "career_sample.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")
    links = [a.get_text(strip=True) for a in soup.find_all("a") if "Engineer" in a.get_text()]
    assert len(links) >= 1
    for t in links:
        mas(root, f"职位：{t}\n公司：example.ai\n")


def test_life_riasec_score():
    from compass_core.life import load_riasec_bank, score_riasec

    bank = load_riasec_bank()
    assert len(bank["questions"]) >= 36
    from collections import Counter

    assert Counter(q["dim"] for q in bank["questions"]) == {
        "R": 6,
        "I": 6,
        "A": 6,
        "S": 6,
        "E": 6,
        "C": 6,
    }
    answers = {q["id"]: (5 if q["dim"] == "I" else 2) for q in bank["questions"]}
    scored = score_riasec(answers)
    assert scored["scores"]["I"] > scored["scores"]["R"]
    assert scored["holland_code"].startswith("I")
    assert scored["answered"] == len(bank["questions"])


def test_life_confidence_route(root: Path):
    from compass_core.life import answer_life, assess_confidence, explore_life

    thin = "我想找工作。"
    a = assess_confidence(thin)
    assert a["route"] == "assessment"
    assert a["confidence"] < 0.72

    rich = (
        "我是计算机硕士，在北京做了 4 年 Python 后端与机器学习平台开发，"
        "熟悉 PyTorch、Kubernetes 与数据管道。希望在人工智能赛道升职或转算法工程，"
        "目标城市上海或远程，薪资看机会。"
    )
    b = assess_confidence(rich)
    assert b["signal_classes"] >= 3
    assert b["route"] == "direct"
    assert b["confidence"] >= 0.72

    out = explore_life(root, text=thin)
    assert out["need_assessment"] is True
    assert out["questions"]
    answers = {q["id"]: 4 for q in out["questions"]}
    answered = answer_life(root, out["session_id"], answers)
    assert answered["ready"]
    assert (root / "life" / out["session_id"] / "report.md").is_file()
    assert answered["plan"]["paths"]

    direct = explore_life(root, text=rich)
    assert direct["ready"] is True
    assert direct["route"] == "direct"
    assert direct["plan"]["scores"]
    assert (root / "life" / direct["session_id"] / "export" / "report.html").is_file()
