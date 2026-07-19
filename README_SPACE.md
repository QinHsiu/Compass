---
title: Compass Job Compass
emoji: 🧭
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app_hf.py
pinned: false
license: mit
---

# Compass — Evidence-Driven Job Compass (Demo)

**Demo only.** Loads anonymous fixtures under `content/fixtures/demo`.

- Click **一键 Demo 流水线（fixtures）** on the「智能求职」tab (`COMPASS_DEMO=1`).
- **Do not upload real resumes** to public Spaces.
- **Interview Live** (WebSocket / 证据图谱) is not on HF — run locally:

```bash
docker compose up --build
# Studio http://localhost:7860
# Live  http://localhost:8766  → /timeline 证据图谱
```

See [README.md](README.md), [docs/COMPLIANCE.md](docs/COMPLIANCE.md), [docs/launch_article_zh.md](docs/launch_article_zh.md).
