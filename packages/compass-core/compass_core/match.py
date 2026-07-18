"""Match JD against evidence + profile."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .evidence import EvidenceItem, load_evidence, search_evidence
from .jd import ParsedJD, parse_jd


@dataclass
class MatchResult:
    job_id: str
    title: str
    company: str
    coverage: float
    keyword_hits: list[str] = field(default_factory=list)
    keyword_misses: list[str] = field(default_factory=list)
    hard_gaps: list[str] = field(default_factory=list)
    evidence_hits: list[dict] = field(default_factory=list)
    score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def match_jd(jd: ParsedJD, evidence: list[EvidenceItem]) -> MatchResult:
    hits: list[str] = []
    misses: list[str] = []
    corpus = " ".join(it.searchable_text() for it in evidence)
    for kw in jd.keywords:
        if kw.lower() in corpus:
            hits.append(kw)
        else:
            misses.append(kw)

    hard_gaps: list[str] = []
    for req in jd.hard_requirements:
        req_l = req.lower()
        # covered if any substantial token appears in evidence
        tokens = [t for t in req_l.replace("，", " ").replace(",", " ").split() if len(t) > 2]
        if not tokens:
            continue
        if not any(t in corpus for t in tokens[:6]):
            hard_gaps.append(req)

    query = " ".join(jd.keywords + jd.hard_requirements[:5])
    scored = search_evidence(evidence, query, skills=jd.keywords, limit=10)
    evidence_hits = [
        {"evidence_id": it.id, "title": it.title, "score": sc, "skills": it.skills}
        for it, sc in scored
    ]

    kw_total = max(len(jd.keywords), 1)
    coverage = len(hits) / kw_total
    # score: 0-100
    score = round(
        100 * (0.55 * coverage + 0.25 * (1 - min(len(hard_gaps), 5) / 5) + 0.2 * min(len(evidence_hits) / 5, 1)),
        1,
    )

    return MatchResult(
        job_id=jd.job_id,
        title=jd.title,
        company=jd.company,
        coverage=round(coverage, 3),
        keyword_hits=hits,
        keyword_misses=misses,
        hard_gaps=hard_gaps,
        evidence_hits=evidence_hits,
        score=score,
    )


def match_and_save(root: Path, jd_text: str, job_id: str | None = None) -> MatchResult:
    jd = parse_jd(jd_text, job_id=job_id)
    evidence = load_evidence(root)
    result = match_jd(jd, evidence)
    job_dir = root / "jobs" / jd.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "jd.md").write_text(
        f"# {jd.title} @ {jd.company}\n\n**job_id**: `{jd.job_id}`\n\n## Raw\n\n{jd.raw_text}\n",
        encoding="utf-8",
    )
    (job_dir / "jd.json").write_text(
        json.dumps(jd.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (job_dir / "match.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result
