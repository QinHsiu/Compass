"""Path helpers for Compass content root."""

from __future__ import annotations

import os
from pathlib import Path


def content_root(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("COMPASS_ROOT")
    if env:
        return Path(env).resolve()
    # packages/compass-core/compass_core -> repo content/
    here = Path(__file__).resolve()
    repo = here.parents[3]  # Compass/
    candidate = repo / "content"
    if candidate.is_dir():
        return candidate
    return Path.cwd() / "content"


def ensure_dirs(root: Path) -> None:
    for name in (
        "profile",
        "evidence",
        "jobs",
        "resumes",
        "interviews",
        "diagnoses",
        "track",
        "fixtures",
    ):
        (root / name).mkdir(parents=True, exist_ok=True)
