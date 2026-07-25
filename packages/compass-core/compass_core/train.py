"""8-stage progressive interview training (interview-coach-skill parity)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STAGES: list[dict] = [
    {
        "id": 1,
        "name": "structure_star",
        "title": "结构打底（STAR）",
        "focus": ["structure"],
        "drill": "用完整 S-T-A-R 重述一段经历，每段 ≤2 句；禁止跳过 Result。",
        "pass_hint": "structure ≥ 3.5 或完成 ≥2 次 STAR 口述",
    },
    {
        "id": 2,
        "name": "substance_metrics",
        "title": "实质与指标",
        "focus": ["substance"],
        "drill": "同一故事补可验证数字（延迟/成本/规模）；绑定 evidence_id。",
        "pass_hint": "substance ≥ 3.5 且答案含数字或 evidence",
    },
    {
        "id": 3,
        "name": "ownership_conflict",
        "title": "Ownership / 冲突",
        "focus": ["structure", "substance"],
        "drill": "讲一次分歧或失败：你的决策标准、推动动作、复盘。",
        "pass_hint": "BEI probe ok 或 tags 含 conflict/failure",
    },
    {
        "id": 4,
        "name": "jd_keywords",
        "title": "JD 关键词覆盖",
        "focus": ["relevance", "jd_fit"],
        "drill": "对照 requirement_matrix：每条 gap 准备一句「不编造」过渡。",
        "pass_hint": "relevance/jd_fit ≥ 3.5",
    },
    {
        "id": 5,
        "name": "credibility_gate",
        "title": "可信度与门禁",
        "focus": ["credibility"],
        "drill": "每句主张标 verified / UNVERIFIED；跑 gate 检查。",
        "pass_hint": "gate_pass_rate ≥ 0.7 或 credibility ≥ 3.5",
    },
    {
        "id": 6,
        "name": "differentiation",
        "title": "差异化 sharpness",
        "focus": ["substance", "jd_fit"],
        "drill": "提炼 1 个「只有你能讲」的 sharpness：独特组合技能 + 结果。",
        "pass_hint": "完成 differentiation 笔记并 scorecard 记录 1 轮",
    },
    {
        "id": 7,
        "name": "mock_loop",
        "title": "全流程 Mock",
        "focus": ["substance", "structure", "relevance", "credibility", "jd_fit"],
        "drill": "interview-pack → 连续 5 题口述 → scorecard 全维。",
        "pass_hint": "单次 session ≥5 answers",
    },
    {
        "id": 8,
        "name": "calibrate_real",
        "title": "真实结果校准",
        "focus": ["jd_fit"],
        "drill": "录入 ≥1 次真实面试结果；跑 calibrate report / diagnose --calibrate。",
        "pass_hint": "calibrate 有记录或 real_outcome 非空",
    },
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _state_path(root: Path, job_id: str) -> Path:
    return Path(root) / "interviews" / job_id / "train_state.json"


def load_state(root: Path, job_id: str) -> dict:
    path = _state_path(root, job_id)
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "job_id": job_id,
        "stage": 1,
        "completed": [],
        "notes": {},
        "updated_at": None,
    }


def save_state(root: Path, state: dict) -> Path:
    job_id = state["job_id"]
    path = _state_path(root, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _utcnow()
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _scorecard_scores(root: Path, job_id: str) -> dict:
    sc = Path(root) / "interviews" / job_id / "scorecard.json"
    if not sc.is_file():
        return {}
    data = json.loads(sc.read_text(encoding="utf-8"))
    return {
        "scores": (data.get("aggregate") or {}).get("scores") or {},
        "gate_pass_rate": (data.get("aggregate") or {}).get("gate_pass_rate"),
        "answers": len(data.get("answers") or []),
        "real_outcome": data.get("real_outcome"),
    }


def _auto_pass(root: Path, job_id: str, stage: dict) -> bool:
    """Heuristic auto-detect pass when user hasn't marked complete."""
    sc = _scorecard_scores(root, job_id)
    scores = sc.get("scores") or {}
    sid = stage["id"]
    if sid == 1:
        return float(scores.get("structure") or 0) >= 3.5
    if sid == 2:
        return float(scores.get("substance") or 0) >= 3.5
    if sid == 3:
        return float(scores.get("structure") or 0) >= 3.5 and float(scores.get("substance") or 0) >= 3.0
    if sid == 4:
        return float(scores.get("relevance") or 0) >= 3.5 or float(scores.get("jd_fit") or 0) >= 3.5
    if sid == 5:
        g = sc.get("gate_pass_rate")
        return (g is not None and float(g) >= 0.7) or float(scores.get("credibility") or 0) >= 3.5
    if sid == 6:
        note = Path(root) / "interviews" / job_id / "differentiation.md"
        return note.is_file() or float(scores.get("substance") or 0) >= 4.0
    if sid == 7:
        return int(sc.get("answers") or 0) >= 5
    if sid == 8:
        cal = Path(root) / "calibrate" / "report.json"
        if sc.get("real_outcome"):
            return True
        return cal.is_file()
    return False


def train_status(root: Path, job_id: str) -> dict:
    root = Path(root)
    state = load_state(root, job_id)
    stage_id = int(state.get("stage") or 1)
    stage = STAGES[min(max(stage_id, 1), 8) - 1]
    sc = _scorecard_scores(root, job_id)
    from .root_cause import diagnose_root_causes

    roots = diagnose_root_causes(sc.get("scores") or {})
    # bottleneck → suggest stage
    bottleneck_stage = None
    if roots:
        dim = roots[0]["dimension"]
        for s in STAGES:
            if dim in s["focus"]:
                bottleneck_stage = s["id"]
                break
    auto = _auto_pass(root, job_id, stage)
    return {
        "job_id": job_id,
        "stage": stage,
        "state": state,
        "scorecard": sc,
        "root_causes": roots,
        "bottleneck_stage": bottleneck_stage,
        "auto_pass": auto,
        "stages_total": 8,
        "progress": f"{len(state.get('completed') or [])}/8",
    }


def train_next(root: Path, job_id: str) -> dict:
    st = train_status(root, job_id)
    stage = st["stage"]
    md_lines = [
        f"# Train stage {stage['id']}/8 — {stage['title']}",
        "",
        f"**focus**: {', '.join(stage['focus'])}",
        "",
        "## Drill",
        "",
        stage["drill"],
        "",
        f"**pass**: {stage['pass_hint']}",
        "",
        "## Commands",
        "",
        f"- `scorecard record --job-id {job_id} ...`",
        f"- `train complete --job-id {job_id}` when done",
        f"- `train advance --job-id {job_id}` to next stage",
    ]
    if st.get("bottleneck_stage") and st["bottleneck_stage"] != stage["id"]:
        md_lines += [
            "",
            f"> Bottleneck suggests stage **{st['bottleneck_stage']}** "
            f"(from root_causes).",
        ]
    out_dir = Path(root) / "interviews" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "train_next.md"
    path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {**st, "path": str(path), "markdown": "\n".join(md_lines)}


def train_complete(root: Path, job_id: str, *, note: str = "") -> dict:
    state = load_state(root, job_id)
    cur = int(state.get("stage") or 1)
    completed = list(state.get("completed") or [])
    if cur not in completed:
        completed.append(cur)
    state["completed"] = completed
    notes = dict(state.get("notes") or {})
    if note:
        notes[str(cur)] = note
    state["notes"] = notes
    save_state(root, state)
    return train_status(root, job_id)


def train_advance(root: Path, job_id: str) -> dict:
    state = load_state(root, job_id)
    cur = int(state.get("stage") or 1)
    completed = list(state.get("completed") or [])
    if cur not in completed:
        completed.append(cur)
    state["completed"] = completed
    state["stage"] = min(8, cur + 1)
    save_state(root, state)
    return train_next(root, job_id)


def train_goto(root: Path, job_id: str, stage: int) -> dict:
    state = load_state(root, job_id)
    state["stage"] = max(1, min(8, int(stage)))
    save_state(root, state)
    return train_next(root, job_id)
