"""Profile intake helper."""

from __future__ import annotations

import json
from pathlib import Path


TEMPLATE = {
    "version": 1,
    "name": "",
    "target_roles": [],
    "locations": [],
    "salary_band": "",
    "constraints": {
        "must_have": [],
        "avoid": [],
        "notice_period": "",
        "remote": None,
    },
    "links": {"github": "", "linkedin": "", "email": ""},
    "notes": "",
}


def save_profile(root: Path, data: dict | None = None) -> Path:
    root = Path(root)
    out = root / "profile" / "profile.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {**TEMPLATE, **(data or {})}
    if "constraints" in (data or {}) and isinstance(data["constraints"], dict):
        payload["constraints"] = {**TEMPLATE["constraints"], **data["constraints"]}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load_profile(root: Path) -> dict:
    path = Path(root) / "profile" / "profile.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return dict(TEMPLATE)
