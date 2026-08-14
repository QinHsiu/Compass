# Interview question bank sources / 题库来源备注

Compass ships a **curated, searchable** question bank under `bank.jsonl`.
Entries are rewritten for retrieval (short stem + tags + topic). Each record
has a `source` field pointing to the originating open project or “Compass curated”.

## Primary open-source references (MIT / permissive)

| Source | Scope | License | URL |
|:-------|:------|:--------|:----|
| h5bp/Front-end-Developer-Interview-Questions | Front-end HTML/CSS/JS | MIT | https://github.com/h5bp/Front-end-Developer-Interview-Questions |
| yangshun/tech-interview-handbook | Coding / system design / behavioral guidance | MIT | https://github.com/yangshun/tech-interview-handbook |
| DopplerHQ/awesome-interview-questions | Index of interview lists | various | https://github.com/DopplerHQ/awesome-interview-questions |
| JSON Resume community | Resume/interview prep adjacency | MIT | https://jsonresume.org/ |

## Policy

1. **Retrieval-first**: `/interview` merges JD keywords + evidence skills → top-N bank hits.
2. **Not a 面试鸭 clone**: we do not vendor 9000+ scraped 八股; we retrieve relevant subset + JD-specific questions.
3. Users may append `content/questions/extra.jsonl` (same schema) for private banks.
4. When answering in simulation, still require `evidence_id` for experiential claims.

## LLM / Agent bank (2026 focus)

| File | Role |
|:-----|:-----|
| `bank.jsonl` | General SWE bank |
| `llm_agent.jsonl` | LLM + Agent focus (seed + public crawl) |

Refresh:

```bash
python -m compass_core.cli crawl-llm --root content
```

Crawl sources (public raw only): see `compass_core/crawl_llm.py` `SOURCES`.
Seed questions are Compass-curated for RAG / Agent / tool-use / MCP / eval.

## Domain packs (2026-08)

| File | Pack id | Role |
|:-----|:--------|:-----|
| `cv_llm.jsonl` | `cv-llm` | AIGC / CV / LLM stems (Compass-rewritten) |
| `nlp.jsonl` | `nlp` | NLP engineer stems |
| `mldl.jsonl` | `mldl` | ML/DL concept stems |
| `algo.jsonl` | `algo` | Algorithm practice + `starter_code` |
| `company_packs.jsonl` | `curated-bigtech` | 大厂行为/技术追问（含百度/美团/华为/京东/滴滴） |

Refresh into a workspace:

```bash
python -m compass_core.cli import-questions --root content --source cv-llm
python -m compass_core.cli import-questions --root content --source nlp
python -m compass_core.cli import-questions --root content --source mldl
python -m compass_core.cli import-questions --root content --source algo
python -m compass_core.cli import-questions --root content --source curated-bigtech
python -m compass_core.cli import-questions --root content --source local --file path/to/extra.jsonl
python -m compass_core.cli rag-index --root content
```

## License / crawl policy

- **Not vendored:** `0voice/interview_internal_reference` (no license). CLI `--source voice-interview` is rejected.
- Topic URLs on curated rows are **inspiration citations**, not copies of those repositories.
- `doocs/leetcode`, `itcharge/AlgoNote`, `MisterBooo/LeetCodeAnimation` are linked, not copied.
- Users may import private JSONL into gitignored `content/questions/imported/`.
