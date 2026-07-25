"""Interview transcript import (Otter/Zoom/Grain-ish) → oral_log (compas.txt P1)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


_SPEAKER_RE = re.compile(
    r"^(?:"
    r"(?:\[\d{1,2}:\d{2}(?::\d{2})?\])\s*"  # [mm:ss]
    r"|(?:\d{1,2}:\d{2}(?::\d{2})?\s+)"
    r")?"
    r"(?P<who>Interviewer|Candidate|Host|Guest|面试官|候选人|HR|Me|You|[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"
    r"\s*[:：]\s*(?P<text>.+)$"
)


def parse_transcript(text: str) -> list[dict]:
    """Normalize transcript lines into {role, text} turns."""
    turns: list[dict] = []
    pending_role = None
    buf: list[str] = []

    def flush():
        nonlocal buf, pending_role
        if pending_role and buf:
            turns.append({"role": pending_role, "text": " ".join(buf).strip()})
        buf = []

    for raw in (text or "").splitlines():
        ln = raw.strip()
        if not ln:
            continue
        m = _SPEAKER_RE.match(ln)
        if m:
            flush()
            who = m.group("who").lower()
            if who in ("interviewer", "host", "面试官", "hr") or "interviewer" in who:
                pending_role = "interviewer"
            elif who in ("candidate", "me", "you", "guest", "候选人"):
                pending_role = "candidate"
            else:
                # alternate unknown speakers: odd→interviewer
                pending_role = "interviewer" if len(turns) % 2 == 0 else "candidate"
            buf = [m.group("text").strip()]
        else:
            if pending_role is None:
                pending_role = "interviewer" if len(turns) % 2 == 0 else "candidate"
            buf.append(ln)
    flush()
    return turns


def turns_to_qa_pairs(turns: list[dict]) -> list[dict]:
    """Pair interviewer questions with following candidate answers."""
    pairs: list[dict] = []
    i = 0
    while i < len(turns):
        t = turns[i]
        if t["role"] == "interviewer":
            q = t["text"]
            a = ""
            if i + 1 < len(turns) and turns[i + 1]["role"] == "candidate":
                a = turns[i + 1]["text"]
                i += 2
            else:
                i += 1
            pairs.append({"question": q, "answer": a})
        else:
            # orphan candidate line
            pairs.append({"question": "(prior)", "answer": t["text"]})
            i += 1
    return pairs


def import_transcript(
    root: Path,
    job_id: str,
    text: str,
    *,
    sync_scorecard: bool = True,
) -> dict:
    root = Path(root)
    turns = parse_transcript(text)
    pairs = turns_to_qa_pairs(turns)
    out_dir = root / "interviews" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "oral_log.jsonl"
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with log_path.open("a", encoding="utf-8") as f:
        for n, p in enumerate(pairs, 1):
            row = {
                "ts": ts,
                "turn": n,
                "source": "transcript_import",
                "question": p["question"],
                "q": p["question"],
                "answer": p["answer"],
                "a": p["answer"],
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out_dir / "transcript_turns.json").write_text(
        json.dumps({"turns": turns, "pairs": len(pairs)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    scorecard = None
    if sync_scorecard and pairs:
        from .scorecard import import_oral_log

        scorecard = import_oral_log(root, job_id)
    return {
        "job_id": job_id,
        "turns": len(turns),
        "pairs": len(pairs),
        "oral_log": str(log_path),
        "scorecard_answers": len((scorecard or {}).get("answers") or []) if scorecard else 0,
    }
