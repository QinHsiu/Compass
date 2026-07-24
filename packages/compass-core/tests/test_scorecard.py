"""Tests for interview scorecard (interview-coach-skill Round 3)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass_core.evidence import build_index
from compass_core.match import match_and_save
from compass_core.interview import interview_and_save
from compass_core.scorecard import (
    import_oral_log,
    load_scorecard,
    record_answer,
    sync_session_md,
)

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "content" / "fixtures" / "demo"


@pytest.fixture()
def root(tmp_path: Path) -> Path:
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


def test_record_and_aggregate(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    interview_and_save(root, m.job_id)
    assert (root / "interviews" / m.job_id / "scorecard.json").is_file()

    data = record_answer(
        root,
        m.job_id,
        turn=0,
        question="Why this role?",
        answer="I cut p99 latency with redis cache ev_featstore_latency",
        scores={"substance": 4, "structure": 3},
    )
    assert data["aggregate"]["answer_count"] == 1
    assert data["answers"][0]["evidence_ids"]
    assert data["answers"][0]["scores"]["substance"] == 4

    # overwrite same turn
    data2 = record_answer(
        root,
        m.job_id,
        turn=0,
        question="Why this role?",
        answer="I cut p99 latency with redis cache ev_featstore_latency",
        scores={"substance": 5, "structure": 4, "relevance": 4, "credibility": 5, "jd_fit": 4},
    )
    assert data2["aggregate"]["answer_count"] == 1
    assert data2["answers"][0]["scores"]["substance"] == 5

    session = (root / "interviews" / m.job_id / "session.md").read_text(encoding="utf-8")
    assert "5" in session or "Technical" in session
    sync_session_md(root, m.job_id)
    session2 = (root / "interviews" / m.job_id / "session.md").read_text(encoding="utf-8")
    assert "| Technical |" in session2


def test_reject_unknown_evidence(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    interview_and_save(root, m.job_id)
    with pytest.raises(ValueError, match="unknown evidence"):
        record_answer(
            root,
            m.job_id,
            turn=1,
            question="x",
            answer="I invented ev_not_real_at_all",
        )


def test_import_oral_log(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    interview_and_save(root, m.job_id)
    log = root / "interviews" / m.job_id / "oral_log.jsonl"
    log.write_text(
        json.dumps(
            {
                "q": "intro",
                "answer": "redis cache cut latency ev_featstore_latency",
                "gate": "verified",
                "turn": 0,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    data = import_oral_log(root, m.job_id)
    assert data["aggregate"]["answer_count"] >= 1
    loaded = load_scorecard(root, m.job_id)
    assert loaded["answers"]
