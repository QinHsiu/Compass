"""Plausibility filters for salary / role claims — reject fabricated outliers.

Never invent market numbers. Only drop or down-rank impossible / single-source extremes
(e.g. 硕士+2年 · 年薪1000万).
"""

from __future__ import annotations

import re
from typing import Any

# Soft annual CNY caps by rough seniority band (personal research filters, not market truth)
_CAPS_CNY = {
    "intern": 150_000,
    "junior": 600_000,  # ~2y
    "mid": 1_200_000,  # ~3-5y
    "senior": 2_500_000,
    "staff": 4_000_000,
    "principal": 6_000_000,
    "unknown": 3_000_000,
}

# Absolute hard reject (even for principal) unless ≥3 sources agree within 20%
_HARD_MAX_CNY = 8_000_000
_HARD_MAX_USD = 1_500_000


def infer_band(*, years: float | None = None, level: str = "", title: str = "") -> str:
    lv = f"{level} {title}".lower()
    if any(x in lv for x in ("intern", "实习", "校园")):
        return "intern"
    if any(x in lv for x in ("principal", "distinguished", "fellow", "l8", "e8", "p10", "t8")):
        return "principal"
    if any(x in lv for x in ("staff", "l7", "e7", "p9", "t7", "专家")):
        return "staff"
    if any(x in lv for x in ("senior", "高级", "l6", "e6", "p7", "p8", "t5", "t6", "2-2", "3-1")):
        return "senior"
    if years is not None:
        if years < 1:
            return "intern"
        if years <= 2:
            return "junior"
        if years <= 5:
            return "mid"
        if years <= 8:
            return "senior"
        return "staff"
    if any(x in lv for x in ("junior", "初级", "应届", "校招", "l3", "l4", "p4", "p5", "1-1", "1-2", "2-1")):
        return "junior"
    if any(x in lv for x in ("中级", "l5", "p6")):
        return "mid"
    return "unknown"


def to_annual_cny(value: float, *, currency: str = "CNY", unit_hint: str = "") -> float | None:
    """Normalize a money figure to approximate annual CNY."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    cur = (currency or "CNY").upper()
    hint = (unit_hint or "").lower()
    # monthly k mistaken as annual
    if v < 200 and ("k" in hint or "千" in hint):
        v *= 1000
    if "月" in hint or "month" in hint or (v < 100_000 and "年" not in hint and "year" not in hint):
        # treat as monthly if small
        if v < 150_000:
            v *= 12
    if cur in ("USD", "US$"):
        v *= 7.2  # rough FX for plausibility only
    elif cur in ("HKD",):
        v *= 0.92
    return v


def salary_red_flags(
    annual_cny: float | None,
    *,
    years: float | None = None,
    level: str = "",
    title: str = "",
    degree: str = "",
    source_count: int = 1,
) -> list[dict]:
    """Return list of {code, severity, message} for implausible pay."""
    flags: list[dict] = []
    if annual_cny is None or annual_cny <= 0:
        return [{"code": "missing_salary", "severity": "info", "message": "无可用年薪数字"}]
    band = infer_band(years=years, level=level, title=title)
    cap = _CAPS_CNY.get(band, _CAPS_CNY["unknown"])

    # classic fake: 1000万 / 年 for early career
    if annual_cny >= 10_000_000:
        flags.append(
            {
                "code": "extreme_10m_plus",
                "severity": "reject",
                "message": f"年薪约 {annual_cny:.0f} CNY ≥1000万，视为虚假/单位错误 unless 多源强共识",
            }
        )
    if annual_cny > _HARD_MAX_CNY and source_count < 3:
        flags.append(
            {
                "code": "over_hard_max",
                "severity": "reject",
                "message": f"超过硬上限 {_HARD_MAX_CNY} 且来源<{3}",
            }
        )
    if annual_cny > cap:
        sev = "reject" if source_count < 2 or annual_cny > cap * 1.5 else "warn"
        flags.append(
            {
                "code": "over_band_cap",
                "severity": sev,
                "message": f"相对资历带 {band} 上限≈{cap}，观测值 {annual_cny:.0f}（来源数={source_count}）",
            }
        )
    # early career + elite pay
    if years is not None and years <= 2 and annual_cny >= 1_500_000:
        flags.append(
            {
                "code": "early_career_high_pay",
                "severity": "reject",
                "message": f"工作≈{years}年却年薪≥150万，高度可疑",
            }
        )
    if years is not None and years <= 3 and annual_cny >= 3_000_000:
        flags.append(
            {
                "code": "early_career_extreme",
                "severity": "reject",
                "message": "≤3 年经验与超高总包不兼容（过滤）",
            }
        )
    deg = (degree or "").lower()
    if any(x in deg for x in ("硕士", "master", "本科", "bachelor")) and (
        years is not None and years <= 2
    ) and annual_cny >= 2_000_000:
        flags.append(
            {
                "code": "degree_years_pay_mismatch",
                "severity": "reject",
                "message": "硕/本 + ≤2年 + ≥200万：典型谣言样本，拒绝采信",
            }
        )
    # unit confusion: user typed 1000 meaning 1000万
    if 800 <= annual_cny <= 5000 and "万" in (title + level):
        flags.append(
            {
                "code": "possible_unit_confusion",
                "severity": "warn",
                "message": "数值像「万」单位被当成元，请人工核对",
            }
        )
    return flags


def is_salary_rejected(flags: list[dict]) -> bool:
    return any(f.get("severity") == "reject" for f in flags)


def filter_salary_samples(
    samples: list[dict],
    *,
    years: float | None = None,
    degree: str = "",
    title: str = "",
    level: str = "",
) -> tuple[list[dict], list[dict]]:
    """Split samples into (kept, rejected_with_reasons)."""
    kept: list[dict] = []
    rejected: list[dict] = []
    # first pass annual values
    valued = []
    for s in samples:
        cur = str(s.get("currency") or "CNY")
        annual = to_annual_cny(s.get("p50"), currency=cur)
        if annual is None and s.get("p25") and s.get("p75"):
            mid = (float(s["p25"]) + float(s["p75"])) / 2
            annual = to_annual_cny(mid, currency=cur)
        valued.append((s, annual))

    # peer median for relative outlier (among plausible first)
    peers = []
    for s, annual in valued:
        if annual is None:
            continue
        flags = salary_red_flags(
            annual,
            years=years,
            level=level or str(s.get("level") or ""),
            title=title or str(s.get("title") or ""),
            degree=degree,
            source_count=1,
        )
        if not is_salary_rejected(flags):
            peers.append(annual)
    peer_med = None
    if len(peers) >= 3:
        peers_sorted = sorted(peers)
        peer_med = peers_sorted[len(peers_sorted) // 2]

    for s, annual in valued:
        flags = salary_red_flags(
            annual,
            years=years,
            level=level or str(s.get("level") or ""),
            title=title or str(s.get("title") or ""),
            degree=degree,
            source_count=int(s.get("source_count") or 1),
        )
        if peer_med and annual and annual > peer_med * 3.5:
            flags.append(
                {
                    "code": "peer_outlier_3_5x",
                    "severity": "reject",
                    "message": f"相对同伴中位 {peer_med:.0f} 的 3.5 倍以上（{annual:.0f}）",
                }
            )
        row = dict(s)
        row["annual_cny_est"] = annual
        row["plausibility_flags"] = flags
        if is_salary_rejected(flags):
            row["verdict"] = "rejected_implausible"
            rejected.append(row)
        else:
            row["verdict"] = "plausible"
            kept.append(row)
    return kept, rejected


def extract_claimed_salary_cny(text: str) -> float | None:
    """Parse user/claim text like '年薪1000万' / '1000w' / '50k*16'."""
    if not text:
        return None
    t = text.replace(",", "").strip()
    m = re.search(r"年薪\s*(\d+(?:\.\d+)?)\s*万", t)
    if m:
        return float(m.group(1)) * 10_000
    m = re.search(r"(\d+(?:\.\d+)?)\s*[wW万]\b", t)
    if m:
        return float(m.group(1)) * 10_000
    m = re.search(r"(\d+(?:\.\d+)?)\s*[kK]\s*[*×x]\s*(\d+)", t)
    if m:
        return float(m.group(1)) * 1000 * float(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*[kK]\b", t)
    if m:
        return float(m.group(1)) * 1000 * 12
    m = re.search(r"(\d{6,})", t)
    if m:
        return float(m.group(1))
    return None
