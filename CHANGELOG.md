# Changelog

## 0.5.1 — 2026-07-19

- **Primary UI**: Compass Web (WebSocket) replaces Gradio as default
- `/ws/app` workbench: ingest, pipeline, demo, bank search, export
- Wide sidebar layout; Docker `web` service on 8766; Gradio behind `--profile gradio`
- CLI: `compass web` alias for `live`

## 0.5.0 — 2026-07-19

- Evidence graph: layered SVG with click highlight (`timeline` HTML / Live `/timeline`)
- Demo: `COMPASS_DEMO=1` one-click fixtures pipeline in Studio; HF Space notes
- Report export: `compass export-report` → HTML (+ optional PDF via `fpdf2`)
- Studio/Live mobile CSS; PWA SW caches static only (not `/api` `/ws` `/timeline`)
- Community: `docs/launch_article_zh.md`, `docs/GOOD_FIRST_ISSUES.md`, GitHub issue templates
- COMPETITIVE refresh: tech gaps closed; proctoring/enterprise/LoRA still out of scope

## 0.4.0 — 2026-07-19

- Docker + compose; multi-LLM; Interview Live; RAG; adaptive follow-up; Monaco/PWA

## 0.3.0 — 2026-07-19

- Gradio Studio, PDF/image ingest, LLM/Agent crawl bank, TTS/ASR hooks

## 0.2.0 — 2026-07-19

- 12 resume themes, question bank retrieval

## 0.1.0 — 2026-07-19

- Initial evidence-driven compass skill + core library
