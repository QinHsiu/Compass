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

## Out of scope (intentional)

| Item | Why |
|:-----|:----|
| Camera proctoring | Privacy / job-seeker positioning |
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
