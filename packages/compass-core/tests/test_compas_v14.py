"""compas v0.14 core-gap fills: train, story compose, comp, board, pick, experience complete."""

from __future__ import annotations

import json
from pathlib import Path

from compass_core.comp_bench import lookup_comp
from compass_core.experience_bank import complete_answer, complete_experience
from compass_core.pipeline_board import format_pipeline_board, pipeline_board
from compass_core.resume_pick import apply_picks, list_pickable_bullets
from compass_core.story_compose import compose_stories
from compass_core.story_vault import upsert_from_answer
from compass_core.train import train_advance, train_next, train_status


def test_train_eight_stages(tmp_path: Path):
    st = train_status(tmp_path, "j1")
    assert st["stages_total"] == 8
    assert st["stage"]["id"] == 1
    nxt = train_next(tmp_path, "j1")
    assert Path(nxt["path"]).is_file()
    adv = train_advance(tmp_path, "j1")
    assert adv["stage"]["id"] == 2


def test_story_compose(tmp_path: Path):
    (tmp_path / "jobs" / "j1").mkdir(parents=True)
    (tmp_path / "jobs" / "j1" / "jd.json").write_text(
        json.dumps({"keywords": ["rag", "llm", "python"], "hard_requirements": ["RAG latency"]}),
        encoding="utf-8",
    )
    a1 = upsert_from_answer(
        tmp_path,
        job_id="j1",
        turn=1,
        answer="I cut RAG latency by forty percent with Python caching and ANN index tuning across production traffic.",
        keywords=["rag", "python"],
        gate_ok=True,
    )
    a2 = upsert_from_answer(
        tmp_path,
        job_id="j1",
        turn=2,
        answer="I led the LLM evaluation harness ownership end-to-end including offline metrics and human preference loops.",
        keywords=["llm"],
        gate_ok=True,
    )
    assert a1 and a2
    out = compose_stories(tmp_path, "j1", limit=3)
    assert out["combo"]
    assert Path(out["path"]).is_file()


def test_comp_lookup():
    out = lookup_comp(title="ML Platform", location="Shanghai")
    assert out["hits"]
    assert out["disclaimer"].startswith("local_")


def test_pipeline_board(tmp_path: Path):
    data = pipeline_board(tmp_path)
    text = format_pipeline_board(data)
    assert "Pipeline Board" in text


def test_resume_pick(tmp_path: Path):
    ev = tmp_path / "evidence"
    ev.mkdir(parents=True)
    (ev / "e1.md").write_text(
        "# RAG work\n\n- **id**: e1\n- **skills**: rag, python\n\n## Actions\nbuilt cache\n\n## Metrics\nP99 -40%\n",
        encoding="utf-8",
    )
    (tmp_path / "jobs" / "j1").mkdir(parents=True)
    (tmp_path / "jobs" / "j1" / "jd.json").write_text(
        json.dumps({"keywords": ["rag"]}), encoding="utf-8"
    )
    items = list_pickable_bullets(tmp_path, "j1")
    assert items
    out = apply_picks(tmp_path, [items[0]["pick_id"]], job_id="j1", name="Test")
    assert out["picked"] == 1
    assert Path(out["path"]).is_file()


def test_experience_complete():
    bare = {"id": "x", "topic": "behavioral", "q": "讲一次冲突"}
    done = complete_answer(bare)
    assert done["completed"] is True
    assert done["answer_points"]
    hits = complete_experience(query="RAG", limit=3)
    assert hits
