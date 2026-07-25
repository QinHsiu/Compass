"""JD parsing into structured requirements."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field


HARD_MARKERS = (
    "必须",
    "要求",
    "必备",
    "required",
    "must have",
    "must-have",
    "至少",
    "熟悉",
    "精通",
)
NICE_MARKERS = (
    "优先",
    "加分",
    "最好",
    "nice to have",
    "bonus",
    "prefer",
)

SKILL_HINTS = [
    "python",
    "java",
    "go",
    "golang",
    "c++",
    "javascript",
    "typescript",
    "react",
    "vue",
    "node",
    "kubernetes",
    "k8s",
    "docker",
    "aws",
    "gcp",
    "azure",
    "spark",
    "flink",
    "sql",
    "pytorch",
    "tensorflow",
    "llm",
    "rag",
    "feature store",
    "mlops",
    "redis",
    "kafka",
    "grpc",
    "fastapi",
    "django",
    "spring",
    "linux",
]


@dataclass
class ParsedJD:
    job_id: str
    title: str
    company: str
    raw_text: str
    responsibilities: list[str] = field(default_factory=list)
    hard_requirements: list[str] = field(default_factory=list)
    nice_to_have: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    url: str | None = None
    posted_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _slug(text: str, n: int = 24) -> str:
    s = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "_", text.strip().lower())
    s = re.sub(r"_+", "_", s).strip("_")
    return (s[:n] or "job")


def make_job_id(title: str, company: str, raw: str) -> str:
    base = f"job_{_slug(company, 12)}_{_slug(title, 16)}"
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:6]
    return f"{base}_{h}"


def _extract_header(text: str) -> tuple[str, str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title, company = "Untitled Role", "Unknown"
    for ln in lines[:8]:
        m = re.match(r"^(?:职位|岗位|title)\s*[:：]\s*(.+)$", ln, re.I)
        if m:
            title = m.group(1).strip()
            continue
        m = re.match(r"^(?:公司|company)\s*[:：]\s*(.+)$", ln, re.I)
        if m:
            company = m.group(1).strip()
            continue
    if title == "Untitled Role" and lines:
        title = lines[0][:80]
    return title, company


def _split_bullets(text: str) -> list[str]:
    items: list[str] = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if re.match(r"^[-*•·\d]+[\.\)、\s]", ln):
            items.append(re.sub(r"^[-*•·\d]+[\.\)、\s]+", "", ln).strip())
        elif len(ln) > 12 and ln not in items:
            items.append(ln)
    return items


def _extract_url(text: str) -> str | None:
    m = re.search(r"https?://[^\s\]\)<>\"']+", text)
    return m.group(0).rstrip(".,;") if m else None


def _extract_posted_at(text: str) -> str | None:
    for ln in text.splitlines()[:20]:
        m = re.match(
            r"^(?:发布|posted|date|更新日期)\s*[:：]\s*(.+)$",
            ln.strip(),
            re.I,
        )
        if m:
            return m.group(1).strip()[:32]
    m = re.search(r"(20\d{2}[-/]\d{1,2}[-/]\d{1,2})", text[:400])
    return m.group(1) if m else None


def parse_jd(text: str, job_id: str | None = None) -> ParsedJD:
    text = text.strip()
    title, company = _extract_header(text)
    jid = job_id or make_job_id(title, company, text)
    bullets = _split_bullets(text)
    hard: list[str] = []
    nice: list[str] = []
    resp: list[str] = []
    lower = text.lower()
    for b in bullets:
        bl = b.lower()
        if any(m in bl for m in NICE_MARKERS) or any(m in b for m in ("优先", "加分", "最好")):
            nice.append(b)
        elif any(m in bl for m in HARD_MARKERS) or any(m in b for m in ("必须", "要求", "必备", "熟悉", "精通", "至少")):
            hard.append(b)
        elif any(k in ("职责", "responsibility", "you will", "岗位职责") for k in (bl, b)):
            resp.append(b)
        else:
            # heuristic: middle section lines as responsibilities if short list
            resp.append(b)

    if not hard:
        # fallback: lines with skill hints become hard
        for b in bullets:
            if any(h in b.lower() for h in SKILL_HINTS):
                hard.append(b)
        if not hard and bullets:
            hard = bullets[:5]

    keywords: list[str] = []
    for h in SKILL_HINTS:
        if h in lower and h not in keywords:
            keywords.append(h)
    # also capture Capitalized Tech Tokens
    for tok in re.findall(r"\b[A-Z][a-zA-Z0-9+\.#]{1,20}\b", text):
        t = tok.lower()
        if t not in keywords and t not in ("the", "and", "for"):
            keywords.append(t)

    return ParsedJD(
        job_id=jid,
        title=title,
        company=company,
        raw_text=text,
        responsibilities=resp[:20],
        hard_requirements=hard[:20],
        nice_to_have=nice[:15],
        keywords=keywords[:40],
        url=_extract_url(text),
        posted_at=_extract_posted_at(text),
    )
