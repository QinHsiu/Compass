# Competitive positioning / 竞品对照

Source: [compass_r.txt](../../compass_r.txt) (2026-07 eval refresh).

## Status

Core loop and stack (Docker / multi-LLM / WebSocket Web / RAG / follow-up / evidence graph) are **in place**.  
UX primary surface is **Compass Web**, not Gradio. v0.6 focuses on **config onboarding**, **interactive graph**, **ASR fallback**, **RAG measurability**, and **community cold-start**.

## Moat (keep)

| Differentiator | Compass |
|:---------------|:--------|
| Evidence gate | Claims need `evidence_id` |
| Gap compass 4Q | Evidence / Narrative / Skill / Process |
| Multi-form | **Compass Web** + optional Gradio + Skill + CLI + MCP |
| Local-first | Data under `content/` |
| Evidence graph | Interactive filter / search / detail |

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
