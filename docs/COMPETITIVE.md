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
