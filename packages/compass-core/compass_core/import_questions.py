"""Compliance-safe question import. Curated packs live in assets; user files in content/questions/imported/."""

from __future__ import annotations

import json
from pathlib import Path

from .questions import ASSETS, validate_record

ALLOWED_SOURCES: tuple[str, ...] = ("curated-bigtech", "cv-llm", "nlp", "mldl", "algo", "local")
BLOCKED_SOURCES: tuple[str, ...] = ("voice-interview", "0voice", "interview_internal_reference")

_CURATED_COPY = {
    "cv-llm": "cv_llm.jsonl",
    "nlp": "nlp.jsonl",
    "mldl": "mldl.jsonl",
    "algo": "algo.jsonl",
    "curated-bigtech": "company_packs.jsonl",
}


def _read_jsonl(path: Path) -> tuple[list[dict], int]:
    rows: list[dict] = []
    skipped_malformed = 0
    if not path.is_file():
        return rows, skipped_malformed
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            rows.append(validate_record(json.loads(ln)))
        except json.JSONDecodeError:
            skipped_malformed += 1
    return rows, skipped_malformed


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    return path


def import_questions(
    root: Path,
    *,
    source: str,
    file: Path | None = None,
    rebuild_index: bool = False,
) -> dict:
    src = (source or "").strip().lower()
    if src in BLOCKED_SOURCES:
        raise ValueError(
            f"source {src} is blocked (no redistributable license). "
            "Use --source curated-bigtech for Compass-rewritten 大厂 stems."
        )
    if src not in ALLOWED_SOURCES:
        raise ValueError(f"unknown source {src}; allowed={list(ALLOWED_SOURCES)}")

    if src == "local":
        if file is None:
            raise ValueError("local import requires file=")
        src_file = Path(file)
        if not src_file.is_file():
            raise ValueError(f"local import file not found: {src_file}")
        rows, skipped_malformed = _read_jsonl(src_file)
        for r in rows:
            r["pack"] = r.get("pack") or "local"
    else:
        asset_name = _CURATED_COPY[src]
        rows, skipped_malformed = _read_jsonl(ASSETS / asset_name)
        for r in rows:
            r["pack"] = r.get("pack") or src

    dest = Path(root) / "questions" / "imported" / f"{src}.jsonl"
    _write_jsonl(dest, rows)
    info: dict = {
        "ok": True,
        "source": src,
        "count": len(rows),
        "path": str(dest),
        "skipped_malformed": skipped_malformed,
    }
    if rebuild_index:
        from .rag import index_questions

        info["rag"] = index_questions(root)
    return info
