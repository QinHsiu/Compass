"""Tests for zero-LLM JD skill-gap classifier (career-ops Round 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass_core.evidence import EvidenceItem, load_evidence
from compass_core.jd import parse_jd
from compass_core.match import match_and_save
from compass_core.resume import apply_and_save, build_targeted_resume, empty_resume
from compass_core.skill_gap import (
    classify_skills,
    skill_mentioned_in_text,
)

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "content" / "fixtures" / "demo"


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    from compass_core.evidence import build_index

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


def test_skill_mentioned_word_boundary():
    assert skill_mentioned_in_text("Java", "Built APIs in Java and Kotlin")
    assert not skill_mentioned_in_text("Java", "Expert in JavaScript and TypeScript")
    assert skill_mentioned_in_text("C++", "Used C++ for inference kernels")
    assert skill_mentioned_in_text("pytorch", "skills: pytorch, redis")


def test_classify_three_buckets():
    evidence = [
        EvidenceItem(
            id="ev_a",
            title="Serving",
            skills=["pytorch", "python"],
            actions="Deployed Triton inference with Grafana dashboards",
            body="Deployed Triton inference with Grafana dashboards",
        )
    ]
    result = classify_skills(
        ["pytorch", "Grafana", "COBOL", "Java"],
        evidence,
    )
    assert "pytorch" in result.existing
    assert any(s.lower() == "grafana" for s in result.supported_by_evidence)
    assert "COBOL" in result.gap
    # Java must not match via JavaScript-style substring; neither is present → gap
    assert "Java" in result.gap
    assert "COBOL" not in result.injectable
    assert "pytorch" in result.injectable


def test_match_writes_skill_gap(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    assert "skill_gap" in m.to_dict()
    sg = m.skill_gap
    assert set(sg.keys()) >= {"existing", "supported_by_evidence", "gap"}
    # Fixture evidence names python + kubernetes → python should be existing
    existing_l = [s.lower() for s in sg["existing"]]
    assert "python" in existing_l or "kubernetes" in existing_l
    saved = json.loads((root / "jobs" / m.job_id / "match.json").read_text(encoding="utf-8"))
    assert "skill_gap" in saved


def test_resume_never_injects_gap_skills(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    # Force a synthetic gap into the match result
    m.skill_gap = {
        "existing": ["python"],
        "supported_by_evidence": ["redis"],
        "gap": ["COBOL", "Mainframe"],
    }
    jd = parse_jd(text, job_id=m.job_id)
    updated, _ops, ats = build_targeted_resume(empty_resume("Demo"), jd, m, root)
    skills_l = [s.lower() for s in (updated.get("skills") or [])]
    assert "cobol" not in skills_l
    assert "mainframe" not in skills_l
    assert "python" in skills_l
    assert ats["checklist"]["no_gap_skills_injected"] is True
    assert "skill_gap" in ats

    # Full apply path also reports checklist
    r = apply_and_save(root, m.job_id)
    assert r["ats"]["checklist"]["no_gap_skills_injected"] is True


def test_match_from_dict_tolerates_legacy():
    from compass_core.match import MatchResult

    legacy = {
        "job_id": "x",
        "title": "t",
        "company": "c",
        "coverage": 0.5,
        "keyword_hits": [],
        "keyword_misses": [],
        "hard_gaps": [],
        "evidence_hits": [],
        "score": 50.0,
    }
    m = MatchResult.from_dict(legacy)
    assert m.skill_gap == {"existing": [], "supported_by_evidence": [], "gap": []}
