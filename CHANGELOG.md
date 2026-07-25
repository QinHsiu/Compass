# Changelog

## 0.21.0 — 2026-07-25

compas.txt refresh — close true remaining deltas (matrix P0/P1 mostly stale vs ≤0.20):

- **batch**: checkpoint + `--resume` + progress lines (`batches/*/checkpoint.json`)
- **parallel**: `match-explain` / `resume-patch --job-ids --workers`
- **transcript rubric**: per-Q five-dim heuristic → scorecard via oral_log `scores`
- **experience import**: `experience import --file` → `content/experiences/`
- **tutorial** / **report-summary**: onboarding steps + practice center alias
- Docs: COMPETITIVE learned-from-compas v0.21; update oss `compas.txt` status

## 0.20.0 — 2026-07-25

JobSpy-style multi discover + stronger export-HTML ingest + Crawl4AI patterns (still no JobSpy/Boss/Crawl4AI deps):

- **`discover --source multi`**: fan-in ats/feeds/companies/career; `--sources` / `--depth`
- **`session scout-html`**: card/anchor parsers, fit-markdown, content_hash, optional `--match`
- **Fit markdown + depth crawl**: `html_to_jd_markdown(fit=True)`, `crawl_career_depth` (list→same-host detail)
- Docs: COMPLIANCE clarifies export-HTML vs CDP

## 0.19.0 — 2026-07-25

First-party crawl patterns from `oss_competitors/crawl.txt` (no Crawl4AI/JobSpy/Boss deps):

- **Career normalizer**: `html_to_jd_markdown` (JSON-LD → clean markdown) wired into `parse_career_page` / `collect_career_html`
- **Public feeds**: `discover --source feeds` (Remotive / Arbeitnow + `feeds.yml`)
- **SmartRecruiters**: `ats_scan` board `smartrecruiters:id`
- **Watchlist**: `watch scan` — companies.yml + portals, URL dedupe vs warehouse, `batches/watch_*/summary.json`
- **JD red-flags**: `jd-analyze` / `jd-compare` + diagnose inject (黑话/背锅位/伪技术岗)
- Docs: COMPETITIVE crawl.txt note; COMPLIANCE public feeds / no Boss scrape

## 0.18.0 — 2026-07-25

Close remaining `compass.txt` / GOOD_FIRST deltas (matrix P0–P2 already shipped ≤0.17):

- **Timeline**: 「仅显示有边的节点」+ filter prefs in `localStorage`
- **Industry packs**: tech / finance / consulting → `interview-pack` + `questions --industry`
- **rag-eval → obs**: hit@k gauges in `logs/metrics.json` + audit `rag_eval`; Prom gauges export
- Docs: COMPETITIVE v0.18 note; GOOD_FIRST #6/#8 marked done; `projects/compass.txt` status table

## 0.17.0 — 2026-07-25

Multi-source job intel with anti-fabrication filters:

- **intel dossier / verify-salary**: posting · work · pay · hours · reputation · layoff risk; ≥2 sources to corroborate
- **plausibility**: reject rumor packs (e.g. 硕+2年·年薪1000万); peer/band caps
- **safe_landing** score with cited reasons only
- Live `comp` path drops `rejected_implausible` samples
- Docs: `docs/intel.md`

## 0.16.0 — 2026-07-25

Multi-source live pay + company-career job recommend:

- **recommend jobs** / `discover --source companies`: crawl official `career_url` + public Greenhouse/Lever/Ashby; auto-detect ATS from HTML; rank by match
- **companies.yml** seed + `assets/companies_seed.json`
- **comp --live sources**: `levels`, `career`/`warehouse`, `extra_endpoints` alongside offershow/http/jobs
- Ashby postings include compensation fields in JD text when present
- Docs: `docs/recommend.md`

## 0.15.0 — 2026-07-25

Live compensation (OfferShow-oriented):

- **comp lookup --live**: OfferShow-compatible HTTP + generic live URL + JD salary bands
- **comp refresh / ingest-live**: force fetch cache; import mini-program/Charles JSON captures
- Docs: `docs/comp_live.md`; COMPLIANCE opt-in live section
- MCP `comp_lookup(live=true)` via `COMPASS_ACCEPT_TOS_RISK`

## 0.14.0 — 2026-07-25

compas.txt「核心能力短板」真增量（文中 P0/P1 多为陈旧标注，已在 v0.8–0.13）：

- **train**: 8-stage progressive curriculum (`train status|next|complete|advance|goto`)
- **storybank compose**: JD token set-cover story combo
- **comp lookup**: local benchmarks + coach line; MCP `comp_lookup`
- **pipeline board**: terminal Dashboard TUI-lite
- **resume-pick**: Pick Don't Edit bullet selection
- **experience complete**: template standard-answer autocomplete

## 0.13.0 — 2026-07-25

Enterprise-light APM on top of local obs:

- **spans**: `observability.span` → `logs/spans.jsonl`; optional OTLP/`COMPASS_OTEL`
- **Prometheus**: `obs export-prom` + Desk `GET /metrics`
- **SLO**: `obs slo` → `logs/slo.json` (gate_pass / ingest / latency proxy)
- Docs: `docs/observability.md`

## 0.12.0 — 2026-07-25

Login-session + Four-Leaf-scale local warehouse (opt-in / local-only):

- **session**: `session import|status|scout-html` with `--i-accept-tos-risk`
- **auth_collect**: JSON-LD / attr HTML list parser + experimental fixtures
- **warehouse**: SQLite FTS `warehouse ingest|search|seed|stats` (100k-ready)
- **MCP**: `jobs_search` / `jobs_get` over local warehouse
- **COMPLIANCE**: default blocklist unchanged; opt-in documented

## 0.11.0 — 2026-07-25

compas P1/P2 polish:

- **transcript**: multi-format detect (otter/zoom/grain/teams/tactiq)
- **anki export**: TSV/JSON from vault/packs/diagnose
- **experience bank**: local 面经 seed + `experience search` + pack `experience_hits`
- **practice Progress**: dimension series in practice_center
- **obs alerts**: rule engine → `logs/alerts.json`
- **batch board**: recent batch summary table

## 0.10.0 — 2026-07-25

compas.txt matrix shortfall patch (analysis was stale vs v0.9):

- **batch --jobs urls.txt**: parallel URL/board-spec evaluate (workers 5–10); alias of batch-match
- **research**: company brief + contact checklist (no LinkedIn scrape)
- **scorecard roots**: five-dim → root_causes (narrative_hoarding / evidence_gap / …)
- **company packs**: `assets/questions/company_packs.jsonl` + `questions --company` + pack inject
- **obs**: local `logs/audit.jsonl` + `metrics.json`; `obs status|tail`

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
