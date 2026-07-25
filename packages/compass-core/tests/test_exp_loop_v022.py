"""v0.22 competitive-loop: cover letter, apply email, track patterns, STAR+R."""

from __future__ import annotations

import json
from pathlib import Path

from compass_core.apply_email import build_apply_email
from compass_core.cover_letter import build_cover_letter
from compass_core.storybank import rebuild_storybank
from compass_core.track import upsert
from compass_core.track_patterns import analyze_patterns


def _seed_job(root: Path, job_id: str = "job_demo") -> None:
    d = root / "jobs" / job_id
    d.mkdir(parents=True)
    (d / "jd.json").write_text(
        json.dumps(
            {
                "id": job_id,
                "title": "后端开发工程师",
                "company": "星河支付",
                "url": "https://example.com/jobs/1",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (d / "match.json").write_text(
        json.dumps(
            {
                "match_explain": {
                    "recommendation": "strong",
                    "requirement_matrix": [
                        {
                            "requirement": "Java 幂等",
                            "status": "direct",
                            "evidence_ids": ["ev_a"],
                        }
                    ],
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ev = root / "evidence"
    ev.mkdir(parents=True)
    (ev / "ev_a.md").write_text(
        "# 幂等改造\n\n- **id**: ev_a\n- **skills**: Java, 幂等\n\n## Metrics\n工单 12→0\n\n## Actions\nRedis 令牌\n",
        encoding="utf-8",
    )


def test_cover_letter(tmp_path: Path):
    _seed_job(tmp_path)
    out = build_cover_letter(tmp_path, "job_demo", angle="why")
    assert out["disclaimer"] == "draft_only_evidence_gated"
    assert (tmp_path / "jobs" / "job_demo" / "cover_letter.md").is_file()
    assert any(b["evidence_id"] == "ev_a" for b in out["bullets"])


def test_apply_email(tmp_path: Path):
    _seed_job(tmp_path)
    out = build_apply_email(tmp_path, "job_demo", mode="referral", referrer="张三")
    assert out["mode"] == "referral"
    assert "张三" in out["body"]
    assert "never" in out["disclaimer"]


def test_track_patterns(tmp_path: Path):
    upsert(tmp_path, "j1", "rejected", note="no reply", match_band="plausible")
    upsert(tmp_path, "j2", "rejected", note="level", match_band="plausible")
    upsert(tmp_path, "j3", "wishlist", match_band="skip", suggested_action="do_not_apply")
    out = analyze_patterns(tmp_path)
    assert out["by_status"]["rejected"] == 2
    assert out["advice"]
    assert (tmp_path / "track" / "patterns.md").is_file()


def test_storybank_reflection(tmp_path: Path):
    ev = tmp_path / "evidence"
    ev.mkdir()
    (ev / "ev_b.md").write_text(
        "# 对账\n\n- **id**: ev_b\n- **skills**: 对账\n\n## Metrics\n40→5\n\n## Actions\n日切\n",
        encoding="utf-8",
    )
    idx = rebuild_storybank(tmp_path)
    assert idx["count"] == 1
    star = idx["items"][0]["star"]
    assert "reflection" in star
    assert "对账" in star["reflection"] or "复用" in star["reflection"]
