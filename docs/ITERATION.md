# Iteration plan / 自迭代计划

## Goal

证据驱动闭环 + 实时面试 + 可部署 Demo + 证据图谱与社区冷启动；不堆企业端/监考/微调。

## Loop

| Round | Gap | Fix | Done |
|:------|:----|:----|:-----|
| A–C | Docker / LLM / Live / RAG / followup / Monaco / PWA | v0.4 | ✅ |
| D1 | Evidence graph | SVG timeline HTML | ✅ |
| D2 | Demo one-click | `COMPASS_DEMO` fixtures pipeline | ✅ |
| D3 | Community pack | launch article + GOOD_FIRST_ISSUES | ✅ |
| E1 | Mobile / PWA | Studio CSS + Live SW cache | ✅ |
| E2 | Report export | `export-report` HTML/PDF | ✅ |
| E3 | Contrib | Issue templates + COMPETITIVE 0.5 | ✅ |

## Commands

```bash
docker compose up
python -m compass_core.cli studio --root content
python -m compass_core.cli live --root content
python -m compass_core.cli timeline --root content --html content/timeline.html
python -m compass_core.cli export-report --root content
python -m compass_core.cli rag-index --root content
```
