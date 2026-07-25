"""Career recommend + expanded salary sources."""

from __future__ import annotations

from pathlib import Path

from compass_core.career_recommend import crawl_company, detect_ats_from_html, parse_career_page, recommend_jobs
from compass_core.companies import load_companies
from compass_core.comp_live import live_lookup


def test_detect_ats():
    html = '<a href="https://boards.greenhouse.io/acme/jobs/1">Engineer</a>'
    assert detect_ats_from_html(html) == "greenhouse:acme"


def test_parse_career_jsonld():
    html = """
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"ML Eng","url":"https://ex.com/1",
     "description":"Python RAG 30-40k","hiringOrganization":{"name":"Acme"},
     "baseSalary":{"value":{"minValue":30000,"maxValue":40000,"unitText":"MONTH"}}}
    </script>
    """
    jobs = parse_career_page(html, base_url="https://ex.com/", company="Acme")
    assert jobs and jobs[0]["title"] == "ML Eng"
    assert "30" in (jobs[0].get("salary_hint") or jobs[0]["text"])


def test_recommend_with_mocks(tmp_path: Path):
    companies = [
        {"name": "Acme", "ats": "greenhouse:acme", "career_url": None},
        {"name": "Beta", "ats": None, "career_url": "https://beta.example/careers"},
    ]

    def fetch_json(url: str):
        return {
            "jobs": [
                {
                    "title": "ML Platform Engineer",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    "content": "<p>Python LLM RAG</p>",
                    "location": {"name": "Remote"},
                }
            ]
        }

    def fetch_html(url: str):
        return """
        <html><body>
        <script type="application/ld+json">
        {"@type":"JobPosting","title":"Backend Engineer","url":"https://beta.example/jobs/2",
         "description":"Go Kubernetes 薪资：25-35k","hiringOrganization":{"name":"Beta"}}
        </script>
        </body></html>
        """

    out = recommend_jobs(
        tmp_path,
        keyword="Engineer",
        limit=10,
        match=True,
        workers=1,
        companies=companies,
        fetch_fn=fetch_json,
        fetch_html_fn=fetch_html,
    )
    assert out["crawled"] >= 1
    assert out["recommended"]
    assert Path(out["path"]).is_file()


def test_load_seed_companies():
    cos = load_companies(None)
    assert any(c["name"] == "OpenAI" for c in cos)


def test_comp_levels_source(tmp_path: Path):
    (tmp_path / "comp").mkdir()
    (tmp_path / "comp" / "sources.json").write_text(
        '{"levels":{"url":"https://levels.test/search"}}',
        encoding="utf-8",
    )

    def fetch(url, payload):
        return {"rows": [{"company": "Google", "title": "SWE", "location": "SF", "p50": 220000, "currency": "USD"}]}

    out = live_lookup(
        tmp_path,
        query="SWE",
        sources=["levels"],
        accept_tos_risk=True,
        fetch_fn=fetch,
        use_cache=False,
    )
    assert out["sample_n"] >= 1
    assert "levels" in out["sources_used"]
