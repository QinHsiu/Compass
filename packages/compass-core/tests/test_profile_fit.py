"""Tests for profile_fit gate (prisma-ai Round 6)."""

from __future__ import annotations

from compass_core.jd import parse_jd
from compass_core.profile_fit import apply_to_explain, assess_profile_fit


def test_avoid_blocks():
    jd = parse_jd("公司：X\n职位：广告投放\n职责：负责广告线索获客")
    fit = assess_profile_fit(jd, {"constraints": {"avoid": ["广告线索"]}})
    assert fit["status"] == "block"
    explain = apply_to_explain({"recommendation": "strong", "confidence": "medium"}, fit)
    assert explain["recommendation"] == "skip"


def test_location_mismatch():
    jd = parse_jd("公司：Y\n职位：算法\n工作地：上海")
    fit = assess_profile_fit(jd, {"locations": ["北京"]})
    assert fit["status"] == "block"


def test_location_ok():
    jd = parse_jd("公司：Y\n职位：算法\n工作地：北京海淀")
    fit = assess_profile_fit(jd, {"locations": ["北京"]})
    assert fit["status"] == "pass"


def test_warn_caps_band():
    jd = parse_jd("公司：Z\n职位：后端工程师\n远程办公")
    fit = assess_profile_fit(
        jd,
        {"target_roles": ["大模型算法工程师"], "locations": [], "constraints": {}},
    )
    assert fit["status"] in ("warn", "pass")
    if fit["status"] == "warn":
        explain = apply_to_explain({"recommendation": "strong"}, fit)
        assert explain["recommendation"] == "exploratory"
