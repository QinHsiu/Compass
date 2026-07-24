# Changelog

## 0.7.3 — 2026-07-25

- Core: **Requirement Evidence Matrix** (`match_explain`) — per JD line `direct` / `partial` / `gap` + severity + recommendation band (job-resume-tailor Round 2)
- Artifacts: `match.json` fields `requirement_matrix` / `match_explain`; human table `match_explain.md`
- CLI: `match-explain --job-id`
- Diagnose / interview / resume consume matrix (fatal P0, requirement-mapped STAR, evidence priority)

## 0.7.2 — 2026-07-25

- Core: zero-LLM JD **skill-gap** preflight (`compass_core.skill_gap`) — buckets `existing` / `supported_by_evidence` / `gap` (career-ops Round 1)
- `match.json` includes `skill_gap`; CLI `skill-gap --job-id|--jd-file|--text`
- `/resume`: never inject `gap` skills into Skills; `ats_report.checklist.no_gap_skills_injected`
- Docs: COMPETITIVE.md “Learned from career-ops (Round 1)”; Evidence Gate + `/discover`/`/resume` skill notes

## 0.7.1 — 2026-07-24

- Skill: `/resume` one-page polish spec (`skill/reference/resume-onepage.md`) — timeline, 问题/方法/结果, papers block, whitespace budget, privacy rules
- Skill: interview hooks template (no PII); anonymous `content/fixtures/resume_onepage_example.json`
- Gitignore: extra guards against resume PDFs, hooks, quality reviews, onepage extractors (never commit real CV / experience payloads)

## 0.7.0 — 2026-07-19

- `/life` 兴趣探索 → 职业规划：置信度分流（直接规划 vs Holland RIASEC 测评）
- Web「职业探索」独立页：六维雷达/条形、路径卡、90 天行动、交互追问、一键进求职准备
- CLI：`life explore|answer|refine|export|show`；产物 `content/life/{session_id}/`
- 自研改编 RIASEC 题库 `assets/life/riasec_zh.json`（36 题短量表，每维 6 题；非商业 SDS）

## 0.6.0 — 2026-07-19

- Config: `.env.example`, layered install docs, Docker **4GB+** guidance, `requirements-web.txt` / `requirements-lock.txt`
- Evidence graph: type filters, search, detail pane, clickable edges; embed in Web pipeline results
- ASR: `POST /api/asr` Whisper fallback (optional `[asr]`) + record button in Web interview
- RAG: `compass rag-eval` + fixtures `rag_queries.jsonl` + optional `query_log.jsonl`
- Export: HTML quadrant cards + evidence table; PDF sectioned summary
- Community: expanded GOOD_FIRST_ISSUES, 3-minute demo script, `docs/assets/demo-pipeline.svg`

## 0.5.1 — 2026-07-19

- Primary UI: Compass Web (WebSocket); bilingual bank questions; Gradio optional

## 0.5.0 — 2026-07-19

- Evidence graph, demo pipeline, report export, i18n, community pack

## 0.4.0 — 2026-07-19

- Docker + compose; multi-LLM; Interview Live; RAG; adaptive follow-up; Monaco/PWA

## 0.3.0 — 2026-07-19

- Gradio Studio, PDF/image ingest, LLM/Agent crawl bank, TTS/ASR hooks

## 0.2.0 — 2026-07-19

- 12 resume themes, question bank retrieval

## 0.1.0 — 2026-07-19

- Initial evidence-driven compass skill + core library
