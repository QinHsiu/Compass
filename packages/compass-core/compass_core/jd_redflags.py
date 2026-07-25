"""JD red-flag lexicon (JD Analyzer pattern) — 黑话 / 伪技术岗 / 背锅位 / dirty work."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_ASSET = Path(__file__).resolve().parent / "assets" / "jd_redflags.yml"
_ASSET_JSON = Path(__file__).resolve().parent / "assets" / "jd_redflags.json"


DEFAULT_RULES: list[dict] = [
    {
        "id": "rf_pressure",
        "category": "dirty_work",
        "severity": "P1",
        "patterns": ["抗压", "承受压力", "高压", "加班常态", "996", "大小周"],
        "label": "高强度/加班暗示",
        "hint": "追问真实工时与 on-call；对照 intel hours 证据",
    },
    {
        "id": "rf_screw",
        "category": "scapegoat",
        "severity": "P0",
        "patterns": ["螺丝钉", "打杂", "随叫随到", "背锅", "救火", "背责"],
        "label": "背锅位/杂务风险",
        "hint": "确认职责边界与晋升路径；写入 retracted / Do not claim",
    },
    {
        "id": "rf_buzz",
        "category": "buzzword",
        "severity": "P2",
        "patterns": ["赋能", "抓手", "闭环", "对齐颗粒度", "打法", "心智"],
        "label": "黑话/空心表述",
        "hint": "要求对方用可验证交付物改写 JD 句子",
    },
    {
        "id": "rf_pseudo_tech",
        "category": "pseudo_tech",
        "severity": "P1",
        "patterns": ["懂技术更好", "技术氛围", "参与架构讨论", "不写代码也可"],
        "label": "伪技术岗信号",
        "hint": "确认是否写生产代码、是否有 code review / oncall",
    },
    {
        "id": "rf_growth_vague",
        "category": "prospect",
        "severity": "P2",
        "patterns": ["广阔平台", "空间巨大", "快速发展期", "期权丰厚"],
        "label": "前景空话",
        "hint": "用 intel dossier / comp 交叉验证，勿单信 JD",
    },
    {
        "id": "rf_owner_dump",
        "category": "scapegoat",
        "severity": "P1",
        "patterns": ["独立负责", "从0到1独自", "无人带", "自我驱动即可"],
        "label": "孤立交付/缺 mentor",
        "hint": "问团队规模与 code owner；评估支援",
    },
]


def _parse_simple_yml(text: str) -> list[dict]:
    """Minimal YAML list parser for our asset shape (no PyYAML required)."""
    rules: list[dict] = []
    cur: dict | None = None
    mode = None
    for ln in text.splitlines():
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        if ln.startswith("- id:"):
            if cur:
                rules.append(cur)
            cur = {"id": ln.split(":", 1)[1].strip().strip("\"'"), "patterns": []}
            mode = None
            continue
        if cur is None:
            continue
        m = re.match(r"^\s+(\w+):\s*(.*)$", ln)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "patterns":
            mode = "patterns"
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1]
                cur["patterns"] = [p.strip().strip("\"'") for p in inner.split(",") if p.strip()]
            continue
        if mode == "patterns" and ln.strip().startswith("-"):
            cur.setdefault("patterns", []).append(ln.strip()[1:].strip().strip("\"'"))
            continue
        if key != "patterns":
            mode = None
            cur[key] = val.strip("\"'")
    if cur:
        rules.append(cur)
    return rules


@lru_cache(maxsize=1)
def load_redflag_rules() -> list[dict]:
    if _ASSET_JSON.is_file():
        try:
            data = json.loads(_ASSET_JSON.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return data
            if isinstance(data, dict) and data.get("rules"):
                return list(data["rules"])
        except json.JSONDecodeError:
            pass
    if _ASSET.is_file():
        text = _ASSET.read_text(encoding="utf-8")
        try:
            import yaml as _yaml  # optional

            data = _yaml.safe_load(text)
            if isinstance(data, dict) and data.get("rules"):
                return list(data["rules"])
            if isinstance(data, list):
                return data
        except Exception:
            parsed = _parse_simple_yml(text)
            if parsed:
                return parsed
    return list(DEFAULT_RULES)


def analyze_jd_text(text: str, *, title: str = "", company: str = "") -> dict:
    blob = f"{title}\n{company}\n{text}"
    hits: list[dict] = []
    for rule in load_redflag_rules():
        pats = rule.get("patterns") or []
        matched = [p for p in pats if p and p.lower() in blob.lower()]
        if not matched:
            # also try regex word-ish for ascii
            for p in pats:
                if len(p) >= 3 and re.search(re.escape(p), blob, re.I):
                    matched.append(p)
        if matched:
            hits.append(
                {
                    "id": rule.get("id"),
                    "category": rule.get("category"),
                    "severity": rule.get("severity") or "P2",
                    "label": rule.get("label"),
                    "hint": rule.get("hint"),
                    "matched": matched[:5],
                }
            )
    # severity rollup
    p0 = sum(1 for h in hits if h.get("severity") == "P0")
    p1 = sum(1 for h in hits if h.get("severity") == "P1")
    risk = "high" if p0 else ("medium" if p1 or len(hits) >= 3 else ("low" if hits else "none"))
    return {
        "title": title,
        "company": company,
        "flags": hits,
        "count": len(hits),
        "risk": risk,
        "summary": f"{len(hits)} red-flags ({risk})",
    }


def analyze_job(root: Path, job_id: str) -> dict:
    root = Path(root)
    job_dir = root / "jobs" / job_id
    jd_path = job_dir / "jd.json"
    if not jd_path.is_file():
        return {"error": f"missing {jd_path}", "job_id": job_id}
    jd = json.loads(jd_path.read_text(encoding="utf-8"))
    text = jd.get("raw_text") or ""
    if not text:
        text = "\n".join(
            [
                str(jd.get("title") or ""),
                str(jd.get("company") or ""),
                "\n".join(jd.get("hard_requirements") or []),
                "\n".join(jd.get("responsibilities") or []),
            ]
        )
    out = analyze_jd_text(text, title=str(jd.get("title") or ""), company=str(jd.get("company") or ""))
    out["job_id"] = job_id
    out_path = job_dir / "redflags.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    out["path"] = str(out_path)

    # inject into match_explain.md if present
    mx = job_dir / "match_explain.md"
    if hits := out.get("flags"):
        block = "\n## JD red-flags\n\n" + "\n".join(
            f"- **{h.get('priority')}** `{h.get('id')}` {h.get('label')}: {', '.join(h.get('matched') or [])}"
            for h in hits
        )
        if mx.is_file():
            body = mx.read_text(encoding="utf-8")
            if "## JD red-flags" not in body:
                mx.write_text(body.rstrip() + "\n" + block + "\n", encoding="utf-8")
        else:
            mx.write_text(f"# match explain\n{block}\n", encoding="utf-8")
    return out


def compare_jobs(root: Path, job_ids: list[str]) -> dict:
    """Multi-JD compare on grade parts + redflag counts (radar-friendly)."""
    root = Path(root)
    rows = []
    for jid in job_ids:
        jdir = root / "jobs" / jid
        match_path = jdir / "match.json"
        grade = {}
        title = jid
        company = ""
        if match_path.is_file():
            data = json.loads(match_path.read_text(encoding="utf-8"))
            grade = data.get("grade") or {}
            title = data.get("title") or title
            company = data.get("company") or ""
        rf = analyze_job(root, jid)
        parts = grade.get("parts") or {}
        rows.append(
            {
                "job_id": jid,
                "title": title,
                "company": company,
                "letter": grade.get("letter"),
                "score_100": grade.get("score_100"),
                "parts": parts,
                "redflag_count": rf.get("count"),
                "risk": rf.get("risk"),
                "flags": [f.get("id") for f in (rf.get("flags") or [])],
                "radar": [
                    {"dim": k, "value": float(v)} for k, v in parts.items() if isinstance(v, (int, float))
                ],
            }
        )
    return {"jobs": rows, "n": len(rows)}
