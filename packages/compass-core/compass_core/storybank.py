"""STAR storybank from evidence (compas.txt P1 / interview-coach-skill)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .evidence import load_evidence

_METRIC_RE = re.compile(
    r"(\d+\s*%|\d+\s*(ms|s|x|倍|天|周|月)|p\d{2}|提升|下降|降低|减少|增长)",
    re.I,
)


def _strength(text: str, skills: list[str]) -> int:
    score = 2
    if _METRIC_RE.search(text or ""):
        score += 2
    if skills:
        score += 1
    if len(text or "") > 120:
        score += 1
    return max(1, min(5, score))


def rebuild_storybank(root: Path) -> dict:
    root = Path(root)
    items = []
    for ev in load_evidence(root):
        blob = ev.searchable_text() if hasattr(ev, "searchable_text") else str(ev)
        title = getattr(ev, "title", "") or ev.id
        skills = list(getattr(ev, "skills", None) or [])
        metrics_raw = getattr(ev, "metrics", "") or ""
        if isinstance(metrics_raw, list):
            metrics = [str(m) for m in metrics_raw]
        else:
            metrics = [m.strip() for m in str(metrics_raw).splitlines() if m.strip()][:4]
        situation = f"背景：围绕「{title}」相关交付。"
        task = "目标：完成可验证交付并留下指标。"
        action = (blob or "")[:400] or "（补充 Action：你具体做了什么）"
        result = (
            "；".join(metrics)
            if metrics
            else ("含可量化结果" if _METRIC_RE.search(blob) else "（补充 Result + 指标或 UNVERIFIED）")
        )
        # STAR+R (career-ops Interview Story Bank): short reflection for reuse
        reflection = (
            f"复用提示：用「{title}」回答行为题时，先对齐 JD 关键词 "
            f"{', '.join(skills[:3]) or '相关技能'}，再讲指标；承认团队边界，不夸大 Owner。"
        )
        story = {
            "id": f"story_{ev.id}",
            "evidence_ids": [ev.id],
            "title": title,
            "skills": skills,
            "strength": _strength(blob, skills),
            "star": {
                "situation": situation,
                "task": task,
                "action": action,
                "result": result,
                "reflection": reflection,
            },
        }
        items.append(story)
    items.sort(key=lambda s: (-int(s["strength"]), s["id"]))
    out_dir = root / "storybank"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = {"version": 1, "count": len(items), "items": items}
    (out_dir / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return index


def load_storybank(root: Path) -> dict:
    path = Path(root) / "storybank" / "index.json"
    if not path.is_file():
        return {"version": 1, "count": 0, "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def top_stories(root: Path, *, limit: int = 5, skills: list[str] | None = None) -> list[dict]:
    bank = load_storybank(root)
    items = list(bank.get("items") or [])
    if skills:
        sk = {s.lower() for s in skills}
        scored = []
        for it in items:
            overlap = len(sk & {x.lower() for x in (it.get("skills") or [])})
            scored.append((overlap, int(it.get("strength") or 0), it))
        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [t[2] for t in scored[:limit]]
    return items[:limit]
