"""Hugging Face Spaces entrypoint — demo fixtures only."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("COMPASS_DEMO", "1")
os.environ.setdefault("COMPASS_ROOT", str(ROOT / "content"))
os.environ.setdefault("COMPASS_PORT", "7860")

content = ROOT / "content"
fixtures = content / "fixtures" / "demo" / "evidence"
ev = content / "evidence"
ev.mkdir(parents=True, exist_ok=True)
if fixtures.is_dir() and not (ev / "ev_featstore_latency.md").is_file():
    for p in fixtures.glob("*.md"):
        shutil.copy2(p, ev / p.name)

sys.path.insert(0, str(ROOT / "packages" / "compass-core"))
sys.path.insert(0, str(ROOT / "apps" / "studio"))

from compass_core.evidence import build_index  # noqa: E402

build_index(content)

import app as studio_app  # noqa: E402  # apps/studio/app.py

demo = studio_app.build_app()

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ["COMPASS_PORT"]),
        theme=studio_app.gr.themes.Default(primary_hue="blue", neutral_hue="slate"),
        css=studio_app.CSS,
    )
