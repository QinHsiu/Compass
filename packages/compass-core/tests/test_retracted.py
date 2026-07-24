"""Tests for retracted_claims (CareerForge Round 5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass_core.evidence import build_index
from compass_core.match import match_and_save
from compass_core.interview import interview_and_save
from compass_core.retracted import collect_retracted_claims

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


def test_retracted_from_matrix_gaps(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    # Force a hard gap into match.json after match
    m = match_and_save(root, text)
    match_path = root / "jobs" / m.job_id / "match.json"
    data = json.loads(match_path.read_text(encoding="utf-8"))
    data["requirement_matrix"] = data.get("requirement_matrix") or []
    data["requirement_matrix"].append(
        {
            "id": "hard_99",
            "kind": "hard",
            "text": "必须持有 COBOL 认证",
            "fit": "gap",
            "evidence_ids": [],
            "fit_score": 0.0,
            "severity": "fatal",
            "rationale": "test",
        }
    )
    gaps = list((data.get("skill_gap") or {}).get("gap") or [])
    gaps.append("cobol")
    data.setdefault("skill_gap", {})["gap"] = list(dict.fromkeys(gaps))
    match_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    claims = collect_retracted_claims(root, m.job_id)
    assert any(c["source"] == "requirement_gap" for c in claims)
    assert any(c["source"] == "skill_gap" for c in claims)

    iv = interview_and_save(root, m.job_id)
    pack = json.loads((root / "interviews" / m.job_id / "pack.json").read_text(encoding="utf-8"))
    assert pack.get("retracted_claims")
    session = (root / "interviews" / m.job_id / "session.md").read_text(encoding="utf-8")
    assert "Do not claim" in session or "勿声称" in session
    assert iv["job_id"] == m.job_id
