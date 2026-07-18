"""Evidence gate: reject unverified factual claims."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .evidence import EvidenceItem, load_evidence
from pathlib import Path


UNVERIFIED = "UNVERIFIED"

_STOP = {
    "a", "an", "the", "and", "or", "for", "with", "from", "into", "onto", "over",
    "under", "as", "of", "in", "on", "to", "by", "at", "is", "are", "was", "were",
    "be", "been", "being", "this", "that", "these", "those", "it", "its", "my",
    "our", "your", "their", "we", "you", "they", "i", "me", "led", "have", "has",
    "had", "did", "do", "does", "using", "used", "use", "via", "per", "than",
    "then", "also", "very", "just", "about", "into", "after", "before", "during",
}


@dataclass
class GateResult:
    ok: bool
    claim: str
    evidence_ids: list[str]
    status: str  # verified | unverified | empty
    reason: str


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def check_claim(claim: str, evidence: list[EvidenceItem], min_token_hits: int = 3) -> GateResult:
    claim = claim.strip()
    if not claim:
        return GateResult(False, claim, [], "empty", "empty claim")
    if UNVERIFIED in claim.upper():
        return GateResult(True, claim, [], "unverified", "explicitly marked UNVERIFIED")

    # explicit citation
    cited = re.findall(r"ev_[a-zA-Z0-9_]+", claim)
    if cited:
        ids = {it.id for it in evidence}
        missing = [c for c in cited if c not in ids]
        if missing:
            return GateResult(
                False, claim, cited, "unverified", f"unknown evidence ids: {missing}"
            )
        return GateResult(True, claim, cited, "verified", "explicit evidence_id citation")

    tokens = [
        t
        for t in re.findall(r"[a-z0-9\u4e00-\u9fff]{3,}", _normalize(claim))
        if t not in _STOP and not t.isdigit()
    ]
    # Prefer distinctive tokens (length >= 4) when available
    distinctive = [t for t in tokens if len(t) >= 4]
    use_tokens = distinctive or tokens

    best_ids: list[str] = []
    best_hits = 0
    for it in evidence:
        text = it.searchable_text()
        hits = sum(1 for t in use_tokens if t in text)
        if hits > best_hits:
            best_hits = hits
            best_ids = [it.id]
        elif hits == best_hits and hits > 0:
            best_ids.append(it.id)

    need = min_token_hits if len(use_tokens) >= min_token_hits else max(len(use_tokens), 1)
    # Reject if claim has strong unique tokens that never appear
    if best_hits >= need and best_ids and best_hits / max(len(use_tokens), 1) >= 0.4:
        return GateResult(True, claim, best_ids[:5], "verified", f"token overlap={best_hits}")

    return GateResult(
        False,
        claim,
        [],
        "unverified",
        "no evidence overlap; mark UNVERIFIED or cite evidence_id",
    )


def check_claims(claims: list[str], root: Path) -> list[GateResult]:
    evidence = load_evidence(root)
    return [check_claim(c, evidence) for c in claims]


def filter_verified_bullets(bullets: list[str], evidence: list[EvidenceItem]) -> tuple[list[str], list[str]]:
    """Return (kept, rejected)."""
    kept, rejected = [], []
    for b in bullets:
        r = check_claim(b, evidence)
        if r.ok:
            kept.append(b)
        else:
            rejected.append(b)
    return kept, rejected
