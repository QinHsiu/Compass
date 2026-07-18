# Contributing to Compass

## Setup

```bash
python -m pip install -e "packages/compass-core[dev,studio,live,rag]"
python -m pip install -r apps/studio/requirements.txt
python -m pip install -r apps/interview-live/requirements.txt
```

Windows: `.\scripts\install.ps1`

## Run

```bash
# Studio
python -m compass_core.cli studio --root content --port 7860

# Interview Live
python -m compass_core.cli live --root content --port 8766

# Tests
cd packages/compass-core && pytest -q
```

## Privacy

Never commit files under `content/` except fixtures and `.gitkeep` / examples.  
`.gitignore` blocks resumes, interviews, diagnoses, track boards, and RAG indexes.

## LLM (optional)

```bash
set OPENAI_API_KEY=...
set COMPASS_LLM_PROVIDER=openai   # or deepseek / ollama
set COMPASS_MODEL=gpt-4o-mini
python -m compass_core.cli llm-info
```

Without a key, adaptive follow-ups use rule templates.

## PRs

1. Keep changes focused; match existing style.
2. Add/adjust tests for core behavior (gate, followup, timeline).
3. Update CHANGELOG if user-facing.
4. Do not include personal job-search artifacts.
