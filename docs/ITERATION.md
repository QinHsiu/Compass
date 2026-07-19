# Iteration plan / 自迭代计划

## Goal

证据驱动闭环 + Web 主界面；降低配置门槛；图谱可交互；RAG/ASR 可观测；不堆监考/企业端。

## Loop

| Round | Gap | Fix | Done |
|:------|:----|:----|:-----|
| A–E | Docker / Live / RAG / graph / export / i18n | v0.5 | ✅ |
| F1 | Config barrier | `.env.example` + layered install + 4GB note | ✅ |
| F2 | Graph interaction | filter / search / detail / embed | ✅ |
| F3 | Community pack | GOOD_FIRST + 3-min script + demo asset | ✅ |
| G1 | ASR accuracy | `/api/asr` + record button | ✅ |
| G2 | RAG metrics | `rag-eval` + fixtures | ✅ |
| G3/G4 | Lock + export | requirements-* + quadrant HTML | ✅ |
| H1 | Career explore | `/life` + RIASEC + Web 职业探索 | ✅ |

## Commands

```bash
cp .env.example .env
docker compose up --build
python -m compass_core.cli web --root content
python -m compass_core.cli life explore --root content --text-file story.txt
python -m compass_core.cli rag-eval --root content
python -m compass_core.cli export-report --root content
python -m compass_core.cli timeline --root content --html content/timeline.html
```
