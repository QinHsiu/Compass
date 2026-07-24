"""Profile constraint gate for match bands (prisma-ai Round 6).

Zero-LLM checks: locations, target_roles, constraints.avoid / must_have.
Can downgrade match_explain.recommendation to skip / exploratory.
"""

from __future__ import annotations

from .jd import ParsedJD


def assess_profile_fit(jd: ParsedJD, profile: dict | None) -> dict:
    profile = profile or {}
    blockers: list[str] = []
    warnings: list[str] = []

    blob = f"{jd.title}\n{jd.company}\n{jd.raw_text}".lower()
    locations = [str(x).strip() for x in (profile.get("locations") or []) if str(x).strip()]
    if locations:
        if not any(loc.lower() in blob for loc in locations):
            # also allow remote if profile wants remote
            remote = (profile.get("constraints") or {}).get("remote")
            if remote is True and ("remote" in blob or "远程" in blob or "居家" in blob):
                pass
            else:
                blockers.append(
                    f"location_mismatch: JD text has none of {locations}"
                )

    roles = [str(x).strip() for x in (profile.get("target_roles") or []) if str(x).strip()]
    if roles:
        title_l = (jd.title or "").lower()
        if not any(r.lower() in title_l or r.lower() in blob for r in roles):
            warnings.append(f"role_weak: title/JD weak overlap with {roles}")

    constraints = profile.get("constraints") or {}
    for avoid in constraints.get("avoid") or []:
        a = str(avoid).strip()
        if a and a.lower() in blob:
            blockers.append(f"avoid_hit: `{a}` appears in JD")

    for must in constraints.get("must_have") or []:
        m = str(must).strip()
        if m and m.lower() not in blob:
            warnings.append(f"must_have_miss: `{m}` not seen in JD")

    if blockers:
        status = "block"
    elif warnings:
        status = "warn"
    else:
        status = "pass"

    return {
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
    }


def apply_to_explain(explain: dict, fit: dict) -> dict:
    """Mutate recommendation/confidence based on profile_fit."""
    out = dict(explain or {})
    status = (fit or {}).get("status") or "pass"
    if status == "block":
        out["recommendation"] = "skip"
        out["confidence"] = "high"
        out["profile_override"] = "block→skip"
    elif status == "warn":
        band = out.get("recommendation") or "exploratory"
        if band in ("strong", "plausible"):
            out["recommendation"] = "exploratory"
            out["profile_override"] = f"warn→cap({band}→exploratory)"
    return out
