"""Collect claims the candidate must NOT assert in interview (CareerForge Round 5).

Sources: resume rejected bullets, ats unverified, requirement_matrix gaps,
scorecard answers with gate.ok=false.
"""

from __future__ import annotations

import json
from pathlib import Path


def collect_retracted_claims(root: Path, job_id: str) -> list[dict]:
    root = Path(root)
    claims: list[dict] = []
    seen: set[str] = set()

    def add(claim: str, source: str, reason: str, **extra) -> None:
        text = (claim or "").strip()
        if not text:
            return
        key = text.lower()[:200]
        if key in seen:
            return
        seen.add(key)
        row = {"claim": text[:300], "source": source, "reason": reason}
        row.update({k: v for k, v in extra.items() if v is not None})
        claims.append(row)

    ats_path = root / "resumes" / job_id / "ats_report.json"
    if ats_path.is_file():
        ats = json.loads(ats_path.read_text(encoding="utf-8"))
        for b in ats.get("unverified_bullets") or []:
            add(str(b), "ats_unverified", "marked UNVERIFIED — do not present as fact")
        for b in ats.get("rejected_bullets") or []:
            add(str(b), "resume_rejected", "failed evidence gate — do not claim")

    match_path = root / "jobs" / job_id / "match.json"
    if match_path.is_file():
        match = json.loads(match_path.read_text(encoding="utf-8"))
        for row in match.get("requirement_matrix") or []:
            if row.get("fit") == "gap" and row.get("kind") == "hard":
                add(
                    str(row.get("text") or ""),
                    "requirement_gap",
                    f"hard gap ({row.get('severity') or 'material'}) — admit gap or /bridge",
                    requirement_id=row.get("id"),
                )
        for sk in (match.get("skill_gap") or {}).get("gap") or []:
            add(
                f"skill: {sk}",
                "skill_gap",
                "skill_gap.gap — never invent proficiency",
            )

    sc_path = root / "interviews" / job_id / "scorecard.json"
    if sc_path.is_file():
        sc = json.loads(sc_path.read_text(encoding="utf-8"))
        for a in sc.get("answers") or []:
            gate = a.get("gate") or {}
            if gate.get("ok") is False:
                add(
                    str(a.get("question") or a.get("answer_hash") or "prior answer"),
                    "scorecard_gate_fail",
                    str(gate.get("reason") or "gate failed — retract unsupported claim"),
                    evidence_ids=a.get("evidence_ids") or [],
                )

    return claims
