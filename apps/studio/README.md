# Compass Studio

Interactive Gradio workbench: resume upload (PDF/image), JD pipeline, oral interview (TTS/ASR), LLM/Agent bank crawl.

```bash
pip install -e ../../packages/compass-core
pip install -r requirements.txt
# optional: pip install faster-whisper pytesseract python-docx

set COMPASS_ROOT=..\..\content   # Windows
python app.py
# → http://127.0.0.1:7860
```

Or: `python -m compass_core.cli studio`
