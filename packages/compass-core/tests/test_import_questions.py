from __future__ import annotations

import json
from pathlib import Path

from compass_core.questions import load_bank, validate_record


def test_validate_record_fills_defaults():
    row = validate_record({"id": "qb_t_1", "q": "What is attention?"})
    assert row["id"] == "qb_t_1"
    assert row["q"] == "What is attention?"
    assert row["difficulty"] == "mid"
    assert row["tags"] == []
    assert row["topic"] == "general"
    assert row["source"]
    assert row["pack"] == "bank"
    assert row["answer_kind"] == "none"
    assert "skill_tags" in row
    assert "persona_affinity" in row


def test_validate_record_maps_cn_difficulty():
    row = validate_record({"id": "x", "q": "q", "difficulty": "高级"})
    assert row["difficulty"] == "senior"
    row2 = validate_record({"id": "y", "q": "q", "difficulty": "初级"})
    assert row2["difficulty"] == "junior"


def test_load_bank_reads_imported_dir(tmp_path: Path):
    d = tmp_path / "questions" / "imported"
    d.mkdir(parents=True)
    rec = {
        "id": "imp_local_001",
        "q": "Explain Kafka ISR.",
        "topic": "backend",
        "tags": ["kafka"],
        "difficulty": "mid",
        "pack": "local",
        "source": "user extra",
    }
    (d / "local.jsonl").write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    bank = load_bank(tmp_path)
    ids = {r["id"] for r in bank}
    assert "imp_local_001" in ids
