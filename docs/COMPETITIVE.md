# Competitive positioning / 竞品对照

Source: [compass_r.txt](../../compass_r.txt) (2026-07 eval refresh).

## Status

Core loop and stack (Docker / multi-LLM / WebSocket Web / RAG / follow-up / evidence graph) are **in place**.  
UX primary surface is **Compass Web**, not Gradio. v0.6 focuses on **config onboarding**, **interactive graph**, **ASR fallback**, **RAG measurability**, and **community cold-start**.

## Moat (keep)

| Differentiator | Compass |
|:---------------|:--------|
| Evidence gate | Claims need `evidence_id` |
| Skill-gap preflight | JD skills → `existing` / `supported_by_evidence` / `gap`; never inject gap into resume |
| Requirement matrix | Per JD line `direct` / `partial` / `gap` + recommendation band |
| Quant grade | A–F + 1.0–5.0 dimensions on every match |
| ATS discover | Public Greenhouse/Lever/Ashby board scan |
| BEI probe | STAR completeness → scorecard structure + follow-up hints |
| Question dedup | Skip bank questions already asked in scorecards |
| Storybank | Evidence → STAR drafts with strength |
| Resume density/metrics/import | One-page lint + metrics + PDF import |
| Practice rollup / calibrate | Cross-job center + real-outcome drift notes |
| Offer / negotiate | Six-dim compare + local negotiate pack |
| Interview persona | technical / challenging / supportive / hr from JD + band |
| Posting liveness | ATS detect + stale cap on recommendation |
| Gap compass 4Q | Evidence / Narrative / Skill / Process |
| Multi-form | **Compass Web** + optional Gradio + Skill + CLI + MCP |
| Local-first | Data under `content/` |
| Evidence graph | Interactive filter / search / detail |

## Learned from career-ops (Round 1)

Upstream: [santifer/career-ops](https://github.com/santifer/career-ops) (`jd-skill-gap.mjs`).

| career-ops | Compass adaptation (v0.7.2) |
|:-----------|:----------------------------|
| Classify vs `cv.md` Skills / prose | Classify vs evidence `skills[]` + `searchable_text()` (+ optional profile skills) |
| Buckets: existing / supportedByResume / gap | `existing` / `supported_by_evidence` / `gap` in `match.json` |
| PDF path never writes gap skills | `resume-patch` merges only injectable skills; `ats_report.checklist.no_gap_skills_injected` |
| CLI: `node jd-skill-gap.mjs` | `python -m compass_core.cli skill-gap` |

**Deferred** (later rounds): A–G LLM rubric, posting legitimacy / liveness, golden eval harness, tracker CRM analytics.

## Learned from job-resume-tailor (Round 2)

Upstream: [liheyuting/job-resume-tailor](https://github.com/liheyuting/job-resume-tailor) (prompt-only match tables).

| job-resume-tailor | Compass adaptation (v0.7.3) |
|:------------------|:----------------------------|
| Per-line Strong/Partial/Weak + resume cite | `requirement_matrix[]` with `direct` / `partial` / `gap` + `evidence_ids` |
| Apply/skip bands + confidence | `match_explain.recommendation` + `confidence` + `matrix_score` |
| Gap fatal/material/manageable | `severity` on hard rows → diagnose P0 |
| Score-gated STAR depth | Interview STAR stubs mapped to hard rows with evidence |

Human table: `content/jobs/{id}/match_explain.md`. CLI: `match-explain --job-id`.

## Learned from interview-coach-skill (Round 3)

Upstream: [noamseg/interview-coach-skill](https://github.com/noamseg/interview-coach-skill) (per-unit scorecards + Score History).

| interview-coach-skill | Compass adaptation (v0.7.4) |
|:----------------------|:----------------------------|
| Per-answer 5-dim rubric | `scorecard.answers[].scores` (substance/structure/relevance/credibility/jd_fit) |
| Score History persistence | `interviews/{job_id}/scorecard.json` + aggregate |
| Write on every practice turn | CLI `scorecard record` + live WS `record_answer` |
| Session roll-up | `sync_session_md` fills Scorecard table; `import-oral` migrates jsonl |

## Learned from clover-public (Round 4)

Upstream: [fourleafai/clover-public](https://github.com/fourleafai/clover-public) (analyze-JD apply bands + application tracking).

| clover-public | Compass adaptation (v0.7.5) |
|:--------------|:----------------------------|
| Score bands → apply / tailor / skip | `match_explain.recommendation` → `suggested_action` via `BAND_POLICY` |
| Application tracking | `track.seed_from_match` + `follow_up_due` cadence |
| Next-step nudges | Diagnose auto-seeds board; `track --list-due` |

## Learned from CareerForge (Round 5)

Upstream: [rebecha1227-a11y/CareerForge](https://github.com/rebecha1227-a11y/CareerForge) (mock interview「识别风险点」).

| CareerForge | Compass adaptation (v0.7.6) |
|:------------|:----------------------------|
| 识别风险点 / 弱项 | `retracted_claims[]` in pack + session “Do not claim” |
| Sources | requirement gaps, skill_gap.gap, ats unverified/rejected, scorecard gate fails |

## Learned from prisma-ai (Round 6)

Upstream: [weicanie/prisma-ai](https://github.com/weicanie/prisma-ai) (jobSeekDestination memory in match chain).

| prisma-ai | Compass adaptation (v0.7.7) |
|:----------|:----------------------------|
| Destination/city/role memory | `profile.locations` / `target_roles` / `constraints.avoid` |
| Filter before apply | `profile_fit` status pass/warn/block → band override |

## Learned from interview-skills (Round 7)

Upstream: [jennifer88huang/interview-skills](https://github.com/jennifer88huang/interview-skills) (BEI/STAR completeness coaching).

| interview-skills | Compass adaptation (v0.7.8) |
|:-----------------|:----------------------------|
| Probe missing STAR parts | `bei_probe.probe_star` → structure score + hints |
| Collective-only answers | ownership flag when only 「我们」 |
| Coach follow-up | `next_followup` prefers probe hints; scorecard stores `bei_probe` |

## Learned from interview-guide (Round 8)

Upstream: [Snailclimb/interview-guide](https://github.com/Snailclimb/interview-guide) (large Q bank; avoid repeats).

| interview-guide | Compass adaptation (v0.7.8) |
|:----------------|:----------------------------|
| Avoid re-asking | `question_dedup` hashes prior scorecard/oral questions |
| Pack filter | `build_pack` drops already-asked bank hits |

## Learned from open-resume (Round 9)

Upstream: [xitanggg/open-resume](https://github.com/xitanggg/open-resume) (one-page / ATS density).

| open-resume | Compass adaptation (v0.7.8) |
|:------------|:----------------------------|
| One-page budget | `resume_lint.lint_resume_density` in `ats_report.density` |
| Checklist | `one_page_density_ok` |

## Learned from jsonresume.org (Round 10)

Upstream: [jsonresume/jsonresume.org](https://github.com/jsonresume/jsonresume.org) (structured resume metrics).

| jsonresume | Compass adaptation (v0.7.8) |
|:-----------|:----------------------------|
| Key metrics | `resume_metrics` years/companies/projects/degree |
| Surface | diagnose + CLI `resume-metrics` |

## Learned from intervAI (Round 11)

Upstream: [xuan7-7/intervAI](https://github.com/xuan7-7/intervAI) (practice history rollup).

| intervAI | Compass adaptation (v0.7.8) |
|:---------|:----------------------------|
| Cross-session stats | `practice_stats.practice_rollup` |
| Desk / CLI | desk overview + `practice-stats` |

## Learned from IntervAI-xuanyiying (Round 12)

Upstream: [xuanyiying/IntervAI](https://github.com/xuanyiying/IntervAI) (interviewer personas).

| IntervAI | Compass adaptation (v0.7.8) |
|:---------|:----------------------------|
| Persona tones | `interview_persona.pick_persona` → pack + opening Q |
| Pressure vs coach | skip/fatal → challenging; HR/intern → hr |

## Learned from career-ops leftover (Round 13)

Upstream: [santifer/career-ops](https://github.com/santifer/career-ops) (posting legitimacy / ATS hosts).

| career-ops | Compass adaptation (v0.7.8) |
|:-----------|:----------------------------|
| ATS URL detect | `posting_liveness.detect_ats` (greenhouse/lever/ashby/workday) |
| Stale posting | age > 45d → cap strong/plausible → exploratory |
| JD fields | `ParsedJD.url` / `posted_at`; `match.json.posting_liveness` |

**Still deferred** (pre-0.8): A–G LLM rubric golden harness, live HTTP liveness probe.

## Learned from compas.txt P0–P2 (v0.8.0)

Source gap list: `projects/oss_competitors/compas.txt`.

| Priority | Gap | Compass adaptation |
|:---------|:----|:-------------------|
| P0 | ATS board scan | `ats_scan` + `discover --source ats` (Greenhouse/Lever/Ashby public JSON) |
| P0 | A–F / 1–5 score | `grade` on `match.json` (deterministic from matrix + gates) |
| P0 | `.env.example` | Already present (docs corrected) |
| P0 | PDF → resume | `resume-import` heuristic JSON Resume subset |
| P1 | Batch match | `batch-match` → `batches/*/summary.json` |
| P1 | Storybank | `storybank` + pack `stories[]` |
| P1 | Transcript import | `transcript-import` → oral_log + scorecard |
| P1 | Offer decision | `offer` six-dim user scores + compare.md |
| P1 | Report center | `practice-stats --export` |
| P2 light | Negotiate | `negotiate` local templates (**no live salary**) |
| P2 light | Calibration | `calibrate record|report` |

**Opt-in / local (v0.12–0.13)**: auth HTML collect with `--i-accept-tos-risk`; local Job Warehouse + MCP `jobs_search` (not hosted clover dump); Desk `/metrics` + `obs slo` APM export.

## Learned from compas.txt refresh (v0.9.0)

New analysis still labeled ATS/Offer/calibrate as “blank”; v0.8 already had skeletons. v0.9 closes the **delta**:

| Item | Adaptation |
|:-----|:-----------|
| Job Spy UX | `scout --keyword/--location` + `POST /api/scout` |
| 100-pt evidence score | `grade.parts` + `display`「综合匹配度：N/100（X级）」 |
| Calibrate narrative | `narrative_hits` + `band_accuracy`; `diagnose --calibrate` |
| Offer market line | user `market_p50` → vs_p50 高/齐/低（no Level.fyi scrape） |
| Story Vault | SQLite + tags + `storybank recommend` |
| Mentor PDF | `export-report --mentor` |

## Learned from compas.txt matrix refresh (v0.10.0)

Latest matrix still marked scout/grade/story/calibrate as missing — those shipped in v0.8–0.9. True gaps closed here:

| Item | Adaptation |
|:-----|:-----------|
| `batch --jobs urls.txt` | parallel URL/board-spec match |
| Contact mining | `research` local checklist (no LinkedIn) |
| Root-cause coaching | `scorecard roots` / aggregate.root_causes |
| Big-tech packs | `company_packs.jsonl` + `--company` |
| Observability | `obs status\|tail` + audit.jsonl |

## Learned from v0.11–v0.13 execution

| Item | Adaptation |
|:-----|:-----------|
| Transcript formats | `detect_format` otter/zoom/grain/teams/tactiq |
| Anki | `anki export` TSV |
| 面经 | `experience_bank` + pack inject |
| Progress curves | practice_center Progress |
| Alerts | `obs alerts` |
| batch board | `batch board` |
| Login-state | `session` + auth_collect (opt-in) |
| 十万岗 | local warehouse FTS + MCP |
| Enterprise APM | spans / prom / slo |

## Learned from compas.txt core-gap refresh (v0.14.0)

Analysis matrix still marks batch/transcript/report/obs as ❌ — **stale vs v0.10–0.13**. True narrative gaps closed:

| Item | Adaptation |
|:-----|:-----------|
| 8-stage training | `train` curriculum |
| Story combo optimize | `storybank compose` |
| Dashboard TUI | `pipeline board` |
| Comp benchmarks | `comp lookup` + MCP |
| Pick Don't Edit | `resume-pick` |
| 面经标准答案补全 | `experience complete` |

## Out of scope (intentional)

| Item | Why |
|:-----|:----|
| Camera proctoring | Privacy / job-seeker positioning |
| Hosted 18万岗 SaaS | Local warehouse instead |
| Credential stuffing / captcha farms | Compliance |
| Enterprise recruiter SaaS | Dilutes focus |
| LoRA fine-tune | Ops + compliance cost |
| LangGraph rewrite | `next_followup` suffices |
| Gradio as primary UX | Replaced by Web |

## Acceptance (v0.6)

| Metric | Target |
|:-------|:-------|
| `.env.example` + README memory | No-key Demo in 5 minutes |
| Graph filters | Evidence-only filter works after fixtures pipeline |
| `rag-eval` | Prints hit@k on fixture queries |
| `/api/asr` | Clear warning without `[asr]`; works when installed |
