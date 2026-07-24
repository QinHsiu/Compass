"""Tests for requirement evidence matrix (job-resume-tailor Round 2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass_core.evidence import EvidenceItem, build_index
from compass_core.jd import parse_jd
from compass_core.match import MatchResult, match_and_save
from compass_core.match_explain import build_requirement_matrix, summarize_matrix
from compass_core.diagnose import diagnose_and_save
from compass_core.interview import interview_and_save

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


def test_matrix_direct_partial_gap():
    evidence = [
        EvidenceItem(
            id="ev_py",
            title="Python serving",
            skills=["python", "kubernetes"],
            actions="Tuned HPA for training jobs",
            metrics="CPU waste -30%",
            body="Tuned HPA for training jobs. CPU waste -30%.",
        )
    ]
    jd = parse_jd(
        """公司：Acme
职位：ML Eng
要求：
- 必须熟悉 Python
- 必须有 COBOL 主框架经验
- 熟悉 HPA 调优
"""
    )
    rows = build_requirement_matrix(jd, evidence)
    by_fit = {r.fit for r in rows}
    assert "direct" in by_fit or any(r.fit == "direct" for r in rows)
    # COBOL should be gap
    cobol = [r for r in rows if "cobol" in r.text.lower()]
    assert cobol and cobol[0].fit == "gap"
    fatal_or_material = cobol[0].severity in ("fatal", "material")
    assert fatal_or_material
    summary = summarize_matrix(rows, evidence_count=1)
    assert summary["recommendation"] in ("strong", "plausible", "exploratory", "skip")
    assert "matrix_score" in summary


def test_match_writes_matrix_and_md(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    assert m.requirement_matrix
    assert m.match_explain.get("recommendation")
    saved = json.loads((root / "jobs" / m.job_id / "match.json").read_text(encoding="utf-8"))
    assert saved["requirement_matrix"]
    assert (root / "jobs" / m.job_id / "match_explain.md").is_file()
    md = (root / "jobs" / m.job_id / "match_explain.md").read_text(encoding="utf-8")
    assert "Hard requirements" in md or "hard" in md.lower()


def test_from_dict_legacy_without_matrix():
    m = MatchResult.from_dict(
        {
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
    )
    assert m.requirement_matrix == []
    assert m.match_explain["recommendation"] == "exploratory"


def test_diagnose_and_interview_use_matrix(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    d = diagnose_and_save(root, m.job_id)
    report = (root / "diagnoses" / m.job_id / "report.md").read_text(encoding="utf-8")
    assert "矩阵分" in report or "matrix" in report.lower() or "建议" in report
    iv = interview_and_save(root, m.job_id)
    session = (root / "interviews" / m.job_id / "session.md").read_text(encoding="utf-8")
    assert "requirement-mapped" in session or "STAR" in session
    pack = json.loads((root / "interviews" / m.job_id / "pack.json").read_text(encoding="utf-8"))
    assert "requirement_matrix" in pack
    assert d["actions"] >= 1
    assert iv["evidence_n"] >= 0
