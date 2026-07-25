"""Industry interview question packs (tech / finance / consulting)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "assets" / "questions" / "industry_packs.jsonl"

INDUSTRIES = ("tech", "finance", "consulting")


@lru_cache(maxsize=1)
def load_industry_packs() -> list[dict]:
    if not _PATH.is_file():
        return []
    items = []
    for ln in _PATH.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            items.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return items


def infer_industry(title: str | None = None, company: str | None = None, keywords: list | None = None) -> str:
    blob = f"{title or ''} {company or ''} {' '.join(keywords or [])}".lower()
    if any(x in blob for x in ("consult", "咨询", "mckinsey", "bain", "bcg", "strategy")):
        return "consulting"
    if any(x in blob for x in ("finance", "银行", "证券", "quant", "交易", "投行", "pe ", " hedge")):
        return "finance"
    return "tech"


def search_industry_pack(
    industry: str | None = None,
    *,
    title: str | None = None,
    company: str | None = None,
    keywords: list | None = None,
    limit: int = 8,
) -> list[dict]:
    ind = (industry or infer_industry(title, company, keywords) or "tech").lower()
    if ind not in INDUSTRIES:
        ind = "tech"
    hits = [it for it in load_industry_packs() if (it.get("industry") or "").lower() == ind]
    return hits[:limit]
