# Feature store latency cut

- **id**: `ev_featstore_latency`
- **tags**: mlops, platform
- **skills**: python, kubernetes, feature store, redis
- **proof**: internal postmortem + grafana screenshots (redacted)

## Context

Maintained online feature serving for recommendation models.

## Actions

Profiled p99 latency; introduced Redis cache tier and batch warmup; added SLO dashboards.

## Metrics

p99 latency 180ms → 45ms; cache hit rate 92%; zero Sev-1 in 2 quarters.
