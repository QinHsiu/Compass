"""Application tracking board."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

VALID = ("wishlist", "applied", "interviewing", "offer", "rejected", "ghosted")


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
    save_board(root, board)
    return found
