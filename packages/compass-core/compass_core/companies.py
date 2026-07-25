"""Company registry for official career-page + ATS job discovery."""

from __future__ import annotations

import json
import re
from pathlib import Path

# Bundled seed (public career / ATS — no login boards)
_SEED = Path(__file__).resolve().parent / "assets" / "companies_seed.json"


def _parse_companies_yml(text: str) -> list[dict]:
    """Minimal YAML list of company maps."""
    companies: list[dict] = []
    cur: dict | None = None
    for raw in text.splitlines():
        ln = raw.rstrip()
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        if re.match(r"^companies\s*:", ln.strip()):
            continue
        m = re.match(r"^-\s+name\s*:\s*(.+)$", ln.strip())
        if m:
            if cur:
                companies.append(cur)
            cur = {"name": m.group(1).strip().strip("\"'")}
            continue
        m = re.match(r"^-\s+(.+)$", ln.strip())
        if m and ":" not in m.group(1):
            if cur:
                companies.append(cur)
            cur = {"name": m.group(1).strip().strip("\"'")}
            continue
        if cur is None:
            continue
        km = re.match(r"^(\w+)\s*:\s*(.+)$", ln.strip())
        if km:
            k, v = km.group(1), km.group(2).strip().strip("\"'")
            if k == "name" and "name" in cur and len(companies) == 0:
                pass
            cur[k] = v
    if cur:
        companies.append(cur)
    return companies


def load_companies(root: Path | None = None) -> list[dict]:
    """Load content/companies.yml|json, else bundled seed."""
    items: list[dict] = []
    if root:
        for name in ("companies.yml", "companies.yaml", "companies.json"):
            path = Path(root) / name
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if name.endswith(".json"):
                data = json.loads(text)
                items = data.get("companies") if isinstance(data, dict) else data
            else:
                items = _parse_companies_yml(text)
            break
    if not items and _SEED.is_file():
        data = json.loads(_SEED.read_text(encoding="utf-8"))
        items = data.get("companies") or []
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name") or "").strip()
        if not name:
            continue
        out.append(
            {
                "name": name,
                "career_url": (it.get("career_url") or it.get("url") or "").strip() or None,
                "ats": (it.get("ats") or it.get("board") or "").strip() or None,
                "tags": it.get("tags") or [],
                "location_hint": it.get("location") or "",
            }
        )
    return out
