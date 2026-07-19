# Contributing to Compass

## Setup checklist

```bash
python -m pip install -e "packages/compass-core[dev,studio,live,rag,pdf]"
python -m pip install -r apps/studio/requirements.txt
python -m pip install -r apps/interview-live/requirements.txt
cd packages/compass-core && pytest -q
```

Windows: `.\scripts\install.ps1`

## Run

```bash
python -m compass_core.cli studio --root content --port 7860
python -m compass_core.cli live --root content --port 8766
# Demo button when: set COMPASS_DEMO=1
```

## Privacy red lines

Never commit under `content/` except fixtures, `.gitkeep`, and examples.  
Blocked: resumes, interviews, diagnoses, track boards, uploads, RAG indexes, oral logs.

## Labels

| Label | Use |
|:------|:----|
| `good first issue` | See [docs/GOOD_FIRST_ISSUES.md](docs/GOOD_FIRST_ISSUES.md) |
| `docs` | Documentation only |
| `bank` | Question bank entries |
| `ui` | Studio / Live front-end |
| `core` | compass-core logic |

## LLM (optional)

```bash
set OPENAI_API_KEY=...
set COMPASS_LLM_PROVIDER=openai
set COMPASS_MODEL=gpt-4o-mini
python -m compass_core.cli llm-info
```

Without a key, follow-ups use rule templates.

## PRs

1. Keep changes focused; match existing style.
2. Add/adjust tests for gate, followup, timeline, export.
3. Update CHANGELOG for user-facing changes.
4. Do not include personal job-search artifacts.
