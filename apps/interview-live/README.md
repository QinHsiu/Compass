# Compass Web

Primary UI: **FastAPI + WebSocket** full workbench (replaces Gradio as default).

```bash
python -m compass_core.cli web --root content --port 8766
# → http://127.0.0.1:8766/
```

## Channels

| Path | Role |
|:-----|:-----|
| `/ws/app` | ingest / pipeline / demo / bank / export |
| `/ws/interview/{job_id}` | realtime Q&A + coding check |
| `/api/ingest` | multipart file upload |
| `/timeline` | evidence graph |

Gradio Studio remains optional: `python -m compass_core.cli studio` or `docker compose --profile gradio up`.
