"""Practice vs real interview outcome calibration (compas.txt light P2)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .scorecard import load_scorecard

VALID_OUTCOMES = ("pass", "fail", "offer", "ghosted", "withdrawn")


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
    item = {
        "job_id": job_id,
        "outcome": outcome,
        "note": note,
        "recorded_at": _utcnow(),
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
    # also stamp scorecard
    sc["real_outcome"] = outcome
    sc["real_outcome_at"] = item["recorded_at"]
    from .scorecard import save_scorecard

    save_scorecard(root, job_id, sc)
    return item


def calibration_report(root: Path) -> dict:
    data = load_outcomes(root)
    items = list(data.get("items") or [])
    n = len(items)
    # positive outcomes
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

    report = {
        "sample_size": n,
        "items": items,
        "high_practice_fail": high_practice_fail,
        "low_practice_pass": low_practice_pass,
        "drift_notes": drift_notes,
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
    md.append("## Outcomes")
    md.append("")
    for it in items:
        p = it.get("practice") or {}
        md.append(
            f"- `{it.get('job_id')}` → **{it.get('outcome')}** "
            f"(practice jd_fit={p.get('jd_fit')}, avg={p.get('avg_score')})"
        )
    (out_dir / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report
