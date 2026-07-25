"""Interactive first-loop tutorial (compas onboarding)."""

from __future__ import annotations

import json
from pathlib import Path

STEPS = [
    {
        "id": 1,
        "title": "准备证据",
        "cmd": "python -m compass_core.cli evidence-index --root content",
        "hint": "把可验证项目写入 content/evidence/*.md，再重建索引",
    },
    {
        "id": 2,
        "title": "粘贴 JD 并匹配",
        "cmd": "python -m compass_core.cli discover --root content --source paste --text-file content/fixtures/demo/jd.txt",
        "hint": "也可用 fixtures 快速体验；产出 jobs/<id>/match.json",
    },
    {
        "id": 3,
        "title": "看缺口与解释",
        "cmd": "python -m compass_core.cli match-explain --root content --job-id <id>",
        "hint": "requirement_matrix + match_explain.md",
    },
    {
        "id": 4,
        "title": "证据门禁简历",
        "cmd": "python -m compass_core.cli resume-patch --root content --job-id <id>",
        "hint": "不会注入 gap skills",
    },
    {
        "id": 5,
        "title": "面试包 + 练习",
        "cmd": "python -m compass_core.cli interview-pack --root content --job-id <id>",
        "hint": "随后可用 scorecard / transcript-import",
    },
    {
        "id": 6,
        "title": "诊断与统计",
        "cmd": "python -m compass_core.cli diagnose --root content --job-id <id>",
        "hint": "report-summary / practice-stats --export 看练习趋势",
    },
]


def run_tutorial(root: Path, *, step: int | None = None) -> dict:
    root = Path(root)
    fixture_jd = None
    # try locate demo jd relative to content root or repo
    for cand in (
        root / "fixtures" / "demo" / "jd.txt",
        Path(__file__).resolve().parents[3] / "content" / "fixtures" / "demo" / "jd.txt",
    ):
        if cand.is_file():
            fixture_jd = str(cand)
            break

    steps = STEPS
    if step is not None:
        steps = [s for s in STEPS if s["id"] == int(step)]
        if not steps:
            return {"error": f"unknown step {step}", "steps": STEPS}

    # progress file
    prog_path = root / "logs" / "tutorial_progress.json"
    prog_path.parent.mkdir(parents=True, exist_ok=True)
    done = []
    if prog_path.is_file():
        try:
            done = list(json.loads(prog_path.read_text(encoding="utf-8")).get("done") or [])
        except json.JSONDecodeError:
            done = []

    out_steps = []
    for s in steps:
        item = dict(s)
        if fixture_jd and "<id>" not in item["cmd"] and "jd.txt" in item["cmd"]:
            item["cmd"] = item["cmd"].replace(
                "content/fixtures/demo/jd.txt", fixture_jd.replace("\\", "/")
            )
        item["done"] = s["id"] in done
        out_steps.append(item)

    next_id = next((s["id"] for s in STEPS if s["id"] not in done), None)
    md_lines = ["# Compass tutorial", "", "完成闭环：证据 → JD → 匹配 → 简历 → 面试 → 诊断", ""]
    for s in STEPS:
        mark = "x" if s["id"] in done else " "
        md_lines.append(f"- [{mark}] **{s['id']}. {s['title']}**: `{s['cmd']}`")
        md_lines.append(f"  - {s['hint']}")
    guide = root / "reports"
    guide.mkdir(parents=True, exist_ok=True)
    guide_path = guide / "tutorial.md"
    guide_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # mark requested step done when --step given (user ran it)
    if step is not None and int(step) not in done:
        done.append(int(step))
        prog_path.write_text(json.dumps({"done": done}, indent=2), encoding="utf-8")

    return {
        "steps": out_steps,
        "next_step": next_id,
        "fixture_jd": fixture_jd,
        "guide": str(guide_path),
        "progress": str(prog_path),
        "tip": "Run with --step N after completing that step to mark progress",
    }
