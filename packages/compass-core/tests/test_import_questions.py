from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass_core.evidence import build_index
from compass_core.questions import (
    bank_search_args,
    infer_topics,
    load_bank,
    search_questions,
    validate_record,
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


def test_bank_search_args_and_lookup():
    args = bank_search_args({"query": "LoRA", "pack": "cv-llm", "difficulty": "mid", "limit": 5})
    assert args["pack"] == "cv-llm"
    assert args["difficulty"] == "mid"
    hits = search_questions(
        args["query"],
        pack=args["pack"],
        difficulty=args["difficulty"],
        limit=args["limit"],
    )
    assert hits
    algo = [r for r in load_bank() if r.get("id") == "qb_algop_001"]
    assert algo and algo[0].get("starter_code")


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


def test_validate_record_accepts_none():
    row = validate_record(None)
    assert isinstance(row, dict)
    assert row["id"] == "qb_anon"
    assert row["difficulty"] == "mid"


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


def test_import_local_missing_file_raises(tmp_path: Path):
    missing = tmp_path / "no_such.jsonl"
    with pytest.raises(ValueError) as ei:
        import_questions(tmp_path, source="local", file=missing)
    assert "file not found" in str(ei.value).lower() or "not found" in str(ei.value).lower()


def test_import_local_skips_malformed_json(tmp_path: Path):
    src = tmp_path / "mixed.jsonl"
    good = json.dumps({"id": "good_1", "q": "Valid question?"}, ensure_ascii=False)
    src.write_text(good + "\n{not valid json\n", encoding="utf-8")
    out = import_questions(tmp_path, source="local", file=src)
    assert out["ok"] is True
    assert out["count"] == 1
    assert out["skipped_malformed"] >= 1
    bank = load_bank(tmp_path)
    assert any(r["id"] == "good_1" for r in bank)


def test_domain_packs_load():
    from compass_core.questions import ASSETS, load_bank

    bank = load_bank()
    packs = {r.get("pack") for r in bank}
    assert "cv-llm" in packs
    assert "nlp" in packs
    assert "mldl" in packs
    cv = [r for r in bank if r.get("pack") == "cv-llm"]
    nlp = [r for r in bank if r.get("pack") == "nlp"]
    mldl = [r for r in bank if r.get("pack") == "mldl"]
    assert len(cv) >= 12
    assert len(nlp) >= 10
    assert len(mldl) >= 10
    assert any("transformer" in (r.get("tags") or []) for r in cv)
    assert any("diffusion" in (r.get("tags") or []) for r in cv)
    assert any("rlhf" in (r.get("tags") or []) for r in cv)
    assert all(r.get("answer_kind") in ("outline", "none") for r in cv + nlp + mldl)
    assert (ASSETS / "cv_llm.jsonl").is_file()


def test_search_cv_llm_transformer():
    hits = search_questions("transformer attention diffusion", pack="cv-llm", limit=5)
    assert hits
    assert all(h.get("pack") == "cv-llm" for h in hits)


def test_algo_pack_starter_code():
    bank = [r for r in load_bank() if r.get("pack") == "algo"]
    assert len(bank) >= 10
    topics = {r.get("topic") for r in bank}
    for need in ("array", "linked-list", "tree", "dp", "backtrack"):
        assert need in topics
    coded = [r for r in bank if r.get("starter_code")]
    assert len(coded) >= 5
    assert "def " in coded[0]["starter_code"]


def test_company_pack_baidu_meituan_huawei():
    from compass_core.company_pack import match_company_key, search_company_pack

    assert match_company_key("百度") == "baidu"
    assert match_company_key("美团") == "meituan"
    assert match_company_key("华为云计算") == "huawei"
    assert match_company_key("京东零售") == "jingdong"
    assert match_company_key("滴滴出行") == "didi"
    for co in ("baidu", "meituan", "huawei", "jingdong", "didi"):
        hits = search_company_pack(co, limit=8)
        assert len(hits) >= 2, co
        assert all(hit.get("q") for hit in hits)


from compass_core.evidence import EvidenceItem
from compass_core.question_match import attach_evidence


def test_attach_evidence_by_skill_tags():
    q = validate_record({
        "id": "qb_t_kafka",
        "q": "Explain Kafka ISR.",
        "skill_tags": ["kafka", "replication"],
        "tags": ["kafka"],
    })
    ev = [
        EvidenceItem(id="ev_kafka_incident", title="ISR shrink", skills=["kafka", "java"], actions="fixed ISR"),
        EvidenceItem(id="ev_p99_query", title="SQL", skills=["sql"], actions="index"),
    ]
    out = attach_evidence(q, ev, jd_keywords=["kafka", "golang"])
    assert "ev_kafka_incident" in out["matched_evidence_ids"]
    assert "ev_p99_query" not in out["matched_evidence_ids"]
    assert "kafka" in out["matched_jd_keywords"]
    assert "kafka" in out["skill_overlap"]
    assert out["id"] == "qb_t_kafka"


from compass_core.interview_persona import pick_persona
from compass_core.question_match import rank_for_persona


def test_rank_for_persona_technical_prefers_cvllm():
    hits = [
        validate_record({"id": "h", "q": "Tell me about a conflict", "pack": "bank", "topic": "behavioral", "persona_affinity": ["hr"]}),
        validate_record({"id": "t", "q": "Explain LoRA", "pack": "cv-llm", "tags": ["lora"], "persona_affinity": ["technical"]}),
    ]
    persona = {"persona_id": "technical"}
    ranked = rank_for_persona(hits, persona, limit=2)
    assert ranked[0]["id"] == "t"


def test_build_pack_persona_bank(root: Path):
    from compass_core.interview import build_pack
    from compass_core.match import match_and_save

    text = "公司：ExampleAI\n职位：大模型算法工程师\n必须：Transformer、LLM、PyTorch"
    m = match_and_save(root, text)
    pack = build_pack(root, m.job_id)
    assert pack.get("persona", {}).get("persona_id")
    assert pack.get("persona_bank") is True
    assert isinstance(pack.get("bank_hits"), list)


from compass_core.interview import next_followup


def test_followup_uses_bank_id_and_meta():
    pack = {
        "title": "NLP 算法",
        "gaps": [],
        "keyword_misses": [],
        "evidence": [{"evidence_id": "ev_featstore_latency", "title": "x"}],
        "persona": {"persona_id": "technical"},
        "bank_hits": [
            {"id": "qb_nlp_002", "q": "What does BERT pretrain?", "difficulty": "mid"},
        ],
        "asked_ids": [],
    }
    fu = next_followup(
        pack,
        "我们把 p99 做到 45ms ev_featstore_latency，BERT MLM 预训练后做领域微调",
        gate_ok=True,
        turn=0,
    )
    assert fu["question"]
    assert (fu.get("meta") or {}).get("bank_id") == "qb_nlp_002"


_GOOD_ANSWER = (
    "当时背景是 NLP 预训练项目，我负责 BERT 微调。"
    "我引入 MLM 预训练并做领域微调，最终将 p99 做到 45ms ev_featstore_latency，指标提升 30%。"
)


def test_followup_prefers_unused_bank_id():
    pack = {
        "title": "NLP 算法",
        "gaps": [],
        "keyword_misses": [],
        "evidence": [{"evidence_id": "ev_featstore_latency", "title": "x"}],
        "persona": {"persona_id": "technical"},
        "bank_hits": [
            {"id": "qb_first", "q": "First question?", "difficulty": "mid"},
            {"id": "qb_second", "q": "Second unused question?", "difficulty": "mid"},
        ],
        "asked_ids": ["qb_first"],
    }
    fu = next_followup(pack, _GOOD_ANSWER, gate_ok=True, turn=0)
    assert "Second unused" in fu["question"]
    assert (fu.get("meta") or {}).get("bank_id") == "qb_second"


def test_followup_bank_turn_modulo():
    pack = {
        "title": "NLP 算法",
        "gaps": [],
        "keyword_misses": [],
        "evidence": [{"evidence_id": "ev_featstore_latency", "title": "x"}],
        "persona": {"persona_id": "technical"},
        "bank_hits": [
            {"id": "qb_a", "q": "Question A?", "difficulty": "mid"},
            {"id": "qb_b", "q": "Question B?", "difficulty": "mid"},
        ],
        "asked_ids": [],
    }
    fu = next_followup(pack, _GOOD_ANSWER, gate_ok=True, turn=2)
    assert "Question A?" in fu["question"]
    assert (fu.get("meta") or {}).get("bank_id") == "qb_a"


def test_followup_challenging_senior_prefix():
    pack = {
        "title": "NLP 算法",
        "gaps": [],
        "keyword_misses": [],
        "evidence": [{"evidence_id": "ev_featstore_latency", "title": "x"}],
        "persona": {"persona_id": "challenging"},
        "bank_hits": [
            {"id": "qb_senior", "q": "Hard question?", "difficulty": "senior"},
        ],
        "asked_ids": [],
    }
    fu = next_followup(pack, _GOOD_ANSWER, gate_ok=True, turn=0)
    assert fu["question"].startswith("（高压追问）")
    assert "Hard question?" in fu["question"]


from compass_core.answer_rubric import score_qa_rubric


def test_rubric_outline_boosts_substance():
    q = "Explain LoRA"
    outline = "Freeze W, train BA with rank r. Memory vs full fine-tune."
    weak = score_qa_rubric(q, "我做过模型训练，效果很好。", expected_outline=outline)
    strong = score_qa_rubric(
        q,
        "我们 freeze 原权重 W，只训练低秩 BA，rank r=8，显存比 full fine-tune 低很多。",
        expected_outline=outline,
    )
    assert strong["substance"] >= weak["substance"]


from compass_core.rag import record_to_metadata


def test_rag_metadata_includes_pack():
    row = validate_record({"id": "x", "q": "LoRA?", "pack": "cv-llm", "difficulty": "mid", "company": ["alibaba"], "topic": "llm"})
    meta = record_to_metadata(row)
    assert meta["pack"] == "cv-llm"
    assert meta["difficulty"] == "mid"
    assert "alibaba" in meta["company"]
