"""Story combination optimizer — cover JD gaps with minimal strong STAR set."""

from __future__ import annotations

import json
from pathlib import Path

from .story_vault import list_stories, recommend_stories


def _tokens_from_job(root: Path, job_id: str) -> list[str]:
    jd_path = Path(root) / "jobs" / job_id / "jd.json"
    match_path = Path(root) / "jobs" / job_id / "match.json"
    toks: list[str] = []
    if jd_path.is_file():
        jd = json.loads(jd_path.read_text(encoding="utf-8"))
        toks.extend(str(x).lower() for x in (jd.get("keywords") or [])[:30])
        toks.extend(str(x).lower()[:40] for x in (jd.get("hard_requirements") or [])[:10])
    if match_path.is_file():
        m = json.loads(match_path.read_text(encoding="utf-8"))
        for g in m.get("hard_gaps") or []:
            toks.append(str(g).lower()[:40])
        for row in m.get("requirement_matrix") or []:
            if row.get("fit") in ("gap", "partial"):
                toks.append(str(row.get("text") or "")[:40].lower())
    # unique preserve order
    seen = set()
    out = []
    for t in toks:
        t = t.strip()
        if len(t) < 2 or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:40]


def _story_blob(s: dict) -> str:
    return " ".join(
        [
            json.dumps(s.get("star") or {}, ensure_ascii=False),
            " ".join(s.get("tags") or []),
            " ".join(s.get("evidence_ids") or []),
            str(s.get("id") or ""),
        ]
    ).lower()


def compose_stories(
    root: Path,
    job_id: str,
    *,
    limit: int = 5,
) -> dict:
    """Greedy set cover: pick strong stories maximizing uncovered JD tokens."""
    root = Path(root)
    tokens = _tokens_from_job(root, job_id)
    stories = list_stories(root, limit=200)
    if not stories:
        stories = recommend_stories(root, job_id=job_id, limit=20)
    uncovered = set(tokens)
    picked: list[dict] = []
    coverage_log: list[dict] = []

    pool = sorted(stories, key=lambda s: -int(s.get("strength") or 0))
    while uncovered and len(picked) < limit and pool:
        best = None
        best_cover: set[str] = set()
        best_score = -1
        for s in pool:
            if any(p.get("id") == s.get("id") for p in picked):
                continue
            blob = _story_blob(s)
            cover = {t for t in uncovered if t and t in blob}
            score = len(cover) * 10 + int(s.get("strength") or 0)
            if score > best_score:
                best_score = score
                best = s
                best_cover = cover
        if not best or best_score <= 0:
            # fill with strongest remaining
            for s in pool:
                if not any(p.get("id") == s.get("id") for p in picked):
                    best = s
                    best_cover = set()
                    break
        if not best:
            break
        picked.append(best)
        uncovered -= best_cover
        coverage_log.append(
            {
                "id": best.get("id"),
                "strength": best.get("strength"),
                "covers": sorted(best_cover)[:12],
                "tags": best.get("tags"),
            }
        )
        pool = [s for s in pool if s.get("id") != best.get("id")]

    out = {
        "job_id": job_id,
        "target_tokens": tokens,
        "uncovered": sorted(uncovered)[:20],
        "coverage_ratio": round(1 - (len(uncovered) / max(1, len(tokens))), 3) if tokens else 0.0,
        "combo": coverage_log,
        "stories": picked,
    }
    out_dir = Path(root) / "interviews" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "story_combo.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [
        f"# Story combo — `{job_id}`",
        "",
        f"coverage_ratio: **{out['coverage_ratio']}**",
        "",
        "| # | id | strength | covers |",
        "|---|----|----------|--------|",
    ]
    for i, c in enumerate(coverage_log, 1):
        md.append(
            f"| {i} | `{c['id']}` | {c.get('strength')} | "
            f"{', '.join(c.get('covers') or [])[:80] or '—'} |"
        )
    if uncovered:
        md += ["", "## Still uncovered", "", ", ".join(sorted(uncovered)[:15])]
    md_path = out_dir / "story_combo.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    out["path"] = str(path)
    out["md"] = str(md_path)
    return out
