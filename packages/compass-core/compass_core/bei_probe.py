"""BEI/STAR completeness probe (interview-skills Round 7).

Rule-based: missing Situation/Task, Result without metrics, collective-only 'we'.
"""

from __future__ import annotations

import re

_METRIC_RE = re.compile(
    r"(\d+\s*%|\d+\s*(ms|s|x|倍|天|周|月)|p\d{2}|提升|下降|降低|减少|增长|从.+到)",
    re.I,
)
_SIT_HINTS = ("当时", "背景", "场景", "situation", "context", "when", "面临", "问题是")
_TASK_HINTS = ("负责", "目标", "task", "我的任务", "需要我")
_ACTION_HINTS = ("我", "采取", "实现", "action", "做了", "引入", "改了")
_RESULT_HINTS = ("结果", "最终", "result", "outcome", "效果", "指标")


def probe_star(answer: str) -> dict:
    text = (answer or "").strip()
    if not text:
        return {
            "ok": False,
            "missing": ["situation", "task", "action", "result"],
            "hints": ["回答为空：请用 STAR 完整复述并引用 evidence_id。"],
            "structure_score": 1,
        }
    lower = text.lower()
    missing: list[str] = []
    hints: list[str] = []

    has_s = any(h in lower or h in text for h in _SIT_HINTS) or len(text) > 80
    has_t = any(h in lower or h in text for h in _TASK_HINTS)
    has_a = any(h in lower or h in text for h in _ACTION_HINTS)
    has_r = any(h in lower or h in text for h in _RESULT_HINTS) or bool(_METRIC_RE.search(text))

    # Collective-only: many 「我们」 few 「我」
    we_n = len(re.findall(r"我们|we\b", text, flags=re.I))
    i_n = len(re.findall(r"我(?!们)|i\b", text, flags=re.I))
    if we_n >= 2 and i_n == 0:
        missing.append("ownership")
        hints.append("多用「我」说明个人贡献，避免全程「我们」。")

    if not has_s and not has_t:
        missing.append("situation")
        hints.append("补充 Situation/Task：当时背景与你的目标是什么？")
    elif not has_t:
        missing.append("task")
        hints.append("补充 Task：你具体负责什么？")

    if not has_a:
        missing.append("action")
        hints.append("补充 Action：你采取了哪些具体步骤？")

    if not has_r:
        missing.append("result")
        hints.append("补充 Result：给出可量化结果，或标 UNVERIFIED。")
    elif not _METRIC_RE.search(text):
        missing.append("metrics")
        hints.append("Result 缺指标：请补数字/%/时延，并 cite evidence_id。")

    # Structure score 1-5
    filled = 4 - sum(1 for m in ("situation", "task", "action", "result") if m in missing)
    score = max(1, min(5, 1 + filled))
    if "ownership" in missing:
        score = max(1, score - 1)
    if "metrics" in missing:
        score = max(1, score - 1)

    return {
        "ok": len(missing) == 0,
        "missing": missing,
        "hints": hints,
        "structure_score": score,
    }


def followup_from_probe(probe: dict) -> str | None:
    hints = probe.get("hints") or []
    if not hints:
        return None
    return hints[0]
