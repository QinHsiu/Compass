# Interview Live

Realtime interview over WebSocket + browser Web Speech (ASR/TTS) + Monaco coding tab + PWA.

```bash
pip install -r requirements.txt
pip install -e ../../packages/compass-core
set COMPASS_ROOT=..\..\content
python main.py
# http://127.0.0.1:8766
```

Or: `python -m compass_core.cli live --root content --port 8766`
