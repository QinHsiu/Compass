"""Searchable interview question bank with open-source attribution + i18n."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets" / "questions"
BANK_PATH = ASSETS / "bank.jsonl"
ZH_PATH = ASSETS / "i18n_zh.json"

DIFFICULTIES = ("junior", "mid", "senior")
_DIFF_MAP = {
    "junior": "junior",
    "mid": "mid",
    "senior": "senior",
    "初级": "junior",
    "中级": "mid",
    "高级": "senior",
    "easy": "junior",
    "medium": "mid",
    "hard": "senior",
}
PACK_ASSET_FILES = (
    "bank.jsonl",
    "llm_agent.jsonl",
    "cv_llm.jsonl",
    "nlp.jsonl",
    "mldl.jsonl",
    "algo.jsonl",
)


def validate_record(row: dict) -> dict:
    """Normalize a bank row. Unknown keys are kept."""
    out = dict(row or {})
    out["id"] = str(out.get("id") or "").strip() or "qb_anon"
    out["q"] = str(out.get("q") or out.get("question") or "").strip()
    if "difficulty" not in row and row.get("level"):
        mapped = _DIFF_MAP.get(str(row["level"]).lower())
        if mapped:
            out["difficulty"] = mapped
    diff = str(out.get("difficulty") or "mid").strip().lower()
    out["difficulty"] = _DIFF_MAP.get(diff, _DIFF_MAP.get(str(out.get("difficulty") or "").strip(), "mid"))
    tags = out.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    out["tags"] = list(tags)
    out["topic"] = str(out.get("topic") or "general")
    out["source"] = str(out.get("source") or "Compass curated")
    out["source_url"] = str(out.get("source_url") or "")
    out["pack"] = str(out.get("pack") or "bank")
    skills = out.get("skill_tags") or list(out["tags"])
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(",") if s.strip()]
    out["skill_tags"] = list(skills)
    aff = out.get("persona_affinity") or []
    if isinstance(aff, str):
        aff = [aff]
    out["persona_affinity"] = [str(a) for a in aff]
    companies = out.get("company") or []
    if isinstance(companies, str):
        companies = [companies]
    out["company"] = [str(c) for c in companies]
    out["position"] = str(out.get("position") or "")
    out["round"] = str(out.get("round") or "")
    out["answer"] = str(out.get("answer") or "")
    out["answer_kind"] = str(out.get("answer_kind") or ("outline" if out["answer"] else "none"))
    out["starter_code"] = str(out.get("starter_code") or "")
    out["animation_url"] = str(out.get("animation_url") or "")
    return out


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9\u4e00-\u9fff+#.]{2,}", (text or "").lower()))


def load_bank(extra_root: Path | None = None) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    def _add_file(path: Path) -> None:
        if not path.is_file():
            return
        for ln in path.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                rec = validate_record(json.loads(ln))
            except json.JSONDecodeError:
                continue
            qid = rec.get("id") or ""
            if qid in seen:
                continue
            seen.add(qid)
            rows.append(rec)

    for name in PACK_ASSET_FILES:
        _add_file(ASSETS / name)
    if extra_root:
        qdir = Path(extra_root) / "questions"
        _add_file(qdir / "extra.jsonl")
        _add_file(qdir / "llm_agent.jsonl")
        imported = qdir / "imported"
        if imported.is_dir():
            for p in sorted(imported.glob("*.jsonl")):
                _add_file(p)
    return rows


@lru_cache(maxsize=1)
def _zh_map() -> dict[str, str]:
    if ZH_PATH.is_file():
        return json.loads(ZH_PATH.read_text(encoding="utf-8"))
    return {}


def is_mostly_english(text: str) -> bool:
    s = (text or "").strip()
    if not s or s.startswith("<"):
        return False
    letters = re.findall(r"[A-Za-z]", s)
    cjk = re.findall(r"[\u4e00-\u9fff]", s)
    if not letters:
        return False
    return len(letters) >= max(8, len(cjk) * 2)


def chinese_for(hit: dict) -> str:
    """Return Chinese description for a bank hit (prefer curated map)."""
    if hit.get("q_zh"):
        return str(hit["q_zh"])
    qid = hit.get("id") or ""
    mapped = _zh_map().get(qid)
    if mapped:
        return mapped
    q = hit.get("q") or ""
    if not is_mostly_english(q):
        return q
    # light heuristic fallback
    rules = [
        ("Explain the difference between ", "请解释二者区别："),
        ("Explain ", "请解释："),
        ("How do you ", "你如何"),
        ("How does ", "如何理解："),
        ("How would you ", "你会如何"),
        ("What is the difference between ", "有何区别："),
        ("What is ", "什么是"),
        ("What are ", "什么是"),
        ("Describe ", "请描述："),
        ("Design ", "请设计："),
        ("Compare ", "请比较："),
        ("Tell me about ", "请讲述："),
        ("Difference between ", "区别是什么："),
    ]
    out = q
    for a, b in rules:
        if out.startswith(a):
            out = b + out[len(a) :]
            break
    return "（译文）" + out.replace("?", "？")


def enrich_hit(hit: dict, lang: str = "zh") -> dict:
    """
    Attach bilingual fields.
    - q: original
    - q_zh: Chinese description (always filled for English stems)
    - q_display: preferred line for UI language
    - q_secondary: companion line (EN↔ZH)
    """
    row = dict(hit)
    q = row.get("q") or ""
    zh = chinese_for(row)
    row["q_zh"] = zh
    row["q_en"] = q if is_mostly_english(q) else row.get("q_en") or q
    lang = (lang or "zh").lower()
    if lang.startswith("zh"):
        row["q_display"] = zh if zh else q
        row["q_secondary"] = q if is_mostly_english(q) and zh != q else ""
    else:
        # en / ja / es: keep original primary; if English, still attach Chinese note
        row["q_display"] = q
        row["q_secondary"] = zh if is_mostly_english(q) and zh and zh != q else ""
    return row


def enrich_hits(hits: list[dict], lang: str = "zh") -> list[dict]:
    return [enrich_hit(h, lang=lang) for h in hits]


def search_questions(
    query: str,
    *,
    keywords: list[str] | None = None,
    topics: list[str] | None = None,
    limit: int = 12,
    bank: list[dict] | None = None,
    extra_root: Path | None = None,
    lang: str = "zh",
    company: str | None = None,
    difficulty: str | None = None,
    pack: str | None = None,
    position: str | None = None,
    round: str | None = None,
) -> list[dict]:
    """Token overlap retrieval; returns questions with score + bilingual fields."""
    items = bank if bank is not None else load_bank(extra_root)
    q_tokens = _tokenize(query)
    for kw in keywords or []:
        q_tokens |= _tokenize(kw)
    topic_set = {t.lower() for t in (topics or [])}

    def _ok(it: dict) -> bool:
        if pack and str(it.get("pack") or "") != pack:
            return False
        if difficulty and str(it.get("difficulty") or "") != difficulty:
            return False
        if topic_set and (it.get("topic") or "").lower() not in topic_set and not (
            set(it.get("tags") or []) & topic_set
        ):
            # topics are boost-only (never a hard filter), even when pack is set
            pass
        if company:
            blob = " ".join(str(c).lower() for c in (it.get("company") or []))
            if company.lower() not in blob:
                return False
        if position and str(it.get("position") or "").lower() != position.lower():
            return False
        if round and str(it.get("round") or "").lower() != round.lower():
            return False
        return True

    items = [it for it in items if _ok(it)]

    scored: list[tuple[float, dict]] = []
    for it in items:
        text = " ".join(
            [
                it.get("q") or "",
                it.get("q_zh") or "",
                it.get("topic") or "",
                " ".join(it.get("tags") or []),
                it.get("pack") or "",
                " ".join(str(c) for c in (it.get("company") or [])),
                " ".join(it.get("skill_tags") or []),
            ]
        )
        tokens = _tokenize(text)
        overlap = len(q_tokens & tokens)
        score = float(overlap)
        if topic_set and (it.get("topic") or "").lower() in topic_set:
            score += 2.0
        for t in it.get("tags") or []:
            if t.lower() in q_tokens:
                score += 1.5
        if score > 0:
            scored.append((score, it))
    scored.sort(key=lambda x: x[0], reverse=True)
    out = []
    for sc, it in scored[:limit]:
        row = enrich_hit(it, lang=lang)
        row["score"] = sc
        out.append(row)
    return out


def infer_topics(keywords: list[str]) -> list[str]:
    blob = " ".join(keywords).lower()
    topics = []
    mapping = [
        ("python", ["python", "django", "fastapi"]),
        ("java", ["java", "spring", "jvm", "kafka"]),
        ("frontend", ["react", "vue", "javascript", "typescript", "css", "frontend"]),
        ("mlops", ["ml", "llm", "rag", "feature store", "pytorch", "spark", "mlops"]),
        ("llm", ["llm", "gpt", "transformer", "prompt", "embedding", "finetune", "lora"]),
        ("agent", ["agent", "react", "tool", "langchain", "autogen", "mcp", "multi-agent"]),
        ("devops", ["kubernetes", "k8s", "docker", "devops", "sre", "linux", "redis"]),
        ("system-design", ["distributed", "scale", "architecture"]),
        ("behavioral", ["ownership", "leadership"]),
        ("cv", ["cv", "computer vision", "yolo", "diffusion", "clip", "vit", "检测", "分割"]),
        ("nlp", ["nlp", "bert", "ner", "tokenizer", "预训练", "词向量"]),
        ("ml", ["gradient", "正则", "cnn", "rnn", "optimizer", "batchnorm"]),
        ("algorithms", ["algorithm", "sql", "leetcode", "链表", "动态规划", "回溯"]),
    ]
    for topic, keys in mapping:
        if any(k in blob for k in keys):
            topics.append(topic)
    if not topics:
        topics = ["behavioral", "system-design"]
    return topics


_SECTION_TITLE = {
    "zh": "### 检索到的题库题目",
    "en": "### Retrieved bank questions",
    "ja": "### 検索された問題集",
    "es": "### Preguntas del banco",
}

_EMPTY = {
    "zh": "_暂无题库命中 — 请以岗位深挖题为主。_\n",
    "en": "_No bank hits — rely on job deep-dive questions._\n",
    "ja": "_問題集ヒットなし — 求人深掘り問題を中心に。_\n",
    "es": "_Sin aciertos — usa las preguntas del puesto._\n",
}


def format_bank_section(hits: list[dict], lang: str = "zh") -> str:
    lang = (lang or "zh").lower()[:2]
    if not hits:
        return _EMPTY.get(lang, _EMPTY["en"])
    lines = []
    for i, h in enumerate(enrich_hits(hits, lang=lang), 1):
        src = h.get("source") or "unknown"
        url = h.get("source_url") or ""
        cite = f" — {src}" + (f" ({url})" if url else "")
        primary = h.get("q_display") or h.get("q") or ""
        secondary = h.get("q_secondary") or ""
        head = (
            f"{i}. **[{h.get('id')}]** ({h.get('topic')}/{h.get('difficulty')}) "
            f"{primary}{cite}"
        )
        lines.append(head)
        if secondary:
            label = {
                "zh": "原文",
                "en": "中文",
                "ja": "中国語",
                "es": "中文",
            }.get(lang, "中文")
            # When UI is zh, secondary is English original; otherwise secondary is Chinese.
            if lang == "zh":
                label = "英文"
            lines.append(f"   - *{label}*: {secondary}")
    return "\n".join(lines) + "\n"


def bank_section_title(lang: str = "zh") -> str:
    return _SECTION_TITLE.get((lang or "zh")[:2], _SECTION_TITLE["en"])
