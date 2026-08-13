from __future__ import annotations

import json
from pathlib import Path

from compass_core.questions import infer_topics, load_bank, search_questions, validate_record


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


def test_search_questions_filters_pack_and_difficulty():
    bank = [
        validate_record({"id": "a", "q": "What is a Transformer encoder?", "pack": "cv-llm", "difficulty": "senior", "tags": ["transformer"]}),
        validate_record({"id": "b", "q": "What is a Transformer encoder?", "pack": "nlp", "difficulty": "junior", "tags": ["transformer"]}),
    ]
    hits = search_questions(
        "transformer",
        bank=bank,
        pack="cv-llm",
        difficulty="senior",
        limit=10,
    )
    assert [h["id"] for h in hits] == ["a"]


def test_search_questions_filters_company():
    bank = [
        validate_record({"id": "a", "q": "System design question", "company": ["Google", "Alphabet"], "tags": ["design"]}),
        validate_record({"id": "b", "q": "System design question", "company": ["Meta"], "tags": ["design"]}),
    ]
    hits = search_questions("design", bank=bank, company="Google", limit=10)
    assert [h["id"] for h in hits] == ["a"]


def test_search_questions_filters_position():
    bank = [
        validate_record({"id": "a", "q": "ML fundamentals", "position": "MLE", "tags": ["ml"]}),
        validate_record({"id": "b", "q": "ML fundamentals", "position": "SWE", "tags": ["ml"]}),
    ]
    hits = search_questions("ml", bank=bank, position="mle", limit=10)
    assert [h["id"] for h in hits] == ["a"]


def test_search_questions_filters_round():
    bank = [
        validate_record({"id": "a", "q": "Coding round question", "round": "onsite", "tags": ["coding"]}),
        validate_record({"id": "b", "q": "Coding round question", "round": "phone", "tags": ["coding"]}),
    ]
    hits = search_questions("coding", bank=bank, round="onsite", limit=10)
    assert [h["id"] for h in hits] == ["a"]


def test_search_questions_topics_boost_only_without_pack():
    bank = [
        validate_record({"id": "a", "q": "Explain BERT tokenizer?", "topic": "nlp", "tags": ["bert"]}),
        validate_record({"id": "b", "q": "Explain BERT tokenizer?", "topic": "cv", "tags": ["bert"]}),
    ]
    hits_no_topic = search_questions("bert", bank=bank, limit=10)
    hits_with_topic = search_questions("bert", bank=bank, topics=["cv"], limit=10)
    assert {h["id"] for h in hits_no_topic} == {"a", "b"}
    assert {h["id"] for h in hits_with_topic} == {"a", "b"}
    assert hits_with_topic[0]["id"] == "b"


def test_search_questions_topics_boost_only_with_pack():
    bank = [
        validate_record({"id": "a", "q": "Explain BERT?", "topic": "nlp", "pack": "nlp-pack", "tags": ["bert"]}),
        validate_record({"id": "b", "q": "Explain BERT?", "topic": "cv", "pack": "cv-pack", "tags": ["bert"]}),
    ]
    hits = search_questions("bert", bank=bank, pack="nlp-pack", topics=["cv"], limit=10)
    assert [h["id"] for h in hits] == ["a"]


def test_infer_topics_cv_mapping():
    assert "cv" in infer_topics(["yolo object detection 分割"])


def test_infer_topics_nlp_mapping():
    assert "nlp" in infer_topics(["bert tokenizer 预训练 词向量"])


def test_infer_topics_ml_mapping():
    assert "ml" in infer_topics(["gradient descent batchnorm cnn"])


def test_infer_topics_algorithms_extended_keys():
    assert "algorithms" in infer_topics(["动态规划 链表"])
    assert "algorithms" in infer_topics(["回溯 leetcode"])


import pytest
from compass_core.import_questions import BLOCKED_SOURCES, import_questions


FIXTURE_Q = Path(__file__).resolve().parent / "fixtures" / "questions" / "local_sample.jsonl"


def test_import_local_jsonl(tmp_path: Path):
    out = import_questions(tmp_path, source="local", file=FIXTURE_Q, rebuild_index=False)
    assert out["ok"] is True
    assert out["count"] >= 1
    path = Path(out["path"])
    assert path.is_file()
    bank = load_bank(tmp_path)
    assert any(r["id"] == "imp_fix_001" for r in bank)


def test_import_blocks_unlicensed_voice(tmp_path: Path):
    with pytest.raises(ValueError) as ei:
        import_questions(tmp_path, source="voice-interview")
    assert "curated-bigtech" in str(ei.value)
    assert "voice-interview" in BLOCKED_SOURCES
