"""Practice vs real interview outcome calibration (compas v0.9 deepened)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .scorecard import load_scorecard

VALID_OUTCOMES = ("pass", "fail", "offer", "ghosted", "withdrawn")
APPLY_BANDS = {"strong", "plausible"}
SKIP_BANDS = {"skip"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def calibrate_path(root: Path) -> Path:
    return Path(root) / "calibrations" / "outcomes.json"


def load_outcomes(root: Path) -> dict:
    path = calibrate_path(root)
    if not path.is_file():
        return {"version": 1, "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_outcomes(root: Path, data: dict) -> Path:
    path = calibrate_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_match(root: Path, job_id: str) -> dict:
    p = Path(root) / "jobs" / job_id / "match.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _load_actions(root: Path, job_id: str) -> list[dict]:
    p = Path(root) / "diagnoses" / job_id / "actions.json"
    if p.is_file():
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else list(data.get("actions") or [])
    return []


def build_narrative_hits(root: Path, job_id: str, scorecard: dict | None = None) -> list[dict]:
    """Map diagnose narrative/evidence P0 items to practice weak dims / ask counts."""
    sc = scorecard or load_scorecard(root, job_id)
    answers = sc.get("answers") or []
    actions = _load_actions(root, job_id)
    hits: list[dict] = []

    # Low structure / substance counts as narrative weakness probes
    low_struct = sum(1 for a in answers if float((a.get("scores") or {}).get("structure") or 5) <= 2)
    low_cred = sum(1 for a in answers if float((a.get("scores") or {}).get("credibility") or 5) <= 2)
    if low_struct:
        hits.append(
            {
                "kind": "structure",
                "times": low_struct,
                "message": f"叙事结构弱点在练习中被追问/打低分 {low_struct} 次（structure≤2）",
            }
        )
    if low_cred:
        hits.append(
            {
                "kind": "credibility",
                "times": low_cred,
                "message": f"证据可信度弱点出现 {low_cred} 次（credibility≤2）",
            }
        )

    narrative_actions = [
        a for a in actions if (a.get("quadrant") in ("narrative", "evidence") and a.get("priority") == "P0")
    ]
    for a in narrative_actions[:5]:
        what = str(a.get("what") or "")[:80]
        # count answers whose question/notes mention tokens from action
        tokens = [t for t in what.replace("：", " ").replace(":", " ").split() if len(t) >= 2][:4]
        times = 0
        if tokens:
            for ans in answers:
                blob = f"{ans.get('question') or ''} {ans.get('notes') or ''}"
                if any(t in blob for t in tokens):
                    times += 1
        hits.append(
            {
                "kind": "diagnose_p0",
                "quadrant": a.get("quadrant"),
                "times": times,
                "what": what,
                "message": (
                    f"缺口罗盘 P0（{a.get('quadrant')}）「{what}」"
                    + (f"在练习问题中命中 {times} 次" if times else "在练习中未直接命中（建议针对性追问）")
                ),
            }
        )
    return hits


def predicted_apply(match: dict) -> str:
    """Return 'apply' | 'skip' | 'explore' from match recommendation/grade."""
    band = (match.get("match_explain") or {}).get("recommendation") or ""
    letter = (match.get("grade") or {}).get("letter") or ""
    if band in SKIP_BANDS or letter == "F":
        return "skip"
    if band in APPLY_BANDS or letter in ("A", "B"):
        return "apply"
    return "explore"


def record_outcome(root: Path, job_id: str, outcome: str, *, note: str = "") -> dict:
    outcome = (outcome or "").lower().strip()
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {VALID_OUTCOMES}")
    sc = load_scorecard(root, job_id)
    agg = (sc.get("aggregate") or {}).get("scores") or {}
    practice_jd_fit = float(agg.get("jd_fit") or 0)
    practice_avg = 0.0
    if agg:
        practice_avg = round(sum(float(v) for v in agg.values()) / max(len(agg), 1), 2)
    match = _load_match(root, job_id)
    pred = predicted_apply(match)
    narrative_hits = build_narrative_hits(root, job_id, sc)
    item = {
        "job_id": job_id,
        "outcome": outcome,
        "note": note,
        "recorded_at": _utcnow(),
        "predicted": pred,
        "recommendation": (match.get("match_explain") or {}).get("recommendation"),
        "score_100": (match.get("grade") or {}).get("score_100"),
        "narrative_hits": narrative_hits,
        "practice": {
            "answer_count": (sc.get("aggregate") or {}).get("answer_count") or len(sc.get("answers") or []),
            "jd_fit": practice_jd_fit,
            "avg_score": practice_avg,
            "gate_pass_rate": (sc.get("aggregate") or {}).get("gate_pass_rate"),
        },
    }
    data = load_outcomes(root)
    items = [x for x in (data.get("items") or []) if x.get("job_id") != job_id]
    items.append(item)
    data["items"] = items
    save_outcomes(root, data)
    sc["real_outcome"] = outcome
    sc["real_outcome_at"] = item["recorded_at"]
    from .scorecard import save_scorecard

    save_scorecard(root, job_id, sc)
    return item


def _band_accuracy(items: list[dict]) -> dict:
    """Compare predicted apply/skip vs real pass/fail/offer."""
    pos = {"pass", "offer"}
    neg = {"fail", "ghosted"}
    correct = 0
    considered = 0
    for it in items:
        pred = it.get("predicted") or "explore"
        out = it.get("outcome")
        if pred == "explore":
            continue
        if out not in pos and out not in neg:
            continue
        considered += 1
        if pred == "apply" and out in pos:
            correct += 1
        elif pred == "skip" and out in neg:
            correct += 1
    rate = round(correct / considered, 3) if considered else None
    return {"correct": correct, "considered": considered, "accuracy": rate}


def calibration_report(root: Path) -> dict:
    data = load_outcomes(root)
    items = list(data.get("items") or [])
    n = len(items)
    pos = {"pass", "offer"}
    high_practice_fail = []
    low_practice_pass = []
    for it in items:
        jd = float((it.get("practice") or {}).get("jd_fit") or 0)
        out = it.get("outcome")
        if jd >= 4.0 and out in ("fail", "ghosted"):
            high_practice_fail.append(it["job_id"])
        if jd <= 2.5 and out in pos:
            low_practice_pass.append(it["job_id"])

    drift_notes = []
    if n >= 3:
        if len(high_practice_fail) >= 2:
            drift_notes.append(
                "练习 jd_fit≥4 但仍失败偏多：可能评分偏松或真实面试压力不足，加强 challenging persona。"
            )
        if len(low_practice_pass) >= 2:
            drift_notes.append(
                "练习分偏低却通过：可能练习题过难或真实流程偏行为面，补充 HR persona 与故事库。"
            )
        if not drift_notes:
            drift_notes.append("样本≥3，暂未检测到显著评分漂移。")
    else:
        drift_notes.append(f"样本不足（{n}/3）：继续记录 real_outcome 后再校准。")

    acc = _band_accuracy(items)
    all_hits = []
    for it in items:
        for h in it.get("narrative_hits") or []:
            all_hits.append({"job_id": it.get("job_id"), **h})

    report = {
        "sample_size": n,
        "items": items,
        "high_practice_fail": high_practice_fail,
        "low_practice_pass": low_practice_pass,
        "drift_notes": drift_notes,
        "band_accuracy": acc,
        "narrative_hits": all_hits[:40],
        "ready": n >= 3,
    }
    out_dir = Path(root) / "calibrations"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = ["# Calibration report", "", f"sample_size={n}", "", "## Drift notes", ""]
    md.extend(f"- {n_}" for n_ in drift_notes)
    md.append("")
    md.append("## Band accuracy (apply/skip vs real)")
    md.append("")
    md.append(
        f"- accuracy={acc.get('accuracy')} ({acc.get('correct')}/{acc.get('considered')} considered)"
    )
    md.append("")
    md.append("## Narrative hits")
    md.append("")
    for h in all_hits[:20]:
        md.append(f"- `{h.get('job_id')}`: {h.get('message')}")
    if not all_hits:
        md.append("- _(none yet)_")
    md.append("")
    md.append("## Outcomes")
    md.append("")
    for it in items:
        p = it.get("practice") or {}
        md.append(
            f"- `{it.get('job_id')}` → **{it.get('outcome')}** "
            f"(pred={it.get('predicted')}, jd_fit={p.get('jd_fit')}, "
            f"score_100={it.get('score_100')})"
        )
    (out_dir / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report


def calibrate_summary_for_job(root: Path, job_id: str) -> dict:
    """Lightweight summary after diagnose --calibrate."""
    hits = build_narrative_hits(root, job_id)
    data = load_outcomes(root)
    prior = next((x for x in (data.get("items") or []) if x.get("job_id") == job_id), None)
    return {
        "job_id": job_id,
        "narrative_hits": hits,
        "prior_outcome": prior,
        "hint": "记录真实结果：calibrate record --job-id ... --outcome pass|fail|offer",
    }
