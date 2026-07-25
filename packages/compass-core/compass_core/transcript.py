"""Interview transcript import — multi-format detect (Otter/Zoom/Grain/Teams/Tactiq)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


_SPEAKER_RE = re.compile(
    r"^(?:"
    r"(?:\[\d{1,2}:\d{2}(?::\d{2})?\])\s*"
    r"|(?:\d{1,2}:\d{2}(?::\d{2})?\s+)"
    r")?"
    r"(?P<who>Interviewer|Candidate|Host|Guest|面试官|候选人|HR|Me|You|[A-Z][a-z]+(?:\s[A-Z][a-z]+)?)"
    r"\s*[:：]\s*(?P<text>.+)$"
)

# Zoom: "John Doe 00:12:03"
_ZOOM_RE = re.compile(
    r"^(?P<who>.+?)\s+(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)\s*$"
)
# Otter / Tactiq: "Speaker 1  0:12" or "00:12 Speaker"
_OTTER_RE = re.compile(
    r"^(?:(?P<ts>\d{1,2}:\d{2}(?::\d{2})?)\s+)?(?P<who>Speaker\s*\d+|未知说话人|.+?)"
    r"(?:\s+(?P<ts2>\d{1,2}:\d{2}(?::\d{2})?))?\s*$",
    re.I,
)
# Teams: "John Doe   12:03 PM"
_TEAMS_RE = re.compile(
    r"^(?P<who>.+?)\s{2,}(?P<ts>\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)\s*$",
    re.I,
)
# Grain: "00:12:03 — Name"
_GRAIN_RE = re.compile(
    r"^(?P<ts>\d{1,2}:\d{2}:\d{2})\s*[—\-]\s*(?P<who>.+)$"
)


def detect_format(text: str) -> str:
    """Heuristic format id: otter|zoom|grain|teams|tactiq|generic."""
    sample = "\n".join((text or "").splitlines()[:80])
    low = sample.lower()
    if "tactiq" in low or "exported from tactiq" in low:
        return "tactiq"
    if "grain.com" in low or _GRAIN_RE.search(sample):
        grain_hits = sum(1 for ln in sample.splitlines() if _GRAIN_RE.match(ln.strip()))
        if grain_hits >= 2:
            return "grain"
    if "microsoft teams" in low or "transcript" in low and "am" in low and "pm" in low:
        teams_hits = sum(1 for ln in sample.splitlines() if _TEAMS_RE.match(ln.strip()))
        if teams_hits >= 2:
            return "teams"
    zoom_hits = sum(1 for ln in sample.splitlines() if _ZOOM_RE.match(ln.strip()))
    if "zoom" in low or zoom_hits >= 3:
        # distinguish zoom header lines from otter
        if zoom_hits >= 3:
            return "zoom"
    otter_hits = sum(
        1
        for ln in sample.splitlines()
        if re.match(r"^speaker\s*\d+", ln.strip(), re.I)
        or re.match(r"^\d{1,2}:\d{2}\s+\S+", ln.strip())
    )
    if "otter" in low or otter_hits >= 2:
        return "otter"
    if _SPEAKER_RE.search(sample):
        return "generic"
    return "generic"


def _role_from_who(who: str, turn_idx: int) -> str:
    w = (who or "").strip().lower()
    if w in ("interviewer", "host", "面试官", "hr") or "interviewer" in w:
        return "interviewer"
    if w in ("candidate", "me", "you", "guest", "候选人", "self"):
        return "candidate"
    if w.startswith("speaker"):
        # Speaker 1 → interviewer, Speaker 2 → candidate (common Otter)
        m = re.search(r"(\d+)", w)
        n = int(m.group(1)) if m else 1
        return "interviewer" if n % 2 == 1 else "candidate"
    return "interviewer" if turn_idx % 2 == 0 else "candidate"


def _parse_block_format(text: str, header_re: re.Pattern) -> list[dict]:
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
        m = header_re.match(ln)
        if m:
            flush()
            who = m.groupdict().get("who") or ""
            pending_role = _role_from_who(who, len(turns))
            buf = []
            continue
        # also allow "Name: text" inline
        sm = _SPEAKER_RE.match(ln)
        if sm:
            flush()
            pending_role = _role_from_who(sm.group("who"), len(turns))
            buf = [sm.group("text").strip()]
            continue
        if pending_role is None:
            pending_role = _role_from_who("", len(turns))
        buf.append(ln)
    flush()
    return turns


def parse_transcript(text: str, *, fmt: str | None = None) -> list[dict]:
    """Normalize transcript lines into {role, text} turns."""
    fmt = fmt or detect_format(text)
    if fmt == "grain":
        return _parse_block_format(text, _GRAIN_RE)
    if fmt == "teams":
        return _parse_block_format(text, _TEAMS_RE)
    if fmt in ("zoom", "otter", "tactiq"):
        # Zoom/Otter: speaker+time on its own line, then body
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
            if fmt == "zoom" and _ZOOM_RE.match(ln):
                flush()
                who = _ZOOM_RE.match(ln).group("who")
                pending_role = _role_from_who(who, len(turns))
                buf = []
                continue
            if fmt in ("otter", "tactiq"):
                if re.match(r"^speaker\s*\d+", ln, re.I) or (
                    re.match(r"^\d{1,2}:\d{2}", ln) and len(ln) < 40
                ):
                    flush()
                    who_m = re.match(r"^(speaker\s*\d+)", ln, re.I)
                    who = who_m.group(1) if who_m else ln
                    pending_role = _role_from_who(who, len(turns))
                    buf = []
                    continue
            sm = _SPEAKER_RE.match(ln)
            if sm:
                flush()
                pending_role = _role_from_who(sm.group("who"), len(turns))
                buf = [sm.group("text").strip()]
                continue
            if pending_role is None:
                pending_role = _role_from_who("", len(turns))
            buf.append(ln)
        flush()
        if turns:
            return turns

    # generic Speaker: text
    turns: list[dict] = []
    pending_role = None
    buf: list[str] = []

    def flush_g():
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
            flush_g()
            pending_role = _role_from_who(m.group("who"), len(turns))
            buf = [m.group("text").strip()]
        else:
            if pending_role is None:
                pending_role = _role_from_who("", len(turns))
            buf.append(ln)
    flush_g()
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
            pairs.append({"question": "(prior)", "answer": t["text"]})
            i += 1
    return pairs


def import_transcript(
    root: Path,
    job_id: str,
    text: str,
    *,
    sync_scorecard: bool = True,
    fmt: str | None = None,
) -> dict:
    root = Path(root)
    detected = fmt or detect_format(text)
    turns = parse_transcript(text, fmt=detected)
    pairs = turns_to_qa_pairs(turns)
    out_dir = root / "interviews" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / "oral_log.jsonl"
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with log_path.open("a", encoding="utf-8") as f:
        for n, p in enumerate(pairs, 1):
            from .answer_rubric import score_qa_rubric

            scores = score_qa_rubric(p["question"], p["answer"])
            row = {
                "ts": ts,
                "turn": n,
                "source": "transcript_import",
                "format": detected,
                "question": p["question"],
                "q": p["question"],
                "answer": p["answer"],
                "a": p["answer"],
                "scores": scores,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out_dir / "transcript_turns.json").write_text(
        json.dumps(
            {
                "detected_format": detected,
                "turns": turns,
                "pairs": len(pairs),
                "rubric": "answer_rubric.score_qa_rubric",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    scorecard = None
    if sync_scorecard and pairs:
        from .scorecard import import_oral_log

        scorecard = import_oral_log(root, job_id)
    agg = (scorecard or {}).get("aggregate") or {}
    return {
        "job_id": job_id,
        "detected_format": detected,
        "turns": len(turns),
        "pairs": len(pairs),
        "oral_log": str(log_path),
        "scorecard_answers": len((scorecard or {}).get("answers") or []) if scorecard else 0,
        "rubric_scores": agg.get("scores"),
    }
