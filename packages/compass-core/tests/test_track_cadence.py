"""Tests for match-band track seeding (clover-public Round 4)."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from compass_core.evidence import build_index
from compass_core.match import match_and_save
from compass_core.diagnose import diagnose_and_save
from compass_core.track import list_due, load_board, seed_from_match

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


def test_seed_from_match_and_list_due(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    item = seed_from_match(root, m.job_id)
    assert item["match_band"] in ("strong", "plausible", "exploratory", "skip")
    assert item["suggested_action"]
    assert "match_synced_at" in item
    board = load_board(root)
    assert any(i["job_id"] == m.job_id for i in board["items"])

    # Force overdue
    item2 = seed_from_match(root, m.job_id)
    # manually set due in past via re-seed after patching board
    board = load_board(root)
    for it in board["items"]:
        if it["job_id"] == m.job_id:
            it["follow_up_due"] = (date.today() - timedelta(days=1)).isoformat()
    from compass_core.track import save_board

    save_board(root, board)
    due = list_due(root)
    assert any(i["job_id"] == m.job_id for i in due)
    assert item2["job_id"] == m.job_id


def test_diagnose_seeds_track(root: Path):
    text = (FIXTURE / "jd.txt").read_text(encoding="utf-8")
    m = match_and_save(root, text)
    out = diagnose_and_save(root, m.job_id)
    assert out.get("track_item")
    assert out["track_item"]["match_band"]
