# On-call incident ownership

- **id**: `ev_oncall_sev2`
- **tags**: ownership, reliability
- **skills**: linux, python, kafka
- **proof**: incident ticket INC-2041

## Context

Sev-2: feature pipeline lag after Kafka partition reassignment.

## Actions

Led triage, rolled back consumer config, added lag alerts, wrote runbook.

## Metrics

Restored lag <1min in 25 minutes; added 3 alerts; runbook adopted by team.
