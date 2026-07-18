# Iteration plan / 自迭代计划

## Goal

证据驱动闭环 + 实时面试追问 + 可部署 Demo；不堆企业端/监考。

## Loop

| Round | Gap | Fix | Done |
|:------|:----|:----|:-----|
| R1–R6 | Studio / ingest / bank / voice / README | v0.3 | ✅ |
| A1 | Docker / Demo | Dockerfile + compose + HF card | ✅ |
| A2 | Multi-LLM | `compass_core.llm` | ✅ |
| A3 | Realtime interview | `apps/interview-live` WebSocket | ✅ |
| A4 | Adaptive follow-up | `next_followup` | ✅ |
| B1 | RAG | Chroma `rag-index` / `--semantic` | ✅ |
| B2 | Docs / community | COMPETITIVE + CONTRIBUTING + launch.md | ✅ |
| C | Timeline / Monaco / PWA | Live UI | ✅ |

## Commands

```bash
docker compose up
python -m compass_core.cli studio --root content
python -m compass_core.cli live --root content
python -m compass_core.cli rag-index --root content
python -m compass_core.cli questions --semantic --query "rag agent memory"
python -m compass_core.cli timeline --root content --html content/timeline.html
```
