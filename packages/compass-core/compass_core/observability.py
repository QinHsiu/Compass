"""Local audit log + counters (compas v0.10 light observability)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def logs_dir(root: Path) -> Path:
    d = Path(root) / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def audit_event(root: Path, event: str, **payload: Any) -> None:
    """Append one audit line; never raise to callers."""
    try:
        path = logs_dir(root) / "audit.jsonl"
        row = {"ts": _utcnow(), "event": event, **payload}
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        # bump metrics
        inc_metric(root, event)
        if event in ("match", "discover", "scout", "batch"):
            n = int(payload.get("count") or payload.get("jobs") or 1)
            inc_metric(root, "jobs_matched", n)
        if event == "scorecard_record":
            inc_metric(root, "answers_recorded", 1)
        if event == "scout":
            inc_metric(root, "scout_runs", 1)
    except Exception:
        pass


def metrics_path(root: Path) -> Path:
    return logs_dir(root) / "metrics.json"


def load_metrics(root: Path) -> dict:
    path = metrics_path(root)
    if not path.is_file():
        return {"counters": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"counters": {}}


def inc_metric(root: Path, key: str, n: int = 1) -> None:
    try:
        data = load_metrics(root)
        counters = data.setdefault("counters", {})
        counters[key] = int(counters.get(key) or 0) + int(n)
        data["updated_at"] = _utcnow()
        metrics_path(root).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


def status(root: Path) -> dict:
    return {
        "metrics": load_metrics(root),
        "audit_path": str(logs_dir(root) / "audit.jsonl"),
        "metrics_path": str(metrics_path(root)),
    }


def tail_audit(root: Path, *, n: int = 20) -> list[dict]:
    path = logs_dir(root) / "audit.jsonl"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for ln in lines[-max(1, n) :]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out
