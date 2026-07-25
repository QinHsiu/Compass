"""Dedup previously asked bank questions (interview-guide Round 8)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def normalize_question(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip().lower())
    t = re.sub(r"[？?！!。．.]+$", "", t)
    return t


def question_hash(text: str) -> str:
    return hashlib.sha1(normalize_question(text).encode("utf-8")).hexdigest()[:16]


def load_asked_hashes(root: Path, job_id: str | None = None) -> set[str]:
    """Collect hashes from scorecards (+ oral logs) across jobs or one job."""
    root = Path(root)
    iv = root / "interviews"
    if not iv.is_dir():
        return set()
    dirs = [iv / job_id] if job_id else [p for p in iv.iterdir() if p.is_dir()]
    hashes: set[str] = set()
    for d in dirs:
        sc = d / "scorecard.json"
        if sc.is_file():
            data = json.loads(sc.read_text(encoding="utf-8"))
            for a in data.get("answers") or []:
                q = a.get("question") or ""
                if q:
                    hashes.add(question_hash(q))
        oral = d / "oral_log.jsonl"
        if oral.is_file():
            for line in oral.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                q = str(row.get("q") or row.get("question") or "")
                if q:
                    hashes.add(question_hash(q))
    return hashes


def filter_bank_hits(hits: list[dict], asked: set[str]) -> list[dict]:
    out: list[dict] = []
    for h in hits:
        q = str(h.get("q_display") or h.get("q_zh") or h.get("q") or "")
        if question_hash(q) in asked:
            continue
        out.append(h)
    return out
