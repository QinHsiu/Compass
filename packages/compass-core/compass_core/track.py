"""Application tracking board."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

VALID = ("wishlist", "applied", "interviewing", "offer", "rejected", "ghosted")

# Clover-style apply bands mapped onto match_explain.recommendation
BAND_POLICY = {
    "strong": {"suggested_action": "apply_now", "follow_up_days": 3, "note": "Apply with current resume"},
    "plausible": {
        "suggested_action": "tailor_then_apply",
        "follow_up_days": 2,
        "note": "Run /resume then apply",
    },
    "exploratory": {
        "suggested_action": "bridge_then_rematch",
        "follow_up_days": 7,
        "note": "/bridge then re-run match-explain",
    },
    "skip": {"suggested_action": "do_not_apply", "follow_up_days": None, "note": "Skip or only if fatal cleared"},
}


def load_board(root: Path) -> dict:
    path = root / "track" / "board.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": 1, "items": []}


def save_board(root: Path, board: dict) -> None:
    path = root / "track" / "board.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert(
    root: Path,
    job_id: str,
    status: str,
    note: str = "",
    company: str = "",
    title: str = "",
    *,
    match_band: str | None = None,
    matrix_score: float | None = None,
    confidence: str | None = None,
    suggested_action: str | None = None,
    follow_up_due: str | None = None,
    match_synced_at: str | None = None,
) -> dict:
    if status not in VALID:
        raise ValueError(f"status must be one of {VALID}")
    board = load_board(root)
    items = board.setdefault("items", [])
    found = None
    for it in items:
        if it.get("job_id") == job_id:
            found = it
            break
    today = date.today().isoformat()
    if found is None:
        # try enrich from job folder
        jd_path = root / "jobs" / job_id / "jd.json"
        if jd_path.is_file():
            jd = json.loads(jd_path.read_text(encoding="utf-8"))
            company = company or jd.get("company", "")
            title = title or jd.get("title", "")
        found = {
            "job_id": job_id,
            "company": company,
            "title": title,
            "status": status,
            "note": note,
            "updated": today,
            "history": [{"status": status, "date": today, "note": note}],
        }
        items.append(found)
    else:
        found["status"] = status
        found["updated"] = today
        if note:
            found["note"] = note
        if company:
            found["company"] = company
        if title:
            found["title"] = title
        found.setdefault("history", []).append(
            {"status": status, "date": today, "note": note}
        )

    if match_band is not None:
        found["match_band"] = match_band
        found["follow_up_due"] = follow_up_due  # may be None for skip
    elif follow_up_due is not None:
        found["follow_up_due"] = follow_up_due
    if matrix_score is not None:
        found["matrix_score"] = matrix_score
    if confidence is not None:
        found["confidence"] = confidence
    if suggested_action is not None:
        found["suggested_action"] = suggested_action
    if match_synced_at is not None:
        found["match_synced_at"] = match_synced_at

    save_board(root, board)
    return found


def seed_from_match(root: Path, job_id: str, *, status: str = "wishlist") -> dict:
    """Seed/update track item from match_explain recommendation band + cadence."""
    match_path = Path(root) / "jobs" / job_id / "match.json"
    if not match_path.is_file():
        raise FileNotFoundError(f"missing {match_path}")
    match = json.loads(match_path.read_text(encoding="utf-8"))
    explain = match.get("match_explain") or {}
    band = str(explain.get("recommendation") or "exploratory")
    policy = BAND_POLICY.get(band, BAND_POLICY["exploratory"])
    today = date.today()
    due = None
    days = policy.get("follow_up_days")
    if days is not None:
        due = (today + timedelta(days=int(days))).isoformat()

    note = policy["note"]
    # Keep existing user note if present and not empty — append band hint
    board = load_board(root)
    existing = next((i for i in board.get("items") or [] if i.get("job_id") == job_id), None)
    if existing and existing.get("note") and existing["note"] != note:
        note = f"{existing['note']} · {policy['note']}"

    return upsert(
        root,
        job_id,
        status=existing["status"] if existing and existing.get("status") in VALID else status,
        note=note,
        company=match.get("company") or "",
        title=match.get("title") or "",
        match_band=band,
        matrix_score=float(explain.get("matrix_score") or 0),
        confidence=str(explain.get("confidence") or "low"),
        suggested_action=policy["suggested_action"],
        follow_up_due=due,
        match_synced_at=today.isoformat(),
    )


def list_due(root: Path, as_of: date | None = None) -> list[dict]:
    """Items with follow_up_due on or before as_of (default today)."""
    as_of = as_of or date.today()
    out: list[dict] = []
    for it in load_board(root).get("items") or []:
        due = it.get("follow_up_due")
        if not due:
            continue
        try:
            d = date.fromisoformat(str(due)[:10])
        except ValueError:
            continue
        if d <= as_of:
            out.append(it)
    out.sort(key=lambda x: str(x.get("follow_up_due") or ""))
    return out
