# M6 acceptance checklist

Run from repo after `pip install -e packages/compass-core[dev]`:

```bash
cd packages/compass-core
pytest -q
```

| Metric | Target | Status command |
|:-------|:-------|:---------------|
| E2E ≤4 steps | pass | `python -m compass_core.cli pipeline --root <tmp> --text-file content/fixtures/demo/jd.txt` |
| Unverified expansion blocked | gate exit 2 | `python -m compass_core.cli gate --claim "Became CEO of NASA"` |
| Diagnose actions have 做什么/证明物/耗时 | unit test | `test_match_diagnose_actions_schema` |
| Paste 100% | unit test | `test_paste_collector` |
| RSS/career fixtures | unit test | `test_rss_and_career_fixtures` |
| Local privacy | no account | desk binds 127.0.0.1 |

See also [docs/COMPETITIVE.md](../docs/COMPETITIVE.md).
