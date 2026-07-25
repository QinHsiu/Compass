"""Rounds 7–13 competitive gap fills."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from compass_core.bei_probe import followup_from_probe, probe_star
from compass_core.interview_persona import pick_persona
from compass_core.jd import parse_jd
from compass_core.posting_liveness import apply_liveness_to_explain, assess_liveness, detect_ats
from compass_core.practice_stats import practice_rollup
from compass_core.question_dedup import filter_bank_hits, question_hash
from compass_core.resume_lint import lint_resume_density
from compass_core.resume_metrics import calculate_key_metrics


def test_bei_probe_empty():
    p = probe_star("")
    assert not p["ok"]
    assert "situation" in p["missing"]
    assert followup_from_probe(p)


def test_bei_probe_metrics():
    ans = (
        "当时线上延迟升高，我负责定位。采取了限流与缓存改造，"
        "结果 p99 从 800ms 降到 200ms。"
    )
    p = probe_star(ans)
    assert p["ok"] or "metrics" not in p["missing"]
    assert p["structure_score"] >= 3


def test_question_dedup():
    asked = {question_hash("介绍一下你自己？")}
    hits = [
        {"q": "介绍一下你自己"},
        {"q": "讲讲最近一个项目"},
    ]
    out = filter_bank_hits(hits, asked)
    assert len(out) == 1
    assert "项目" in out[0]["q"]


def test_resume_lint_overflow():
    resume = {
        "basics": {"summary": "x" * 50},
        "skills": ["a"] * 5,
        "experience": [{"bullets": [f"b{i}" for i in range(20)]}],
    }
    d = lint_resume_density(resume)
    assert d["status"] == "fail"
    assert not d["one_page_ok"]


def test_resume_metrics():
    resume = {
        "experience": [
            {"org": "A", "start": "2020", "end": "2023", "bullets": ["x"]},
            {"company": "B", "dates": "2018-2020", "bullets": []},
        ],
        "projects": [{"name": "p1"}],
        "skills": ["python", "llm"],
        "education": [{"degree": "硕士"}],
    }
    m = calculate_key_metrics(resume)
    assert m["companies"] == 2
    assert m["projects"] == 1
    assert m["skills"] == 2
    assert m["highest_degree"] in ("master", "硕士")
    assert m["years_experience"] >= 2


def test_practice_rollup_empty(tmp_path: Path):
    r = practice_rollup(tmp_path)
    assert r["sessions"] == 0
    assert r["total_answers"] == 0


def test_practice_rollup(tmp_path: Path):
    sc = tmp_path / "interviews" / "job_a" / "scorecard.json"
    sc.parent.mkdir(parents=True)
    sc.write_text(
        '{"job_id":"job_a","updated_at":"2026-01-01","answers":[{},{}],'
        '"aggregate":{"scores":{"jd_fit":4},"gate_pass_rate":1.0}}',
        encoding="utf-8",
    )
    r = practice_rollup(tmp_path)
    assert r["sessions"] == 1
    assert r["total_answers"] == 2
    assert r["avg_jd_fit"] == 4.0


def test_persona_challenging():
    jd = parse_jd("公司：X\n职位：算法工程师\n必须：深度学习")
    p = pick_persona(jd, {"recommendation": "skip", "fatal_count": 1})
    assert p["persona_id"] == "challenging"


def test_persona_technical():
    jd = parse_jd("公司：Y\n职位：大模型算法\n要求：LLM 推理优化")
    p = pick_persona(jd, {"recommendation": "strong", "fatal_count": 0})
    assert p["persona_id"] == "technical"


def test_ats_detect():
    assert detect_ats("https://boards.greenhouse.io/acme/jobs/1") == "greenhouse"
    assert detect_ats("https://jobs.lever.co/acme") == "lever"


def test_liveness_stale_caps_band():
    lv = assess_liveness(
        url="https://boards.greenhouse.io/x",
        posted_at="2020-01-01",
        as_of=date(2026, 7, 1),
        stale_days=45,
    )
    assert lv["status"] == "stale"
    assert lv["ats"] == "greenhouse"
    explain = apply_liveness_to_explain({"recommendation": "strong"}, lv)
    assert explain["recommendation"] == "exploratory"


def test_liveness_fresh():
    lv = assess_liveness(posted_at="2026-07-01", as_of=date(2026, 7, 10))
    assert lv["status"] == "fresh"


def test_parse_jd_url():
    jd = parse_jd(
        "公司：Z\n职位：SRE\n发布：2026-06-01\nhttps://jobs.ashbyhq.com/z/abc\n必须：Linux"
    )
    assert jd.url and "ashbyhq" in jd.url
    assert jd.posted_at
