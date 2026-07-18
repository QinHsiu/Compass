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
