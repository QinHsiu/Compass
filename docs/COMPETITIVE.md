# Competitive positioning / 竞品对照

Sources: early resume-tool survey + [compass_r.txt](../../compass_r.txt) interview-sim wave (DeepInterview, alading, OfferCat, Lingwu, …).

## Moat (keep)

| Differentiator | Compass |
|:---------------|:--------|
| Evidence gate | Resume/interview claims need `evidence_id` |
| Gap compass 4Q | Evidence / Narrative / Skill / Process + 做什么/证明物/耗时 |
| Multi-form | Gradio Studio + Interview Live + Skill + CLI + MCP |
| Local-first | Data under `content/`, no required cloud account |

## Interview-sim wave (compass_r.txt)

| Capability | Compass | DeepInterview | alading | OfferCat | Lingwu | InterviewPrep.AI |
|:-----------|:-------:|:-------------:|:-------:|:--------:|:------:|:----------------:|
| Resume→JD→Patch→Diagnose | **✅** | partial | ❌ | partial | ❌ | resume+interview |
| Evidence gate | **✅** | ❌ | ❌ | ❌ | ❌ | ❌ |
| Texttime voice | **Live WS + Web Speech** | LiveKit | WebSocket | voice | voice | voice |
| Adaptive follow-up | **✅** | ✅ | partial | partial | ✅ | partial |
| Multi-LLM BYOK | **✅ OpenAI-compatible** | ✅ | OpenAI | vLLM | ✅ | ✅ |
| RAG bank | **Chroma** | ❌ | ❌ | BGE | ❌ | ❌ |
| Docker / Demo | **compose + HF Space card** | Docker | demo | ❌ | Docker | APK |
| Enterprise HR | ❌ (out of scope) | ❌ | ❌ | ❌ | ✅ | dual-mode |
| Proctoring camera | ❌ (privacy) | ❌ | ❌ | ❌ | ❌ | MediaPipe |

## Resume-tool wave (earlier)

| Capability | FaceTomato | Job OK | JadeAI | 面试鸭 | **Compass** |
|:-----------|:----------:|:------:|:------:|:------:|:-----------:|
| Resume themes | mid | low | 50+ | ❌ | 12 + JSON Resume |
| Question bank ops | DIY | low | ❌ | 9k+ | curated + crawl + RAG |
| Track | ❌ | ✅ | ❌ | ❌ | ✅ |

## Intentionally skipped

- 200+ career mini-tools (Sproutern)
- Default enterprise recruiter SaaS (Lingwu)
- Camera proctoring (conflicts with local privacy positioning)
- Full Gradio→React rewrite (Live app covers realtime gap)

## Acceptance (post Wave A–C)

| Metric | Target |
|:-------|:-------|
| `docker compose up` | Studio + Live reachable |
| Adaptive follow-up | LLM or rules; gate on each answer |
| `rag-index` + `--semantic` | semantic hits when chromadb installed |
| Timeline / Monaco / PWA | Live UI available |
