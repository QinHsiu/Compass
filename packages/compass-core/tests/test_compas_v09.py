"""compas v0.9 optimization tests."""

from __future__ import annotations

import json
from pathlib import Path

from compass_core.calibrate import build_narrative_hits, calibration_report, record_outcome
from compass_core.export_report import export_mentor_report
from compass_core.grade import compute_grade, compute_score_parts
from compass_core.offer_compare import compare_offers, empty_offer, save_offer, vs_market_p50
from compass_core.scout import filter_jobs, scout
from compass_core.story_vault import recommend_stories, upsert_from_answer


def test_filter_jobs_keyword_location():
    jobs = [
        {"title": "Software Engineer", "text": "工作地：Remote US\nBuild APIs"},
        {"title": "Data Analyst", "text": "工作地：北京\nSQL"},
    ]
    out = filter_jobs(jobs, keyword="Software", location="Remote")
    assert len(out) == 1
    assert "Software" in out[0]["title"]


def test_scout_mock(tmp_path: Path):
    payload = {
        "jobs": [
            {
                "title": "ML Engineer",
                "absolute_url": "https://boards.greenhouse.io/x/jobs/1",
                "location": {"name": "Remote"},
                "content": "<p>LLM inference</p>",
            },
            {
                "title": "Sales",
                "absolute_url": "https://boards.greenhouse.io/x/jobs/2",
                "location": {"name": "NYC"},
                "content": "<p>quota</p>",
            },
        ]
    }

    def fetch(url: str):
        return payload

    summary = scout(
        tmp_path,
        keyword="ML|Engineer",
        location="Remote",
        boards=["greenhouse:x"],
        limit=5,
        match=True,
        fetch_fn=fetch,
    )
    assert summary["count"] >= 1
    assert summary["jobs"][0].get("job_id")
    assert (tmp_path / "batches" / summary["batch_id"] / "summary.json").is_file()


def test_score_parts_and_display():
    parts = compute_score_parts(
        match_explain={
            "row_count": 10,
            "direct_count": 6,
            "partial_count": 2,
            "gap_count": 2,
            "fatal_count": 0,
        },
        skill_gap={"existing": ["a"], "supported_by_evidence": ["b"], "gap": ["c"]},
        evidence_hit_n=4,
    )
    assert 0 <= parts["direct_evidence"] <= 40
    assert 0 <= parts["transferable"] <= 35
    assert 0 <= parts["gap_risk"] <= 25
    assert abs(
        parts["score_100"]
        - (parts["direct_evidence"] + parts["transferable"] + parts["gap_risk"])
    ) < 0.2
    g = compute_grade(
        matrix_score=80,
        recommendation="strong",
        evidence_hit_n=4,
        skill_gap={"existing": ["a"], "supported_by_evidence": ["b"], "gap": []},
        match_explain={
            "row_count": 10,
            "direct_count": 7,
            "partial_count": 2,
            "gap_count": 1,
            "fatal_count": 0,
            "matrix_score": 80,
        },
        profile_fit={"status": "pass"},
        posting_liveness={"status": "fresh"},
    )
    assert "综合匹配度" in g["display"]
    assert "/100" in g["display"]
    assert "parts" in g and "direct_evidence" in g["parts"]


def test_calibrate_narrative(tmp_path: Path):
    jid = "job_c"
    (tmp_path / "jobs" / jid).mkdir(parents=True)
    (tmp_path / "jobs" / jid / "match.json").write_text(
        json.dumps(
            {
                "job_id": jid,
                "match_explain": {"recommendation": "strong"},
                "grade": {"letter": "B", "score_100": 78},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "diagnoses" / jid).mkdir(parents=True)
    (tmp_path / "diagnoses" / jid / "actions.json").write_text(
        json.dumps(
            [
                {
                    "quadrant": "narrative",
                    "priority": "P0",
                    "what": "把指标前置到简历摘要",
                }
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "interviews" / jid).mkdir(parents=True)
    (tmp_path / "interviews" / jid / "scorecard.json").write_text(
        json.dumps(
            {
                "job_id": jid,
                "answers": [
                    {
                        "question": "指标如何前置？",
                        "scores": {
                            "structure": 2,
                            "credibility": 2,
                            "jd_fit": 3,
                            "substance": 3,
                            "relevance": 3,
                        },
                    }
                ],
                "aggregate": {
                    "scores": {
                        "structure": 2,
                        "credibility": 2,
                        "jd_fit": 3,
                        "substance": 3,
                        "relevance": 3,
                    },
                    "answer_count": 1,
                    "gate_pass_rate": 1.0,
                },
            }
        ),
        encoding="utf-8",
    )
    hits = build_narrative_hits(tmp_path, jid)
    assert hits
    item = record_outcome(tmp_path, jid, "fail")
    assert item.get("narrative_hits")
    assert item.get("predicted") == "apply"
    rep = calibration_report(tmp_path)
    assert "band_accuracy" in rep
    assert rep["narrative_hits"]


def test_offer_vs_p50(tmp_path: Path):
    assert vs_market_p50(120, 100) == "高"
    assert vs_market_p50(100, 100) == "齐"
    assert vs_market_p50(80, 100) == "低"
    a = empty_offer("a", company="A")
    a["cash"] = 120
    a["market_p50"] = 100
    a["level"] = "L5"
    save_offer(tmp_path, a)
    c = compare_offers(tmp_path, ["a"])
    md = Path(c["path"]).read_text(encoding="utf-8")
    assert "相对 P50" in md
    assert c["offers"][0]["vs_p50"] == "高"


def test_story_vault(tmp_path: Path):
    row = upsert_from_answer(
        tmp_path,
        job_id="j1",
        turn=1,
        answer="当时线上延迟升高，我负责定位并引入缓存，结果 p99 从 800ms 降到 200ms。ev_demo_1",
        evidence_ids=["ev_demo_1"],
        keywords=["llm", "cache"],
        gate_ok=True,
    )
    assert row and row["id"]
    hits = recommend_stories(tmp_path, job_id="j1", keywords=["cache"], limit=3)
    assert hits


def test_mentor_export(tmp_path: Path):
    jid = "job_m"
    (tmp_path / "jobs" / jid).mkdir(parents=True)
    (tmp_path / "jobs" / jid / "match.json").write_text(
        json.dumps(
            {
                "job_id": jid,
                "title": "Eng",
                "company": "X",
                "grade": {
                    "display": "综合匹配度：78/100（B级）",
                    "score_100": 78,
                    "letter": "B",
                },
                "match_explain": {"recommendation": "plausible"},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "diagnoses" / jid).mkdir(parents=True)
    (tmp_path / "diagnoses" / jid / "report.md").write_text(
        "# Diagnose\n\n## Summary\nok\n", encoding="utf-8"
    )
    out = export_mentor_report(tmp_path, jid)
    assert Path(out["mentor_md"]).is_file()
    assert "Mentor report" in Path(out["mentor_md"]).read_text(encoding="utf-8")
