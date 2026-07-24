"""Zero-LLM JD skill-gap classifier (career-ops jd-skill-gap pattern).

Classifies JD skill tokens against the evidence vault into three buckets:

- existing — named in evidence ``skills[]`` (or optional profile skills)
- supported_by_evidence — appears only in evidence prose (searchable_text)
- gap — no trace in the evidence corpus

Never auto-adds skills; consumers must not inject ``gap`` into a resume.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Iterable

from .evidence import EvidenceItem
from .jd import ParsedJD, SKILL_HINTS

# Soft / boilerplate tokens that should not be reported as skill gaps.
_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "you",
    "your",
    "our",
    "this",
    "that",
    "these",
    "those",
    "must",
    "able",
    "ability",
    "strong",
    "excellent",
    "proven",
    "a",
    "an",
    "or",
    "in",
    "of",
    "to",
    "as",
    "is",
    "are",
    "bachelor",
    "bachelors",
    "master",
    "masters",
    "degree",
    "diploma",
    "certification",
    "certificate",
    "experience",
    "years",
    "year",
    "senior",
    "junior",
    "entry",
    "level",
    "minimum",
    "preferred",
    "required",
    "candidates",
    "candidate",
    "applicants",
    "applicant",
    "ideal",
    "successful",
    "knowledge",
    "understanding",
    "familiarity",
    "exposure",
    "background",
    "skills",
    "skill",
    "communication",
    "team",
    "teams",
    "work",
    "working",
    "必须",
    "要求",
    "必备",
    "优先",
    "加分",
    "熟悉",
    "精通",
    "了解",
    "具有",
    "以上",
    "相关",
    "经验",
    "能力",
    "学历",
    "本科",
    "硕士",
    "博士",
}

# Capitalized Latin tokens (C++, Node.js, …) — same idea as career-ops SKILL_TOKEN_RE.
_LATIN_SKILL_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9+.#]{0,29}[A-Za-z0-9+#](?:\.[a-z]{2,4})?)(?!\w)"
)


@dataclass
class SkillGapResult:
    existing: list[str] = field(default_factory=list)
    supported_by_evidence: list[str] = field(default_factory=list)
    gap: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def injectable(self) -> list[str]:
        """Skills safe to merge into a resume Skills section."""
        return list(dict.fromkeys([*self.existing, *self.supported_by_evidence]))


def skill_mentioned_in_text(skill: str, text: str) -> bool:
    """Word-boundary, case-insensitive match (Java !⊂ JavaScript)."""
    if not skill or not text:
        return False
    escaped = re.escape(skill)
    # (?<!\w) / (?!\w) so C++ / C# still match at symbol edges.
    return re.search(rf"(?<!\w){escaped}(?!\w)", text, flags=re.IGNORECASE) is not None


def _normalize_token(token: str) -> str:
    return token.strip()


def _is_noise(token: str) -> bool:
    t = token.lower().strip()
    if len(t) < 2:
        return True
    if t in _STOPWORDS:
        return True
    if t.isdigit():
        return True
    return False


def extract_jd_skills(jd: ParsedJD | str, extra: Iterable[str] | None = None) -> list[str]:
    """
    Conservative skill token list from a ParsedJD or raw JD text.

    Prefer structured ``keywords`` / hints when available; also scan raw text
    for capitalized Latin tokens under requirement-like lines.
    """
    skills: list[str] = []
    seen: set[str] = set()

    def add(tok: str) -> None:
        tok = _normalize_token(tok)
        if _is_noise(tok):
            return
        key = tok.lower()
        if key in seen:
            return
        seen.add(key)
        skills.append(tok)

    if isinstance(jd, ParsedJD):
        for kw in jd.keywords:
            add(kw)
        # Pull technical tokens from hard requirement sentences via known hints.
        blob = " ".join(jd.hard_requirements + jd.nice_to_have).lower()
        for hint in SKILL_HINTS:
            if hint in blob:
                add(hint)
        raw = jd.raw_text
    else:
        raw = jd

    for m in _LATIN_SKILL_RE.finditer(raw or ""):
        add(m.group(1))

    if extra:
        for t in extra:
            add(t)

    return skills


def _named_skills_text(evidence: list[EvidenceItem], profile_skills: Iterable[str] | None = None) -> str:
    parts: list[str] = []
    for it in evidence:
        parts.extend(it.skills or [])
    if profile_skills:
        parts.extend(profile_skills)
    return "\n".join(parts)


def _prose_text(evidence: list[EvidenceItem]) -> str:
    # searchable_text already lowercases; keep original body snippets for CJK / case.
    parts: list[str] = []
    for it in evidence:
        parts.append(it.title)
        parts.append(it.context)
        parts.append(it.actions)
        parts.append(it.metrics)
        parts.append(it.proof)
        parts.append(it.body)
        parts.append(" ".join(it.tags or []))
    return "\n".join(parts)


def classify_skills(
    jd_skills: list[str],
    evidence: list[EvidenceItem],
    profile_skills: Iterable[str] | None = None,
) -> SkillGapResult:
    named = _named_skills_text(evidence, profile_skills)
    prose = _prose_text(evidence)
    existing: list[str] = []
    supported: list[str] = []
    gap: list[str] = []
    for skill in jd_skills:
        if skill_mentioned_in_text(skill, named):
            existing.append(skill)
        elif skill_mentioned_in_text(skill, prose):
            supported.append(skill)
        else:
            gap.append(skill)
    return SkillGapResult(
        existing=existing,
        supported_by_evidence=supported,
        gap=gap,
    )


def classify_jd(
    jd: ParsedJD,
    evidence: list[EvidenceItem],
    profile_skills: Iterable[str] | None = None,
) -> SkillGapResult:
    tokens = extract_jd_skills(jd)
    return classify_skills(tokens, evidence, profile_skills=profile_skills)


def profile_skill_list(profile: dict | None) -> list[str]:
    """Optional profile.skills or constraints.must_have as named skills."""
    if not profile:
        return []
    out: list[str] = []
    for key in ("skills", "skill_tags"):
        val = profile.get(key)
        if isinstance(val, list):
            out.extend(str(x) for x in val if x)
        elif isinstance(val, str) and val.strip():
            out.extend(s.strip() for s in re.split(r"[,，|/]", val) if s.strip())
    constraints = profile.get("constraints") or {}
    if isinstance(constraints, dict):
        for x in constraints.get("must_have") or []:
            if x:
                out.append(str(x))
    return out
