---
id: ev_p99_query
title: 交易查询接口 P99 治理
skills: [MySQL, Redis, 慢SQL, 缓存, 可观测性]
metrics:
  - "核心查询 P99：约 280ms → 95ms（工作日峰值）"
  - "慢 SQL：日均 30+ → <5"
---

## Situation
商户后台「交易明细」在高峰卡顿，客诉上升。

## Action
用慢日志定位联合查询；补覆盖索引；热点商户结果短缓存；Grafana 面板盯 P99 与错误率。

## Result
峰值 P99 进入百毫秒级；未夸大到「全链路毫秒级」。
