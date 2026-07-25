"""compas v0.10 shortfall patch tests."""

from __future__ import annotations

from pathlib import Path

from compass_core.batch_match import batch_from_jobs_file, save_batch
from compass_core.company_pack import match_company_key, search_company_pack
from compass_core.company_research import build_research
from compass_core.observability import audit_event, status, tail_audit
from compass_core.root_cause import diagnose_root_causes
from compass_core.scorecard import aggregate


def test_batch_from_jobs_file_mock(tmp_path: Path):
    jobs = tmp_path / "urls.txt"
    jobs.write_text("greenhouse:acme\n", encoding="utf-8")

    def fetch(url: str):
        return {
            "jobs": [
                {
                    "title": "SWE",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    "content": "<p>Python backend</p>",
                    "location": {"name": "Remote"},
                }
            ]
        }

    rows = batch_from_jobs_file(tmp_path, jobs, workers=1, fetch_fn=fetch)
    assert rows and rows[0].get("job_id")
    summary = save_batch(tmp_path, rows, label="url")
    assert summary["count"] == 1


def test_research_brief(tmp_path: Path):
    out = build_research(tmp_path, company="Acme Corp")
    assert Path(out["path"]).is_file()
    text = Path(out["path"]).read_text(encoding="utf-8")
    assert "Contact mining" in text or "联系人" in text or "checklist" in text.lower()
    assert out["disclaimer"] == "no_linkedin_scrape"


def test_root_causes():
    roots = diagnose_root_causes(
        {"substance": 2, "structure": 2, "relevance": 4, "credibility": 2, "jd_fit": 4}
    )
    ids = {r["root_cause"] for r in roots}
    assert "narrative_hoarding" in ids
    assert "status_anxiety" in ids
    assert "evidence_gap" in ids
    data = {"answers": [], "aggregate": {}}
    aggregate(data)
    # empty answers → no roots required
    assert "root_causes" in data["aggregate"]


def test_company_pack():
    assert match_company_key("字节跳动") == "bytedance"
    hits = search_company_pack("bytedance", limit=4)
    assert hits and hits[0].get("q")


def test_observability(tmp_path: Path):
    audit_event(tmp_path, "scout", count=2, keyword="ml")
    audit_event(tmp_path, "scorecard_record", job_id="j1", turn=1)
    st = status(tmp_path)
    assert st["metrics"]["counters"].get("scout_runs", 0) >= 1
    assert st["metrics"]["counters"].get("answers_recorded", 0) >= 1
    assert len(tail_audit(tmp_path, n=5)) >= 1
