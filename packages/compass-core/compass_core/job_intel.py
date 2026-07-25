"""Multi-source job intelligence with corroboration — no fabricated facts.

Collects claims about posting / work content / pay / hours / reputation / layoff risk
from independent sources, requires multi-source agreement for "corroborated", and
filters implausible salary rumors.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .plausibility import (
    extract_claimed_salary_cny,
    filter_salary_samples,
    salary_red_flags,
    to_annual_cny,
)

CLAIM_KINDS = (
    "posting",
    "work_content",
    "salary",
    "hours",
    "reputation",
    "layoff_risk",
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_claim(
    kind: str,
    value: Any,
    *,
    source: str,
    url: str = "",
    raw: str = "",
    confidence: float = 0.5,
    meta: dict | None = None,
) -> dict:
    return {
        "kind": kind,
        "value": value,
        "source": source,
        "url": url or "",
        "raw": (raw or "")[:2000],
        "confidence": float(confidence),
        "retrieved_at": _utcnow(),
        "meta": meta or {},
        "status": "unverified",  # unverified | corroborated | conflict | rejected
    }


def _norm_text(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip().lower())


def _salary_bucket(annual: float | None) -> str:
    if annual is None:
        return "unknown"
    # 10万桶
    return f"{int(annual // 100_000) * 10}万级"


def corroborate_claims(claims: list[dict], *, min_sources: int = 2) -> list[dict]:
    """Mark claims corroborated / conflict / unverified by independent source count."""
    by_kind: dict[str, list[dict]] = defaultdict(list)
    for c in claims:
        by_kind[c.get("kind") or "unknown"].append(c)

    out: list[dict] = []
    for kind, group in by_kind.items():
        # group by normalized value
        buckets: dict[str, list[dict]] = defaultdict(list)
        for c in group:
            if kind == "salary":
                annual = c.get("meta", {}).get("annual_cny")
                if annual is None and isinstance(c.get("value"), (int, float)):
                    annual = to_annual_cny(float(c["value"]), currency=str(c.get("meta", {}).get("currency") or "CNY"))
                key = _salary_bucket(annual)
            else:
                key = _norm_text(c.get("value"))[:160] or "empty"
            buckets[key].append(c)

        # sources per bucket
        for key, items in buckets.items():
            sources = {i.get("source") for i in items if i.get("source")}
            n = len(sources)
            if n >= min_sources:
                status = "corroborated"
            elif len(buckets) > 1 and n == 1:
                # other buckets exist → potential conflict later
                status = "unverified"
            else:
                status = "unverified"
            for i in items:
                row = dict(i)
                row["status"] = status
                row["agreeing_sources"] = sorted(sources)
                row["source_count"] = n
                out.append(row)

        # conflicts: multiple buckets each with ≥1 source
        active = [(k, v) for k, v in buckets.items() if k not in ("empty", "unknown")]
        if len(active) >= 2:
            # mark all as conflict if they disagree and none dominates
            counts = [(k, len({x.get("source") for x in v})) for k, v in active]
            counts.sort(key=lambda x: -x[1])
            if counts[0][1] == counts[1][1]:
                for i, row in enumerate(out):
                    if row.get("kind") == kind:
                        out[i] = dict(row)
                        out[i]["status"] = "conflict"
                        out[i]["conflict_note"] = f"multi_value:{[c[0] for c in counts[:3]]}"
    return out


_HOURS_PAT = re.compile(r"(9\s*[-–]\s*9\s*[-–]\s*6|大小周|单休|双休|965|996|955|弹性|加班)", re.I)
_LAYOFF_PAT = re.compile(r"(裁员|优化|hc\s*冻结|招聘冻结|layoff|layoff|缩编|止损)", re.I)
_REP_GOOD = re.compile(r"(口碑好|福利好|成长|培养|技术氛围)", re.I)
_REP_BAD = re.compile(r"(坑|加班严重|管理混乱|PUA|欠薪|跑路)", re.I)


def extract_soft_signals(text: str, *, source: str, url: str = "") -> list[dict]:
    """Extract hours / reputation / layoff *signals* — always weak unless corroborated."""
    claims = []
    if not text:
        return claims
    hm = _HOURS_PAT.findall(text)
    if hm:
        claims.append(
            make_claim(
                "hours",
                ",".join(sorted(set(hm)))[:80],
                source=source,
                url=url,
                raw=text[:500],
                confidence=0.35,
                meta={"signal": True},
            )
        )
    if _LAYOFF_PAT.search(text):
        claims.append(
            make_claim(
                "layoff_risk",
                "elevated_signal",
                source=source,
                url=url,
                raw=text[:500],
                confidence=0.3,
                meta={"signal": True, "direction": "higher_risk"},
            )
        )
    if _REP_GOOD.search(text):
        claims.append(
            make_claim(
                "reputation",
                "positive_signal",
                source=source,
                url=url,
                raw=text[:400],
                confidence=0.3,
                meta={"signal": True},
            )
        )
    if _REP_BAD.search(text):
        claims.append(
            make_claim(
                "reputation",
                "negative_signal",
                source=source,
                url=url,
                raw=text[:400],
                confidence=0.3,
                meta={"signal": True},
            )
        )
    return claims


def collect_from_job_record(jd: dict, match: dict | None = None, *, source: str = "local_jd") -> list[dict]:
    claims = []
    title = jd.get("title") or ""
    company = jd.get("company") or ""
    raw = jd.get("raw_text") or ""
    url = jd.get("url") or ""
    claims.append(
        make_claim(
            "posting",
            {"title": title, "company": company},
            source=source,
            url=url,
            raw=raw[:800],
            confidence=0.8 if source.startswith("ats") or source == "career_jsonld" else 0.6,
        )
    )
    # work content: hard requirements + keywords
    reqs = jd.get("hard_requirements") or []
    kws = jd.get("keywords") or []
    if reqs or kws or raw:
        claims.append(
            make_claim(
                "work_content",
                {"requirements": reqs[:12], "keywords": kws[:16], "excerpt": raw[:400]},
                source=source,
                url=url,
                raw=raw[:1000],
                confidence=0.7,
            )
        )
    from .comp_live import parse_salary_token

    lo, hi, cur = parse_salary_token(raw)
    if lo or hi:
        mid = ((lo or 0) + (hi or 0)) / 2
        annual = to_annual_cny(mid, currency=cur)
        claims.append(
            make_claim(
                "salary",
                mid,
                source=source,
                url=url,
                raw=raw[:300],
                confidence=0.75,
                meta={"p25": lo, "p75": hi, "currency": cur, "annual_cny": annual},
            )
        )
    claims.extend(extract_soft_signals(raw, source=source, url=url))
    return claims


def collect_from_comp_samples(samples: list[dict]) -> list[dict]:
    claims = []
    for s in samples:
        annual = to_annual_cny(s.get("p50"), currency=str(s.get("currency") or "CNY"))
        claims.append(
            make_claim(
                "salary",
                s.get("p50"),
                source=str(s.get("source") or "comp"),
                url=str(s.get("url") or ""),
                raw=json.dumps({k: s.get(k) for k in ("title", "company", "level", "p25", "p50", "p75")}, ensure_ascii=False),
                confidence=0.55,
                meta={
                    "annual_cny": annual,
                    "currency": s.get("currency"),
                    "company": s.get("company"),
                    "title": s.get("title"),
                    "level": s.get("level"),
                },
            )
        )
    return claims


def collect_from_warehouse_row(row: dict) -> list[dict]:
    jd_like = {
        "title": row.get("title"),
        "company": row.get("company"),
        "raw_text": row.get("raw") or "",
        "url": row.get("url") or "",
        "keywords": [],
        "hard_requirements": [],
    }
    return collect_from_job_record(jd_like, source=str(row.get("source") or "warehouse"))


def safe_landing_score(claims: list[dict]) -> dict:
    """Heuristic 0–100 'safe landing' score — only from corroborated/plausible signals.

    Higher = more likely stable landing. Always returns rationale + sources; never pretends certainty.
    """
    corr = [c for c in claims if c.get("status") == "corroborated"]
    rej = [c for c in claims if c.get("status") == "rejected"]
    score = 55.0  # neutral prior
    reasons: list[str] = []
    sources: set[str] = set()

    layoff = [c for c in claims if c.get("kind") == "layoff_risk"]
    if any(c.get("status") == "corroborated" and c.get("value") == "elevated_signal" for c in layoff):
        score -= 25
        reasons.append("多源提到裁员/HC冻结信号")
        sources.update(x for c in layoff for x in (c.get("agreeing_sources") or [c.get("source")]))
    elif any(c.get("value") == "elevated_signal" for c in layoff):
        score -= 10
        reasons.append("单源裁员相关措辞（未交叉验证，弱惩罚）")

    hours = [c for c in claims if c.get("kind") == "hours"]
    heavy = [c for c in hours if re.search(r"996|965|大小周|9\s*-\s*9", str(c.get("value") or ""), re.I)]
    if heavy and any(c.get("status") == "corroborated" for c in heavy):
        score -= 8
        reasons.append("多源工时文化偏强（不影响真实性，影响压力）")
    elif heavy:
        score -= 3
        reasons.append("单源加班文化信号")

    rep_neg = [c for c in claims if c.get("kind") == "reputation" and c.get("value") == "negative_signal"]
    rep_pos = [c for c in claims if c.get("kind") == "reputation" and c.get("value") == "positive_signal"]
    if any(c.get("status") == "corroborated" for c in rep_neg):
        score -= 12
        reasons.append("多源负面风评信号")
    if any(c.get("status") == "corroborated" for c in rep_pos):
        score += 8
        reasons.append("多源正面风评信号")

    posting = [c for c in claims if c.get("kind") == "posting" and c.get("status") == "corroborated"]
    if posting:
        score += 10
        reasons.append("岗位基础信息获多源交叉（官网/ATS）")
        sources.update(x for c in posting for x in (c.get("agreeing_sources") or []))

    sal_ok = [c for c in claims if c.get("kind") == "salary" and c.get("status") == "corroborated"]
    sal_rej = [c for c in claims if c.get("kind") == "salary" and c.get("status") == "rejected"]
    if sal_ok:
        score += 5
        reasons.append("薪资区间有多源共识且通过合理性过滤")
    if sal_rej:
        score -= 5
        reasons.append("存在被拒绝的离谱薪资声称（已过滤，不采信）")

    if rej:
        reasons.append(f"已拒绝 {len(rej)} 条不合理声称")

    score = max(0, min(100, round(score)))
    return {
        "score": score,
        "label": "较高" if score >= 70 else ("中等" if score >= 45 else "偏低"),
        "reasons": reasons,
        "sources": sorted(s for s in sources if s),
        "disclaimer": "启发式安全着陆分，非预测；仅基于已标注来源的交叉论证，缺源不加分",
    }


def build_dossier(
    root: Path,
    *,
    company: str = "",
    title: str = "",
    job_id: str | None = None,
    years: float | None = None,
    degree: str = "",
    claimed_salary: str | float | None = None,
    live: bool = False,
    accept_tos_risk: bool = False,
    min_sources: int = 2,
) -> dict:
    """Assemble multi-source dossier with filters + corroboration."""
    root = Path(root)
    claims: list[dict] = []

    # local job
    if job_id:
        jd_path = root / "jobs" / job_id / "jd.json"
        match_path = root / "jobs" / job_id / "match.json"
        if jd_path.is_file():
            jd = json.loads(jd_path.read_text(encoding="utf-8"))
            match = json.loads(match_path.read_text(encoding="utf-8")) if match_path.is_file() else None
            company = company or jd.get("company") or ""
            title = title or jd.get("title") or ""
            claims.extend(collect_from_job_record(jd, match, source="local_jd"))

    # warehouse rows
    try:
        from .warehouse import search_jobs

        q = " ".join(x for x in (company, title) if x)
        for row in search_jobs(root, q, limit=15):
            claims.extend(collect_from_warehouse_row(row))
    except Exception:
        pass

    # live / local comp samples
    samples = []
    try:
        from .comp_bench import lookup_comp, lookup_comp_merged

        if live:
            comp = lookup_comp_merged(
                root,
                title=title,
                company=company,
                query=f"{company} {title}",
                live=True,
                accept_tos_risk=accept_tos_risk,
                sources=["offershow", "http", "levels", "jobs", "career", "cache"],
                limit=30,
            )
        else:
            comp = lookup_comp(root, title=title or company, limit=20)
        samples = [h for h in (comp.get("hits") or []) if isinstance(h, dict) and h.get("p50")]
    except Exception as e:
        comp_err = str(e)
    else:
        comp_err = None

    kept, rejected_sal = filter_salary_samples(
        samples, years=years, degree=degree, title=title, level=""
    )
    claims.extend(collect_from_comp_samples(kept))
    for r in rejected_sal:
        c = make_claim(
            "salary",
            r.get("p50"),
            source=str(r.get("source") or "comp"),
            raw=json.dumps(r.get("plausibility_flags"), ensure_ascii=False),
            confidence=0.1,
            meta={"annual_cny": r.get("annual_cny_est"), "flags": r.get("plausibility_flags")},
        )
        c["status"] = "rejected"
        c["verdict"] = "rejected_implausible"
        claims.append(c)

    # user claimed salary check
    user_claim = None
    if claimed_salary is not None:
        if isinstance(claimed_salary, (int, float)):
            annual = float(claimed_salary)
            if annual < 10000:  # likely 「万」
                annual *= 10000
        else:
            annual = extract_claimed_salary_cny(str(claimed_salary)) or to_annual_cny(
                float(re.sub(r"[^\d.]", "", str(claimed_salary)) or 0)
            )
        flags = salary_red_flags(annual, years=years, title=title, degree=degree, source_count=1)
        user_claim = {
            "annual_cny_est": annual,
            "flags": flags,
            "accepted": not any(f.get("severity") == "reject" for f in flags),
        }
        c = make_claim(
            "salary",
            annual,
            source="user_claim",
            raw=str(claimed_salary),
            confidence=0.2,
            meta={"annual_cny": annual, "flags": flags},
        )
        c["status"] = "rejected" if not user_claim["accepted"] else "unverified"
        claims.append(c)

    claims = corroborate_claims(claims, min_sources=min_sources)
    # re-apply rejected marks that corroborate may have overwritten
    for i, c in enumerate(claims):
        if c.get("verdict") == "rejected_implausible" or (
            c.get("source") == "user_claim" and user_claim and not user_claim["accepted"]
        ):
            claims[i] = dict(c)
            claims[i]["status"] = "rejected"

    landing = safe_landing_score(claims)

    by_kind = {k: [] for k in CLAIM_KINDS}
    for c in claims:
        k = c.get("kind")
        if k in by_kind:
            by_kind[k].append(c)

    summary = {
        "company": company,
        "title": title,
        "job_id": job_id,
        "years": years,
        "degree": degree,
        "corroborated": sum(1 for c in claims if c.get("status") == "corroborated"),
        "unverified": sum(1 for c in claims if c.get("status") == "unverified"),
        "conflicts": sum(1 for c in claims if c.get("status") == "conflict"),
        "rejected": sum(1 for c in claims if c.get("status") == "rejected"),
        "safe_landing": landing,
        "user_salary_claim": user_claim,
        "comp_error": comp_err,
        "policy": {
            "min_sources": min_sources,
            "fabrications": "rejected_not_shown_as_fact",
            "rule": "单源=UNVERIFIED；≥2独立源且一致=corroborated；离谱薪资=rejected",
        },
    }

    dossier = {
        "summary": summary,
        "claims_by_kind": by_kind,
        "claims": claims,
        "rejected_salary_samples": rejected_sal[:20],
        "generated_at": _utcnow(),
    }

    out_dir = root / "intel"
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "_", f"{company}_{title}" or job_id or "query")[:48]
    path = out_dir / f"dossier_{slug}.json"
    path.write_text(json.dumps(dossier, ensure_ascii=False, indent=2), encoding="utf-8")
    md = _dossier_md(dossier)
    md_path = out_dir / f"dossier_{slug}.md"
    md_path.write_text(md, encoding="utf-8")
    dossier["path"] = str(path)
    dossier["md"] = str(md_path)
    return dossier


def _dossier_md(dossier: dict) -> str:
    s = dossier.get("summary") or {}
    land = s.get("safe_landing") or {}
    lines = [
        f"# Job intel dossier — {s.get('company')} / {s.get('title')}",
        "",
        f"- corroborated: **{s.get('corroborated')}** · unverified: {s.get('unverified')} · "
        f"conflict: {s.get('conflicts')} · rejected: **{s.get('rejected')}**",
        f"- safe landing: **{land.get('score')}/100（{land.get('label')}）**",
        f"- policy: {s.get('policy', {}).get('rule')}",
        "",
        "## Safe landing reasons",
        "",
    ]
    for r in land.get("reasons") or []:
        lines.append(f"- {r}")
    lines += ["", f"> {land.get('disclaimer')}", "", "## Claims", ""]
    for kind, items in (dossier.get("claims_by_kind") or {}).items():
        lines.append(f"### {kind}")
        if not items:
            lines.append("- _(none)_")
            continue
        for c in items[:12]:
            lines.append(
                f"- [{c.get('status')}] source=`{c.get('source')}` "
                f"n={c.get('source_count', 1)} · {str(c.get('value'))[:100]}"
            )
        lines.append("")
    uc = s.get("user_salary_claim")
    if uc:
        lines += [
            "## User salary claim check",
            "",
            f"- annual_cny_est: {uc.get('annual_cny_est')}",
            f"- accepted: **{uc.get('accepted')}**",
        ]
        for f in uc.get("flags") or []:
            lines.append(f"- {f.get('severity')}: {f.get('message')}")
    return "\n".join(lines) + "\n"


def verify_salary_claim(
    *,
    claimed: str | float,
    years: float | None = None,
    degree: str = "",
    title: str = "",
    level: str = "",
) -> dict:
    """Standalone check for rumor salaries (百度大模型·硕·2年·1000万)."""
    if isinstance(claimed, (int, float)):
        annual = float(claimed)
        if annual < 10000:
            annual *= 10000
    else:
        annual = extract_claimed_salary_cny(str(claimed))
    flags = salary_red_flags(annual, years=years, degree=degree, title=title, level=level, source_count=1)
    return {
        "annual_cny_est": annual,
        "accepted": not any(f.get("severity") == "reject" for f in flags),
        "flags": flags,
        "example_reject": "硕士工作2年·年薪1000万 → rejected",
    }
