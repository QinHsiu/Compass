"""Local anonymized interview-experience bank (compas / clover-style 面经)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_BANK_PATH = Path(__file__).resolve().parent / "assets" / "questions" / "experience_bank.jsonl"


def load_experience_bank(root: Path | None = None) -> list[dict]:
    items = list(_load_bundled())
    if root:
        extra = Path(root) / "experiences"
        if extra.is_dir():
            for p in sorted(extra.glob("*.jsonl")):
                for ln in p.read_text(encoding="utf-8").splitlines():
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        items.append(json.loads(ln))
                    except json.JSONDecodeError:
                        continue
    return items


@lru_cache(maxsize=1)
def _load_bundled() -> tuple:
    if not _BANK_PATH.is_file():
        return tuple()
    items = []
    for ln in _BANK_PATH.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            items.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return tuple(items)


def search_experience(
    query: str | None = None,
    *,
    company: str | None = None,
    topic: str | None = None,
    limit: int = 10,
    root: Path | None = None,
) -> list[dict]:
    q = (query or "").strip().lower()
    co = (company or "").strip().lower()
    top = (topic or "").strip().lower()
    hits = []
    for it in load_experience_bank(root):
        blob = " ".join(
            [
                str(it.get("q") or ""),
                str(it.get("topic") or ""),
                " ".join(it.get("tags") or []),
                " ".join(it.get("company") or []),
                str(it.get("level") or ""),
            ]
        ).lower()
        score = 0
        if q and q in blob:
            score += 3
        elif q:
            for tok in q.split():
                if tok and tok in blob:
                    score += 1
        if co and any(co in str(c).lower() for c in (it.get("company") or [])):
            score += 2
        if top and top in blob:
            score += 2
        if not q and not co and not top:
            score = 1
        if score > 0:
            hits.append((score, it))
    hits.sort(key=lambda x: -x[0])
    return [h for _, h in hits[:limit]]


def import_experiences(root: Path, path: str | Path) -> dict:
    """Append user JSONL into content/experiences/imported.jsonl."""
    root = Path(root)
    src = Path(path)
    if not src.is_file():
        return {"error": f"missing {src}"}
    out_dir = root / "experiences"
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "imported.jsonl"
    n = 0
    with dest.open("a", encoding="utf-8") as f:
        for ln in src.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if not row.get("id"):
                row["id"] = f"exp_user_{n+1:04d}"
            if not row.get("q") and row.get("question"):
                row["q"] = row["question"]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    _load_bundled.cache_clear()
    return {"imported": n, "path": str(dest)}


_TOPIC_TEMPLATES = {
    "ml_system": [
        "明确 SLA / P99 目标与流量模型",
        "给出索引/缓存/降级分层，并说明你做过的取舍",
        "用一次事故或压测数字证明有效",
    ],
    "behavioral": [
        "Situation 用业务影响量化开场",
        "突出「我」的决策标准与推动动作",
        "Result + 复盘，避免贬低他人",
    ],
    "llm": [
        "数据/评测/线上归因三层拆开讲",
        "坏例聚类比单一分数更有说服力",
        "说明你如何避免编造未验证效果",
    ],
    "coding": [
        "先澄清约束与复杂度",
        "写出正确性再谈性能",
        "补充测试与可观测点",
    ],
    "offer": [
        "现金 / 权益 / 级别分列",
        "用自填 market_p50 对照，不编造公司带宽",
        "准备 BATNA 与回复时间表",
    ],
    "agent": [
        "工具失败按 schema / 权限 / 超时分层排查",
        "用轨迹回放定位",
        "改动用 gate/评测证明",
    ],
    "system_design": [
        "澄清读写比与一致性要求",
        "画清数据流与失败模式",
        "给出可演进的监控指标",
    ],
    "hr": [
        "动机对齐目标岗关键词",
        "不贬低前东家",
        "用可验证成长叙述收尾",
    ],
}


def complete_answer(item: dict) -> dict:
    """Heuristic standard-answer points (prisma-style autocomplete, local templates)."""
    out = dict(item)
    existing = out.get("answer_points") or out.get("hint") or []
    if isinstance(existing, str):
        existing = [existing] if existing.strip() else []
    if existing:
        out["answer_points"] = list(existing)
        out["completed"] = False
        return out
    topic = str(out.get("topic") or "").lower()
    tags = [str(t).lower() for t in (out.get("tags") or [])]
    points = list(_TOPIC_TEMPLATES.get(topic) or [])
    if not points:
        for t in tags:
            if t in _TOPIC_TEMPLATES:
                points = list(_TOPIC_TEMPLATES[t])
                break
    if not points:
        points = [
            "先对齐问题关键词，再给 STAR 骨架",
            "补一个可验证 Result / evidence_id",
            "主动说明缺口，不编造经历",
        ]
    # personalize with question nouns
    q = str(out.get("q") or "")
    if q:
        points = [f"围绕「{q[:36]}」：" + points[0]] + points[1:]
    out["answer_points"] = points
    out["completed"] = True
    out["complete_source"] = "template"
    return out


def complete_experience(
    query: str | None = None,
    *,
    company: str | None = None,
    topic: str | None = None,
    limit: int = 10,
    id: str | None = None,
    root: Path | None = None,
) -> list[dict]:
    if id:
        hits = [it for it in load_experience_bank(root) if it.get("id") == id]
    else:
        hits = search_experience(query, company=company, topic=topic, limit=limit, root=root)
    return [complete_answer(h) for h in hits]
