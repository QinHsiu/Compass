"""compas.txt P0–P2 gap fills."""

from __future__ import annotations

from pathlib import Path

from compass_core.ats_scan import normalize_jobs, parse_board_spec, scan_board
from compass_core.batch_match import save_batch
from compass_core.calibrate import calibration_report, record_outcome
from compass_core.grade import compute_grade, letter_from_score
from compass_core.negotiate import build_negotiate_pack
from compass_core.offer_compare import compare_offers, empty_offer, save_offer
from compass_core.practice_stats import export_practice_center, practice_rollup
from compass_core.resume_import import parse_resume_text
from compass_core.storybank import rebuild_storybank
from compass_core.transcript import import_transcript, parse_transcript, turns_to_qa_pairs


def test_parse_board_spec():
    assert parse_board_spec("greenhouse:acme") == ("greenhouse", "acme")
    assert parse_board_spec("https://boards.greenhouse.io/acme/jobs/1")[0] == "greenhouse"


def test_normalize_greenhouse():
    payload = {
        "jobs": [
            {
                "title": "SWE",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                "location": {"name": "Remote"},
                "content": "<p>Build APIs</p>",
                "updated_at": "2026-07-01T00:00:00Z",
            }
        ]
    }
    jobs = normalize_jobs("greenhouse", "acme", payload)
    assert len(jobs) == 1
    assert "SWE" in jobs[0]["title"]
    assert "Build APIs" in jobs[0]["text"]


def test_scan_board_injectable():
    def fake_fetch(url: str):
        assert "greenhouse" in url
        return {"jobs": [{"title": "X", "absolute_url": "https://boards.greenhouse.io/x/jobs/1", "content": "y"}]}

    jobs = scan_board("greenhouse:x", limit=5, fetch_fn=fake_fetch)
    assert len(jobs) == 1


def test_letter_and_grade():
    assert letter_from_score(90) == "A"
    assert letter_from_score(50, fatal=1) == "F"
    g = compute_grade(
        matrix_score=82,
        coverage=0.8,
        fatal_count=0,
        recommendation="strong",
        evidence_hit_n=4,
        skill_gap={"existing": ["a"], "supported_by_evidence": ["b"], "gap": []},
        profile_fit={"status": "pass"},
        posting_liveness={"status": "fresh"},
        match_explain={
            "row_count": 10,
            "direct_count": 7,
            "partial_count": 2,
            "gap_count": 1,
            "fatal_count": 0,
            "matrix_score": 82,
        },
    )
    assert g["letter"] in ("A", "B", "C", "D")
    assert 3.5 <= g["global_1_5"] <= 5.0
    assert "match_cv" in g["dimensions"]
    assert g.get("score_100", 0) >= 40
    assert "综合匹配度" in (g.get("display") or "")
    assert "parts" in g


def test_resume_parse():
    text = """张三
zhang@example.com
简介
算法工程师
工作经历
某公司 2020-2023
- 负责推荐系统，p99 降低 30%
技能
Python, LLM, PyTorch
"""
    r = parse_resume_text(text)
    assert r["basics"].get("email")
    assert r["skills"] or r["experience"]


def test_batch_save(tmp_path: Path):
    rows = [{"job_id": "j1", "title": "T", "company": "C", "score": 80, "letter": "B", "global_1_5": 4.0}]
    s = save_batch(tmp_path, rows, label="t")
    assert s["count"] == 1
    assert (tmp_path / "batches" / s["batch_id"] / "summary.json").is_file()


def test_transcript_parse():
    text = """Interviewer: Tell me about yourself.
Candidate: I built a search system with 20% CTR lift.
Interviewer: How did you measure?
Candidate: A/B test over 2 weeks.
"""
    turns = parse_transcript(text)
    assert len(turns) >= 4
    pairs = turns_to_qa_pairs(turns)
    assert pairs[0]["answer"]


def test_transcript_import(tmp_path: Path):
    # minimal scorecard path via import without evidence gate issues — import_oral may call gate
    text = "Interviewer: Hi?\nCandidate: Hello with metric 10%.\n"
    # Avoid scorecard sync if no evidence — use no sync
    out = import_transcript(tmp_path, "job_t", text, sync_scorecard=False)
    assert out["pairs"] >= 1
    assert (tmp_path / "interviews" / "job_t" / "oral_log.jsonl").is_file()


def test_offer_compare(tmp_path: Path):
    a = empty_offer("a", company="A")
    a["scores"] = {d: 5 for d in a["scores"]}
    b = empty_offer("b", company="B")
    b["scores"] = {d: 2 for d in b["scores"]}
    save_offer(tmp_path, a)
    save_offer(tmp_path, b)
    c = compare_offers(tmp_path, ["a", "b"])
    assert c["offers"][0]["id"] == "a"


def test_negotiate(tmp_path: Path):
    out = build_negotiate_pack(tmp_path, job_id=None)
    assert Path(out["path"]).is_file()
    assert out["disclaimer"] == "no_live_market_percentile"


def test_calibrate(tmp_path: Path):
    # seed fake scorecards
    for i, outcome in enumerate(["fail", "fail", "pass"]):
        jid = f"job_{i}"
        d = tmp_path / "interviews" / jid
        d.mkdir(parents=True)
        (d / "scorecard.json").write_text(
            json_dumps_sc(jid, jd_fit=4.5 if outcome == "fail" else 2.0),
            encoding="utf-8",
        )
        record_outcome(tmp_path, jid, outcome)
    rep = calibration_report(tmp_path)
    assert rep["sample_size"] == 3
    assert rep["ready"]
    assert rep["drift_notes"]


def json_dumps_sc(job_id: str, jd_fit: float) -> str:
    import json

    return json.dumps(
        {
            "job_id": job_id,
            "answers": [{"scores": {"jd_fit": jd_fit}}],
            "aggregate": {
                "scores": {
                    "substance": 3,
                    "structure": 3,
                    "relevance": 3,
                    "credibility": 3,
                    "jd_fit": jd_fit,
                },
                "gate_pass_rate": 1.0,
                "answer_count": 1,
            },
        }
    )


def test_practice_export(tmp_path: Path):
    d = tmp_path / "interviews" / "j"
    d.mkdir(parents=True)
    (d / "scorecard.json").write_text(json_dumps_sc("j", 3.0), encoding="utf-8")
    r = practice_rollup(tmp_path)
    assert r["sessions"] == 1
    assert r["est_minutes_total"] == 4
    out = export_practice_center(tmp_path)
    assert Path(out["path"]).is_file()


def test_storybank_empty(tmp_path: Path):
    idx = rebuild_storybank(tmp_path)
    assert idx["count"] == 0
