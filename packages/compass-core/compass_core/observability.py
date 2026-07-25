"""Local audit log + counters + alerts + light APM export (compas v0.10–0.13)."""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


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
        inc_metric(root, event)
        if event in ("match", "discover", "scout", "batch", "warehouse_ingest"):
            n = int(payload.get("count") or payload.get("jobs") or 1)
            inc_metric(root, "jobs_matched", n)
        if event == "scorecard_record":
            inc_metric(root, "answers_recorded", 1)
        if event == "scout":
            inc_metric(root, "scout_runs", 1)
        # duration histogram-ish
        if "duration_ms" in payload:
            inc_metric(root, f"{event}_duration_ms_sum", int(payload["duration_ms"]))
            inc_metric(root, f"{event}_duration_count", 1)
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
    otel_on = bool(os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")) or (
        os.environ.get("COMPASS_OTEL", "").lower() in ("1", "true", "on")
    )
    spans_path = logs_dir(root) / "spans.jsonl"
    span_count = 0
    if spans_path.is_file():
        span_count = sum(1 for _ in spans_path.open(encoding="utf-8") if _.strip())
    return {
        "metrics": load_metrics(root),
        "audit_path": str(logs_dir(root) / "audit.jsonl"),
        "metrics_path": str(metrics_path(root)),
        "otel": {"enabled": otel_on, "spans_local": span_count, "spans_path": str(spans_path)},
        "alerts_path": str(logs_dir(root) / "alerts.json"),
        "slo_path": str(logs_dir(root) / "slo.json"),
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


def _avg_gate_pass(root: Path) -> float | None:
    iv = Path(root) / "interviews"
    rates = []
    if not iv.is_dir():
        return None
    for d in iv.iterdir():
        sc = d / "scorecard.json"
        if not sc.is_file():
            continue
        try:
            data = json.loads(sc.read_text(encoding="utf-8"))
            r = (data.get("aggregate") or {}).get("gate_pass_rate")
            if r is not None:
                rates.append(float(r))
        except Exception:
            continue
    if not rates:
        return None
    return sum(rates) / len(rates)


def evaluate_alerts(root: Path) -> dict:
    """Rule engine → logs/alerts.json."""
    root = Path(root)
    metrics = load_metrics(root).get("counters") or {}
    fired: list[dict] = []
    gate = _avg_gate_pass(root)
    if gate is not None and gate < 0.5:
        fired.append(
            {
                "id": "gate_pass_rate_low",
                "severity": "warn",
                "message": f"avg gate_pass_rate={gate:.2f} < 0.5",
                "value": gate,
            }
        )
    # calibrate drift: look for calibrate report
    cal = root / "calibrate" / "report.json"
    if cal.is_file():
        try:
            rep = json.loads(cal.read_text(encoding="utf-8"))
            if rep.get("drift_ready") or (rep.get("band_accuracy") is not None and float(rep.get("band_accuracy") or 1) < 0.4):
                fired.append(
                    {
                        "id": "calibrate_drift",
                        "severity": "info",
                        "message": "calibration drift ready / low band accuracy",
                        "value": rep.get("band_accuracy"),
                    }
                )
        except Exception:
            pass
    scout_runs = int(metrics.get("scout_runs") or 0)
    if scout_runs == 0 and int(metrics.get("batch") or 0) == 0:
        fired.append(
            {
                "id": "no_discovery_activity",
                "severity": "info",
                "message": "no scout/batch activity recorded yet",
                "value": 0,
            }
        )
    ingest_fail = int(metrics.get("warehouse_ingest_error") or 0)
    if ingest_fail >= 3:
        fired.append(
            {
                "id": "warehouse_ingest_errors",
                "severity": "warn",
                "message": f"warehouse_ingest_error={ingest_fail}",
                "value": ingest_fail,
            }
        )
    out = {"ts": _utcnow(), "count": len(fired), "alerts": fired}
    path = logs_dir(root) / "alerts.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def export_prometheus(root: Path) -> str:
    """Text exposition format for Prometheus scrape / obs export-prom."""
    counters = load_metrics(root).get("counters") or {}
    lines = [
        "# HELP compass_counter Compass local counters",
        "# TYPE compass_counter counter",
    ]
    for k, v in sorted(counters.items()):
        safe = "".join(c if c.isalnum() or c == "_" else "_" for c in str(k))
        lines.append(f'compass_counter{{name="{safe}"}} {int(v)}')
    spans = 0
    sp = logs_dir(root) / "spans.jsonl"
    if sp.is_file():
        spans = sum(1 for ln in sp.open(encoding="utf-8") if ln.strip())
    lines.append("# TYPE compass_spans_total counter")
    lines.append(f"compass_spans_total {spans}")
    return "\n".join(lines) + "\n"


def compute_slo(root: Path) -> dict:
    """Simple SLO snapshot."""
    root = Path(root)
    counters = load_metrics(root).get("counters") or {}
    gate = _avg_gate_pass(root)
    match_n = int(counters.get("match") or 0) + int(counters.get("batch") or 0)
    match_sum = int(counters.get("match_duration_ms_sum") or 0) + int(
        counters.get("batch_duration_ms_sum") or 0
    )
    match_cnt = int(counters.get("match_duration_count") or 0) + int(
        counters.get("batch_duration_count") or 0
    )
    p95_proxy = (match_sum / match_cnt) if match_cnt else None  # avg as proxy
    ingest_ok = int(counters.get("warehouse_ingest") or 0)
    ingest_err = int(counters.get("warehouse_ingest_error") or 0)
    ingest_total = ingest_ok + ingest_err
    ingest_success = (ingest_ok / ingest_total) if ingest_total else None
    slo = {
        "ts": _utcnow(),
        "gate_pass_rate": gate,
        "gate_pass_slo_ok": None if gate is None else gate >= 0.5,
        "ingest_success_rate": ingest_success,
        "ingest_slo_ok": None if ingest_success is None else ingest_success >= 0.9,
        "match_avg_ms": p95_proxy,
        "match_latency_slo_ok": None if p95_proxy is None else p95_proxy < 30_000,
        "jobs_activity": match_n,
    }
    path = logs_dir(root) / "slo.json"
    path.write_text(json.dumps(slo, ensure_ascii=False, indent=2), encoding="utf-8")
    return slo


@contextmanager
def span(root: Path, name: str, **attrs: Any) -> Iterator[dict]:
    """Local span recorder; optional OTLP when env set (best-effort)."""
    start = time.perf_counter()
    ctx: dict[str, Any] = {"name": name, "attrs": attrs}
    try:
        yield ctx
        ctx["status"] = "ok"
    except Exception as e:
        ctx["status"] = "error"
        ctx["error"] = str(e)
        raise
    finally:
        dur = int((time.perf_counter() - start) * 1000)
        ctx["duration_ms"] = dur
        ctx["ts"] = _utcnow()
        try:
            path = logs_dir(root) / "spans.jsonl"
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(ctx, ensure_ascii=False) + "\n")
            safe = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
            inc_metric(root, f"span_{safe}", 1)
            if dur:
                inc_metric(root, f"{safe}_duration_ms_sum", dur)
                inc_metric(root, f"{safe}_duration_count", 1)
        except Exception:
            pass
        # optional otel
        if os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get("COMPASS_OTEL"):
            try:
                from .otel_export import export_span

                export_span(name, dur, status=ctx.get("status"), attrs=attrs)
            except Exception:
                pass
