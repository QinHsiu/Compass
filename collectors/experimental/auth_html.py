"""Thin wrapper — implementation lives in compass_core.auth_collect."""

from pathlib import Path

from compass_core.auth_collect import parse_job_list_html, scout_auth_html


def collect_from_fixture(fixture_path: str | Path):
    return parse_job_list_html(
        Path(fixture_path).read_text(encoding="utf-8"), base_url="https://example.com/"
    )


__all__ = ["parse_job_list_html", "scout_auth_html", "collect_from_fixture"]
