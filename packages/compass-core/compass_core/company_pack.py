"""Company-specific interview question packs (compas v0.10 / interview-skills)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_PACK_PATH = Path(__file__).resolve().parent / "assets" / "questions" / "company_packs.jsonl"


@lru_cache(maxsize=1)
def load_company_packs() -> list[dict]:
    if not _PACK_PATH.is_file():
        return []
    items = []
    for ln in _PACK_PATH.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            items.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return items


def match_company_key(company: str | None, title: str | None = None) -> str | None:
    blob = f"{company or ''} {title or ''}".lower()
    keys = (
        ("bytedance", ("bytedance", "字节", "抖音", "tiktok")),
        ("tencent", ("tencent", "腾讯")),
        ("alibaba", ("alibaba", "阿里", "淘宝", "蚂蚁")),
        ("google", ("google", "谷歌")),
        ("meta", ("meta", "facebook", "脸书")),
        ("amazon", ("amazon", "亚马逊", "aws")),
        ("baidu", ("baidu", "百度")),
        ("meituan", ("meituan", "美团")),
        ("huawei", ("huawei", "华为")),
        ("jingdong", ("jingdong", "jd.com", "京东")),
        ("didi", ("didi", "滴滴")),
    )
    for canon, aliases in keys:
        if any(a in blob for a in aliases):
            return canon
    return None


def search_company_pack(
    company: str | None = None,
    *,
    title: str | None = None,
    limit: int = 8,
) -> list[dict]:
    key = (company or "").strip().lower()
    canon = match_company_key(company, title)
    hits = []
    for it in load_company_packs():
        aliases = [str(x).lower() for x in (it.get("company") or [])]
        if canon and any(canon in a or a in (canon,) for a in aliases):
            hits.append(it)
        elif key and any(key in a or a in key for a in aliases):
            hits.append(it)
    return hits[:limit]
