"""Persisted interview scorecard (interview-coach-skill Round 3).

Per-answer rubric with evidence_ids + requirement_ids + dimension scores.
Aggregates into interviews/{job_id}/scorecard.json and syncs session.md.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .gate import check_claim
from .evidence import load_evidence

DIMENSIONS = ("substance", "structure", "relevance", "credibility", "jd_fit")

SCORECARD_VERSION = 1


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def scorecard_path(root: Path, job_id: str) -> Path:
    return Path(root) / "interviews" / job_id / "scorecard.json"


def empty_scorecard(job_id: str) -> dict:
    return {
        "version": SCORECARD_VERSION,
        "job_id": job_id,
        "updated_at": _utcnow(),
        "dimensions": list(DIMENSIONS),
        "answers": [],
        "aggregate": {
            "scores": {d: 0.0 for d in DIMENSIONS},
            "evidence_ids": [],
            "gate_pass_rate": 0.0,
            "requirement_coverage": {"direct": 0, "partial": 0, "gap": 0},
            "answer_count": 0,
        },
    }


def load_scorecard(root: Path, job_id: str) -> dict:
    path = scorecard_path(root, job_id)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("dimensions", list(DIMENSIONS))
        data.setdefault("answers", [])
        data.setdefault("aggregate", empty_scorecard(job_id)["aggregate"])
        return data
    return empty_scorecard(job_id)


def save_scorecard(root: Path, job_id: str, data: dict) -> Path:
    path = scorecard_path(root, job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data["updated_at"] = _utcnow()
    data["version"] = SCORECARD_VERSION
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _extract_evidence_ids(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"ev_[a-zA-Z0-9_]+", text or "")))


def _clamp_score(v: int | float | None, default: int = 3) -> int:
    if v is None:
        return default
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return default
    return max(1, min(5, n))


def _auto_scores_from_gate(
    gate_ok: bool,
    gate_status: str,
    evidence_ids: list[str],
    requirement_ids: list[str],
    matrix: list[dict],
) -> dict[str, int]:
    credibility = 5 if gate_ok and gate_status == "verified" else (3 if gate_ok else 1)
    substance = 4 if evidence_ids else 2
    relevance = 3
    if requirement_ids and matrix:
        fits = []
        for rid in requirement_ids:
            row = next((r for r in matrix if r.get("id") == rid), None)
            if row:
                fits.append(row.get("fit") or "gap")
        if "direct" in fits:
            relevance = 5
        elif "partial" in fits:
            relevance = 4
        elif fits:
            relevance = 2
    jd_fit = relevance
    structure = 3  # reserved for coach/manual
    return {
        "substance": substance,
        "structure": structure,
        "relevance": relevance,
        "credibility": credibility,
        "jd_fit": jd_fit,
    }


def aggregate(data: dict, matrix: list[dict] | None = None) -> dict:
    answers = data.get("answers") or []
    agg_scores = {d: 0.0 for d in DIMENSIONS}
    eids: list[str] = []
    gate_ok_n = 0
    if answers:
        for a in answers:
            sc = a.get("scores") or {}
            for d in DIMENSIONS:
                agg_scores[d] += float(sc.get(d) or 0)
            eids.extend(a.get("evidence_ids") or [])
            if (a.get("gate") or {}).get("ok"):
                gate_ok_n += 1
        for d in DIMENSIONS:
            agg_scores[d] = round(agg_scores[d] / len(answers), 2)
    cov = {"direct": 0, "partial": 0, "gap": 0}
    if matrix:
        for r in matrix:
            fit = r.get("fit") or "gap"
            if fit in cov:
                cov[fit] += 1
    data["aggregate"] = {
        "scores": agg_scores,
        "evidence_ids": list(dict.fromkeys(eids)),
        "gate_pass_rate": round(gate_ok_n / max(len(answers), 1), 3),
        "requirement_coverage": cov,
        "answer_count": len(answers),
    }
    return data


def record_answer(
    root: Path,
    job_id: str,
    *,
    turn: int,
    question: str,
    answer: str,
    scores: dict | None = None,
    requirement_ids: list[str] | None = None,
    notes: str = "",
    confidence: str = "medium",
    gate_ok: bool | None = None,
    gate_status: str | None = None,
    gate_reason: str = "",
) -> dict:
    """Append or overwrite answer for ``turn``; auto-fill scores from gate when omitted."""
    evidence = load_evidence(root)
    cited = _extract_evidence_ids(answer) + _extract_evidence_ids(question)
    cited = list(dict.fromkeys(cited))
    # Validate known evidence ids
    known = {e.id for e in evidence}
    unknown = [c for c in cited if c not in known]
    if unknown:
        raise ValueError(f"unknown evidence ids: {unknown}")

    gate_res = check_claim(answer, evidence)
    ok = gate_ok if gate_ok is not None else gate_res.ok
    status = gate_status or gate_res.status
    reason = gate_reason or gate_res.reason
    if gate_res.evidence_ids:
        cited = list(dict.fromkeys([*cited, *gate_res.evidence_ids]))

    pack_path = Path(root) / "interviews" / job_id / "pack.json"
    matrix: list[dict] = []
    if pack_path.is_file():
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        matrix = pack.get("requirement_matrix") or []
    else:
        match_path = Path(root) / "jobs" / job_id / "match.json"
        if match_path.is_file():
            matrix = json.loads(match_path.read_text(encoding="utf-8")).get("requirement_matrix") or []

    req_ids = list(requirement_ids or [])
    # Warn-level: drop unknown requirement ids
    known_req = {r.get("id") for r in matrix}
    req_ids = [r for r in req_ids if not known_req or r in known_req]

    auto = _auto_scores_from_gate(ok, status, cited, req_ids, matrix)
    final_scores = {d: _clamp_score((scores or {}).get(d, auto[d])) for d in DIMENSIONS}

    entry = {
        "turn": int(turn),
        "question": (question or "")[:500],
        "answer_hash": "sha256:" + hashlib.sha256((answer or "").encode("utf-8")).hexdigest()[:16],
        "gate": {"ok": bool(ok), "status": status, "reason": reason},
        "evidence_ids": cited,
        "requirement_ids": req_ids,
        "scores": final_scores,
        "notes": notes or "",
        "confidence": confidence or "medium",
    }

    data = load_scorecard(root, job_id)
    answers = [a for a in data.get("answers") or [] if a.get("turn") != entry["turn"]]
    answers.append(entry)
    answers.sort(key=lambda a: int(a.get("turn") or 0))
    data["answers"] = answers
    aggregate(data, matrix=matrix)
    save_scorecard(root, job_id, data)
    sync_session_md(root, job_id, data)
    return data


def import_oral_log(root: Path, job_id: str) -> dict:
    """Migrate oral_log.jsonl → scorecard answers (gate-derived scores)."""
    log_path = Path(root) / "interviews" / job_id / "oral_log.jsonl"
    if not log_path.is_file():
        return load_scorecard(root, job_id)
    turn = 0
    data = empty_scorecard(job_id)
    for line in log_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        q = str(row.get("question") or row.get("q") or "")
        a = str(row.get("answer") or row.get("a") or row.get("text") or "")
        if not a and not q:
            continue
        gate = row.get("gate") or {}
        if isinstance(gate, str):
            gate = {"ok": gate in ("verified", "unverified"), "status": gate, "reason": ""}
        record_answer(
            root,
            job_id,
            turn=int(row.get("turn", turn)),
            question=q,
            answer=a,
            gate_ok=gate.get("ok"),
            gate_status=gate.get("status"),
            gate_reason=str(gate.get("reason") or ""),
            requirement_ids=list(row.get("requirement_ids") or []),
            confidence="low",
            notes="imported from oral_log.jsonl",
        )
        turn += 1
    return load_scorecard(root, job_id)


def sync_session_md(root: Path, job_id: str, data: dict | None = None) -> Path | None:
    """Fill the Scorecard table in session.md from aggregate scores."""
    session = Path(root) / "interviews" / job_id / "session.md"
    if not session.is_file():
        return None
    data = data or load_scorecard(root, job_id)
    agg = (data.get("aggregate") or {}).get("scores") or {}
    eids = ", ".join(f"`{e}`" for e in (data.get("aggregate") or {}).get("evidence_ids") or []) or "—"
    n = (data.get("aggregate") or {}).get("answer_count") or 0
    rate = (data.get("aggregate") or {}).get("gate_pass_rate") or 0

    # Map coach dims → session table rows (Technical←substance, Ownership←structure,
    # Communication←relevance, JD fit←jd_fit); credibility noted in footer.
    table = f"""## Scorecard

| Dimension | Score 1-5 | Notes | evidence_ids |
|-----------|-----------|-------|--------------|
| Technical | {agg.get('substance', '—')} | substance · n={n} | {eids} |
| Ownership | {agg.get('structure', '—')} | structure | {eids} |
| Communication | {agg.get('relevance', '—')} | relevance | {eids} |
| JD fit | {agg.get('jd_fit', '—')} | credibility={agg.get('credibility', '—')} · gate_pass={rate} | {eids} |
"""
    text = session.read_text(encoding="utf-8")
    if "## Scorecard" in text:
        text = re.sub(
            r"## Scorecard\n.*?(?=\n## |\Z)",
            table.rstrip() + "\n",
            text,
            count=1,
            flags=re.S,
        )
    else:
        text = text.rstrip() + "\n\n" + table
    session.write_text(text, encoding="utf-8")
    return session
