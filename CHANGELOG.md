# Changelog

## 0.9.0 — 2026-07-25

compas.txt refresh — closed-loop automation + quantified outcomes (on top of v0.8.0):

- **scout**: `scout --keyword/--location/--board` → ATS filter + auto match; Web `POST /api/scout`
- **score_100**: three-part grade (`direct_evidence` / `transferable` / `gap_risk`) → `综合匹配度：78/100（B级）`
- **calibrate deepen**: `narrative_hits` + band accuracy; `diagnose --calibrate`
- **offer**: cash/equity/level + user `market_p50` vs_p50 overlay
- **story vault**: SQLite tags + recommend; scorecard answers upsert; `storybank recommend`
- **mentor PDF**: `export-report --mentor` → mentor_report.md/.pdf

## 0.8.0 — 2026-07-25

compas.txt P0 + P1 + light P2 product gap fills (local-first):

- **ATS scan**: `discover --source ats --board greenhouse|lever|ashby:slug` (public JSON APIs)
- **Grade**: deterministic A–F + 1.0–5.0 dimensions on `match.json.grade`; CLI `grade`
- **Resume import**: `resume-import --file` PDF/text → JSON Resume subset
- **Batch match**: `batch-match --all-jobs|--from-ats` → `batches/*/summary.json`
- **Storybank**: `storybank rebuild|list|show`; injected into interview pack
- **Transcript**: `transcript-import` Otter/Zoom-like → oral_log + scorecard
- **Offer compare**: six-dim radar user scores; `offer init|compare`
- **Practice center**: `practice-stats --export` → `reports/practice_center.md`
- **Negotiate**: local pack (no live salary API); `negotiate`
- **Calibrate**: `calibrate record|report` practice vs real outcomes

Still out of scope: login scrapers, Four-Leaf live job MCP, cloud registry, enterprise observability.

## 0.7.8 — 2026-07-25

- Rounds 7–13 competitive fills:
  - **bei_probe** (interview-skills) — STAR/ownership probe → follow-up + scorecard `structure` / `bei_probe`
  - **question_dedup** (interview-guide) — filter already-asked bank hits in pack
  - **resume_lint** (open-resume) — one-page density in `ats_report`
  - **resume_metrics** (jsonresume) — years/companies/projects/degree; CLI `resume-metrics`
  - **practice_stats** (intervAI) — cross-job rollup; desk + CLI `practice-stats`
  - **interview_persona** (IntervAI-xuanyiying) — pack persona + opening question
  - **posting_liveness** (career-ops leftover) — ATS detect + stale band cap on `match.json`

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
