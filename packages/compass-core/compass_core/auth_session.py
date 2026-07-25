"""Local auth session vault for opt-in authenticated collectors (compas v0.12).

User-provided Playwright storage_state / cookies only. No credential stuffing.
Requires --i-accept-tos-risk on scrape paths.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

SESSION_DIRNAME = "sessions"


def sessions_dir(root: Path) -> Path:
    d = Path(root) / SESSION_DIRNAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def import_session(
    root: Path,
    path: str | Path,
    *,
    name: str = "default",
) -> dict:
    """Copy storage_state.json or cookie JSON into content/sessions/."""
    src = Path(path)
    if not src.is_file():
        raise FileNotFoundError(src)
    data = json.loads(src.read_text(encoding="utf-8"))
    # Normalize: accept Playwright storage_state or {"cookies":[...]}
    if "cookies" not in data and isinstance(data, list):
        data = {"cookies": data, "origins": []}
    out = sessions_dir(root) / f"{name}.storage_state.json"
    meta = {
        "name": name,
        "imported_at": _utcnow(),
        "source": str(src),
        "cookie_count": len(data.get("cookies") or []),
        "path": str(out),
    }
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path = sessions_dir(root) / f"{name}.meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def session_status(root: Path, name: str = "default") -> dict:
    root = Path(root)
    state = sessions_dir(root) / f"{name}.storage_state.json"
    meta_path = sessions_dir(root) / f"{name}.meta.json"
    meta = {}
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return {
        "name": name,
        "present": state.is_file(),
        "path": str(state) if state.is_file() else None,
        "meta": meta,
        "tos_risk_env": os.environ.get("COMPASS_ACCEPT_TOS_RISK", ""),
        "note": "Scraping blocklisted hosts requires --i-accept-tos-risk",
    }


def load_storage_state(root: Path, name: str = "default") -> dict | None:
    path = sessions_dir(root) / f"{name}.storage_state.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def require_tos_risk(accept: bool) -> None:
    if accept:
        return
    if os.environ.get("COMPASS_ACCEPT_TOS_RISK", "").lower() in ("1", "true", "yes"):
        return
    raise PermissionError(
        "Authenticated scrape disabled. Pass --i-accept-tos-risk and keep sessions local. "
        "See docs/COMPLIANCE.md"
    )


def assert_url_allowed_or_risk(url: str, *, accept_tos_risk: bool = False) -> None:
    """Blocklist unless user accepted ToS risk for experimental auth collectors."""
    from .collectors import assert_url_allowed, load_blocklist
    from urllib.parse import urlparse

    try:
        assert_url_allowed(url)
        return
    except PermissionError:
        if not accept_tos_risk and os.environ.get("COMPASS_ACCEPT_TOS_RISK", "").lower() not in (
            "1",
            "true",
            "yes",
        ):
            raise
        host = (urlparse(url).hostname or "").lower()
        blocked = load_blocklist()
        # still require host to be in blocklist set for "auth path" (intentional opt-in)
        if not any(host == b or host.endswith("." + b) for b in blocked):
            raise
