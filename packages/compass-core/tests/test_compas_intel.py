"""Multi-source intel + rumor salary rejection."""

from __future__ import annotations

import json
from pathlib import Path

from compass_core.job_intel import build_dossier, corroborate_claims, make_claim, verify_salary_claim
from compass_core.plausibility import filter_salary_samples, salary_red_flags


def test_reject_baidu_1000w_rumor():
    out = verify_salary_claim(
        claimed="年薪1000万",
        years=2,
        degree="硕士",
        title="大模型开发",
    )
    assert out["accepted"] is False
    assert out["annual_cny_est"] == 10_000_000
    assert any(f["severity"] == "reject" for f in out["flags"])


def test_filter_peer_and_band():
    samples = [
        {"title": "后端", "p50": 400_000, "currency": "CNY", "source": "a"},
        {"title": "后端", "p50": 450_000, "currency": "CNY", "source": "b"},
        {"title": "后端", "p50": 420_000, "currency": "CNY", "source": "c"},
        {"title": "后端", "p50": 10_000_000, "currency": "CNY", "source": "rumor"},
    ]
    kept, rejected = filter_salary_samples(samples, years=2, degree="硕士", title="后端")
    assert any(r.get("p50") == 10_000_000 for r in rejected)
    assert all(k.get("p50") != 10_000_000 for k in kept)
    assert len(kept) >= 3


def test_corroborate_requires_two_sources():
    claims = [
        make_claim("hours", "996", source="s1"),
        make_claim("hours", "996", source="s2"),
        make_claim("hours", "双休", source="s3"),
    ]
    out = corroborate_claims(claims, min_sources=2)
    statuses = {c["status"] for c in out if c["value"] == "996"}
    assert "corroborated" in statuses or any(c.get("source_count", 0) >= 2 for c in out if c["value"] == "996")


def test_dossier_rejects_user_rumor(tmp_path: Path):
    (tmp_path / "jobs" / "j1").mkdir(parents=True)
    (tmp_path / "jobs" / "j1" / "jd.json").write_text(
        json.dumps(
            {
                "title": "大模型开发",
                "company": "百度",
                "raw_text": "职位：大模型开发\n公司：百度\n薪资：30-50k*15\n双休\n职责：训练与推理优化",
                "keywords": ["llm"],
                "hard_requirements": ["PyTorch"],
            }
        ),
        encoding="utf-8",
    )
    d = build_dossier(
        tmp_path,
        job_id="j1",
        company="百度",
        title="大模型开发",
        years=2,
        degree="硕士",
        claimed_salary="年薪1000万",
        live=False,
        min_sources=2,
    )
    assert d["summary"]["user_salary_claim"]["accepted"] is False
    assert d["summary"]["rejected"] >= 1
    assert Path(d["path"]).is_file()
    assert "safe_landing" in d["summary"]


def test_salary_red_flags_early_career():
    flags = salary_red_flags(2_000_000, years=2, degree="硕士", title="大模型")
    assert any(f["severity"] == "reject" for f in flags)
