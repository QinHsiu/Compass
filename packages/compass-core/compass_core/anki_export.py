"""Export Anki-importable TSV/JSON cards from vault, drills, packs, diagnose."""

from __future__ import annotations

import json
from pathlib import Path


def _card(front: str, back: str, tags: str = "") -> dict:
    return {"front": (front or "").strip(), "back": (back or "").strip(), "tags": tags}


def collect_cards(root: Path, *, job_id: str | None = None) -> list[dict]:
    root = Path(root)
    cards: list[dict] = []

    # story vault
    try:
        from .story_vault import list_stories

        for s in list_stories(root, limit=100):
            star = s.get("star") or {}
            if isinstance(star, str):
                try:
                    star = json.loads(star)
                except json.JSONDecodeError:
                    star = {}
            front = f"STAR ({s.get('id')}): {star.get('situation') or s.get('id')}"
            back = "\n".join(
                f"{k}: {star.get(k)}"
                for k in ("situation", "task", "action", "result")
                if star.get(k)
            ) or (s.get("answer_text") or "")
            if front and back:
                tags = " ".join(s.get("tags") or []) + " story"
                cards.append(_card(front, back, tags.strip()))
    except Exception:
        pass

    # company pack + experience bank drills
    company = title = None
    if job_id:
        jd_path = root / "jobs" / job_id / "jd.json"
        if jd_path.is_file():
            jd = json.loads(jd_path.read_text(encoding="utf-8"))
            company, title = jd.get("company"), jd.get("title")
    try:
        from .company_pack import search_company_pack

        for h in search_company_pack(company, title=title, limit=12):
            q = h.get("q") or h.get("question") or ""
            a = h.get("hint") or h.get("answer") or h.get("points") or ""
            if isinstance(a, list):
                a = "\n".join(str(x) for x in a)
            if q:
                cards.append(_card(q, str(a) or "(prep your STAR)", "company_pack"))
    except Exception:
        pass
    try:
        from .experience_bank import search_experience

        for h in search_experience(query=title or company or "ml", limit=12):
            q = h.get("q") or h.get("question") or ""
            a = h.get("answer_points") or h.get("hint") or ""
            if isinstance(a, list):
                a = "\n".join(str(x) for x in a)
            if q:
                cards.append(_card(q, str(a), "experience"))
    except Exception:
        pass

    # diagnose P0 actions
    if job_id:
        bridge = root / "diagnoses" / job_id / "bridge_plan.json"
        if not bridge.is_file():
            bridge = root / "diagnoses" / job_id / "report.json"
        if bridge.is_file():
            try:
                data = json.loads(bridge.read_text(encoding="utf-8"))
                actions = data.get("actions") or data.get("bridge") or []
                for a in actions:
                    if (a.get("priority") or "").upper() != "P0":
                        continue
                    what = a.get("what") or ""
                    proof = a.get("proof") or a.get("eta") or ""
                    if what:
                        cards.append(_card(f"P0 gap: {what}", str(proof), "diagnose"))
            except Exception:
                pass

    # bank hits from interview pack
    if job_id:
        pack_path = root / "interviews" / job_id / "pack.json"
        if pack_path.is_file():
            try:
                pack = json.loads(pack_path.read_text(encoding="utf-8"))
                for h in (pack.get("bank_hits") or [])[:20]:
                    q = h.get("q") or h.get("question") or ""
                    a = h.get("a") or h.get("answer") or h.get("hint") or ""
                    if q:
                        cards.append(_card(q, str(a) or "(drill aloud)", "bank"))
            except Exception:
                pass

    # dedupe by front
    seen = set()
    out = []
    for c in cards:
        key = c["front"][:200]
        if key in seen or not key:
            continue
        seen.add(key)
        out.append(c)
    return out


def export_anki(root: Path, *, job_id: str | None = None, label: str | None = None) -> dict:
    root = Path(root)
    cards = collect_cards(root, job_id=job_id)
    out_dir = root / "anki"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = label or job_id or "all"
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)[:48]
    tsv_path = out_dir / f"{safe}.txt"
    json_path = out_dir / f"{safe}.json"
    lines = []
    for c in cards:
        # Anki basic: front\tback\ttags
        front = c["front"].replace("\t", " ").replace("\n", "<br>")
        back = c["back"].replace("\t", " ").replace("\n", "<br>")
        tags = (c.get("tags") or "").replace("\t", " ")
        lines.append(f"{front}\t{back}\t{tags}")
    tsv_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    json_path.write_text(
        json.dumps({"count": len(cards), "cards": cards}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"count": len(cards), "tsv": str(tsv_path), "json": str(json_path)}
