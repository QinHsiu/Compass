# Competitive positioning / 竞品对照

Source: [compass_r.txt](../../compass_r.txt) (2026-07 interview-sim wave, refreshed).

## Status

Technical gaps from the previous wave (**Docker / multi-LLM / Live WS / RAG / adaptive follow-up**) are **closed**.  
Current focus: **evidence graph UX**, **demo onboarding**, **report export**, **mobile polish**, **community cold-start**.

## Moat (keep)

| Differentiator | Compass |
|:---------------|:--------|
| Evidence gate | Claims need `evidence_id` |
| Gap compass 4Q | Evidence / Narrative / Skill / Process |
| Multi-form | **Compass Web (WS)** + optional Gradio + Skill + CLI + MCP |
| Local-first | Data under `content/` |
| Evidence graph | SVG graph: evidence → resume → interview |

## Capability snapshot

| Capability | Compass | Notes vs peers |
|:-----------|:-------:|:---------------|
| Full loop upload→diagnose | **✅** | Longest chain |
| Realtime voice | **✅ Live WS** | Not LiveKit; Web Speech first |
| Adaptive follow-up | **✅** | LLM or rules |
| RAG bank | **✅ Chroma** | Rare among peers |
| Evidence graph | **✅** | Differentiator |
| Report HTML/PDF | **✅** | `export-report` |
| Docker / Demo | **✅** | compose + HF fixtures |
| Community / Stars | building | launch article + good-first issues |

## Out of scope (intentional)

| Item | Why |
|:-----|:----|
| Camera proctoring (MediaPipe) | Conflicts with local privacy positioning |
| Enterprise recruiter SaaS | Dilutes job-seeker focus |
| LoRA / industry fine-tune | Ops + compliance cost; BYOK + RAG enough |
| LangGraph multi-agent rewrite | `next_followup` + rules suffice |
| Full Gradio→React rewrite | Live covers realtime; cost too high |
| 200+ career mini-tools | Sproutern-style sprawl |

## Acceptance (v0.5)

| Metric | Target |
|:-------|:-------|
| Evidence graph | SVG + click highlight; ≥1 edge after fixture pipeline |
| Demo | `COMPASS_DEMO=1` one-click fixtures pipeline |
| Export | `compass export-report` → HTML (+ PDF if fpdf2) |
| Mobile | 375px Studio/Live usable |
| Community | launch article + GOOD_FIRST_ISSUES + issue templates |
