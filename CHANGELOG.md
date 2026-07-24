# Changelog

## 0.7.7 — 2026-07-25

- Core: **profile_fit** gate (prisma-ai Round 6) — locations / target_roles / avoid → `match.json.profile_fit`; can force recommendation `skip` or cap at `exploratory`
- match_explain.md Profile fit section; track seed notes blockers

## 0.7.6 — 2026-07-25

- Core: **retracted_claims** (CareerForge Round 5) — aggregate gate fails / hard gaps / skill gaps into interview pack “Do not claim”
- `ats_report.rejected_bullets` retained from resume gate; session stress section lists risk points

## 0.7.5 — 2026-07-25

- Core: **track cadence** from match band (clover-public Round 4) — `seed_from_match` writes `match_band` / `suggested_action` / `follow_up_due`
- Diagnose auto-seeds track; CLI `track --seed-from-match` / `--list-due`; Desk shows band + due

## 0.7.4 — 2026-07-25

- Core: **interview scorecard** (`scorecard.py`) — per-answer rubric (substance/structure/relevance/credibility/jd_fit) + evidence_ids + requirement_ids (interview-coach-skill Round 3)
- Artifacts: `interviews/{job_id}/scorecard.json`; sync fills `session.md` Scorecard table
- CLI: `scorecard record|show|sync|import-oral`
- WebSocket live: each answer also calls `record_answer`

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
