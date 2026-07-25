# Observability / APM (v0.13)

Local-first metrics and optional enterprise export.

## CLI

| Command | Output |
|:--|:--|
| `obs status` | counters + span count + paths |
| `obs tail -n 20` | recent `logs/audit.jsonl` |
| `obs alerts` | rule eval → `logs/alerts.json` |
| `obs slo` | gate / ingest / latency snapshot → `logs/slo.json` |
| `obs export-prom [--out f]` | Prometheus text |

## Desk

`GET /metrics` on Compass Desk exposes the same Prometheus text.

## Spans

Key commands wrap `observability.span` → append `logs/spans.jsonl`.

Optional SDK export:

```bash
set COMPASS_OTEL=1
# or
set OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318/v1/traces
```

Requires `opentelemetry-api` / `opentelemetry-sdk` (and OTLP exporter) if you want real export; otherwise local JSONL still works.

## Grafana (sketch)

1. Scrape Desk `/metrics` or a node_exporter textfile from `obs export-prom --out`.
2. Panels: `compass_counter{name="scout_runs"}`, `compass_spans_total`, gate alerts from `logs/alerts.json` (file datasource / sidecar).

## Privacy

Do not enable remote OTLP on machines with real resumes unless the sink is trusted. Paths in attrs should stay job_id-level, not full PII.
