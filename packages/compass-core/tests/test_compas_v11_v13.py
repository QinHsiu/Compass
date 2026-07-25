"""compas v0.11–v0.13: anki, transcript formats, warehouse, auth, APM."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compass_core.anki_export import export_anki
from compass_core.auth_collect import parse_job_list_html, scout_auth_html
from compass_core.auth_session import import_session, require_tos_risk, session_status
from compass_core.batch_match import format_batch_board, list_batches, save_batch
from compass_core.experience_bank import search_experience
from compass_core.observability import compute_slo, evaluate_alerts, export_prometheus, span, status
from compass_core.practice_stats import export_practice_center
from compass_core.transcript import detect_format, parse_transcript
from compass_core.warehouse import search_jobs, seed_fixture, warehouse_stats


def test_detect_zoom_and_otter():
    zoom = "Alice Smith 00:01:02\nTell me about a project.\nBob Jones 00:01:20\nI led RAG latency work.\n"
    assert detect_format(zoom) in ("zoom", "generic", "otter")
    turns = parse_transcript(zoom, fmt="zoom")
    assert len(turns) >= 2
    otter = "Speaker 1\nWhat is your ownership?\nSpeaker 2\nI owned the feature store.\n"
    assert detect_format(otter) == "otter"
    assert parse_transcript(otter, fmt="otter")


def test_experience_and_anki(tmp_path: Path):
    hits = search_experience(query="RAG", limit=5)
    assert hits and hits[0].get("q")
    out = export_anki(tmp_path)
    assert Path(out["tsv"]).is_file()
    assert out["count"] >= 1


def test_practice_progress(tmp_path: Path):
    iv = tmp_path / "interviews" / "j1"
    iv.mkdir(parents=True)
    (iv / "scorecard.json").write_text(
        json.dumps(
            {
                "job_id": "j1",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "answers": [{"q": "x", "a": "y"}],
                "aggregate": {
                    "scores": {
                        "substance": 2,
                        "structure": 3,
                        "relevance": 3,
                        "credibility": 2,
                        "jd_fit": 3,
                    },
                    "gate_pass_rate": 0.4,
                },
            }
        ),
        encoding="utf-8",
    )
    iv2 = tmp_path / "interviews" / "j2"
    iv2.mkdir(parents=True)
    (iv2 / "scorecard.json").write_text(
        json.dumps(
            {
                "job_id": "j2",
                "updated_at": "2026-02-01T00:00:00+00:00",
                "answers": [{"q": "x", "a": "y"}],
                "aggregate": {
                    "scores": {
                        "substance": 4,
                        "structure": 4,
                        "relevance": 4,
                        "credibility": 4,
                        "jd_fit": 4,
                    },
                    "gate_pass_rate": 0.8,
                },
            }
        ),
        encoding="utf-8",
    )
    out = export_practice_center(tmp_path)
    md = Path(out["path"]).read_text(encoding="utf-8")
    assert "## Progress" in md
    assert "dimension_series" in out


def test_obs_alerts_prom_slo_span(tmp_path: Path):
    with span(tmp_path, "match", job_id="x"):
        pass
    al = evaluate_alerts(tmp_path)
    assert "alerts" in al
    assert (tmp_path / "logs" / "alerts.json").is_file()
    prom = export_prometheus(tmp_path)
    assert "compass_counter" in prom
    slo = compute_slo(tmp_path)
    assert "gate_pass_rate" in slo
    st = status(tmp_path)
    assert st["otel"]["spans_local"] >= 1


def test_batch_board(tmp_path: Path):
    save_batch(tmp_path, [{"job_id": "a", "letter": "B", "score_100": 78, "title": "SWE"}], label="t")
    rows = list_batches(tmp_path)
    assert rows and rows[0]["count"] == 1
    assert "batch_id" in format_batch_board(rows)


def test_warehouse_search(tmp_path: Path):
    seed_fixture(tmp_path, n=200)
    st = warehouse_stats(tmp_path)
    assert st["count"] == 200
    hits = search_jobs(tmp_path, "LLM", limit=10)
    assert hits


def test_auth_tos_gate_and_fixture(tmp_path: Path):
    with pytest.raises(PermissionError):
        require_tos_risk(False)
    require_tos_risk(True)
    fixture = (
        Path(__file__).resolve().parents[3]
        / "collectors"
        / "experimental"
        / "fixtures"
        / "sample_job_list.html"
    )
    if not fixture.is_file():
        html = '<script type="application/ld+json">{"@type":"JobPosting","title":"X","hiringOrganization":{"name":"Y"},"url":"https://example.com/1","description":"Z"}</script>'
        jobs = parse_job_list_html(html)
    else:
        jobs = parse_job_list_html(fixture.read_text(encoding="utf-8"))
    assert len(jobs) >= 1
    out = scout_auth_html(tmp_path, fixture=fixture if fixture.is_file() else None, html=None if fixture.is_file() else html, accept_tos_risk=True)
    assert out["jobs"] >= 1


def test_session_import(tmp_path: Path):
    src = tmp_path / "state.json"
    src.write_text(json.dumps({"cookies": [{"name": "a", "value": "b"}], "origins": []}), encoding="utf-8")
    meta = import_session(tmp_path, src, name="default")
    assert meta["cookie_count"] == 1
    assert session_status(tmp_path)["present"]
