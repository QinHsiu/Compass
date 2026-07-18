# Kubernetes job autoscaling

- **id**: `ev_k8s_autoscale`
- **tags**: infra, reliability
- **skills**: kubernetes, docker, python, linux
- **proof**: design doc + oncall notes

## Context

Batch training jobs caused cluster thrash during peak hours.

## Actions

Tuned HPA/VPA policies; isolated training namespace; wrote Python controller hooks for queue depth.

## Metrics

Cluster CPU waste -30%; failed jobs -40%; MTTR for scheduling incidents 40min → 12min.
