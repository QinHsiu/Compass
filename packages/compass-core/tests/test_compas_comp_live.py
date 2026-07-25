"""Live compensation — OfferShow-compatible + ingest + JD salary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass_core.comp_bench import lookup_comp_merged
from compass_core.comp_live import (
    aggregate_samples,
    ingest_live_file,
    live_lookup,
    normalize_offer_row,
    parse_salary_token,
)


def test_parse_salary_k_range():
    lo, hi, cur = parse_salary_token("薪资：25-40k·15薪")
    assert lo and hi and lo < hi
    assert cur == "CNY"


def test_normalize_offershow_row():
    n = normalize_offer_row(
        {"company": "字节", "job": "后端", "city": "北京", "salary": "30-35k", "level": "2-1"},
        source="offershow",
    )
    assert n and n["p50"] and n["company"] == "字节"


def test_ingest_and_live_mock(tmp_path: Path):
    cap = tmp_path / "cap.json"
    cap.write_text(
        json.dumps(
            {
                "data": [
                    {"company": "阿里", "job": "算法", "city": "杭州", "salary": "28-35k*16", "level": "P5"},
                    {"company": "阿里", "job": "算法", "city": "杭州", "salary": "32-40k", "level": "P6"},
                ]
            }
        ),
        encoding="utf-8",
    )
    out = ingest_live_file(tmp_path, cap)
    assert out["ingested"] == 2
    assert out["aggregate"]["p50"]

    def fetch(url, payload):
        return {
            "results": [
                {"company": "字节", "title": "ML", "location": "上海", "salary": "40-50k", "level": "2-2"}
            ]
        }

    (tmp_path / "comp").mkdir(exist_ok=True)
    (tmp_path / "comp" / "sources.json").write_text(
        json.dumps({"offershow": {"base_url": "https://example.test", "token": "t"}}),
        encoding="utf-8",
    )
    live = live_lookup(
        tmp_path,
        query="ML 上海",
        title="ML",
        location="上海",
        sources=["offershow"],
        accept_tos_risk=True,
        fetch_fn=fetch,
        use_cache=False,
    )
    assert live["sample_n"] >= 1
    assert live["aggregate"]["p50"]

    merged = lookup_comp_merged(
        tmp_path,
        title="ML",
        location="上海",
        live=True,
        sources=["offershow", "cache"],
        accept_tos_risk=True,
        fetch_fn=fetch,
    )
    assert merged["mode"] == "live"
    assert merged["hits"]


def test_live_requires_tos(tmp_path: Path):
    (tmp_path / "comp").mkdir(exist_ok=True)
    (tmp_path / "comp" / "sources.json").write_text(
        json.dumps({"offershow": {"base_url": "https://example.test"}}),
        encoding="utf-8",
    )
    with pytest.raises(PermissionError):
        live_lookup(tmp_path, query="x", sources=["offershow"], accept_tos_risk=False)


def test_jobs_salary_source(tmp_path: Path):
    d = tmp_path / "jobs" / "j1"
    d.mkdir(parents=True)
    (d / "jd.json").write_text(
        json.dumps(
            {
                "title": "后端",
                "company": "Acme",
                "raw_text": "职位：后端\n薪资：20-30k\n城市：上海",
            }
        ),
        encoding="utf-8",
    )
    live = live_lookup(tmp_path, query="后端", sources=["jobs"], accept_tos_risk=False)
    assert live["sample_n"] >= 1
    assert aggregate_samples(live["hits"])["p50"]
