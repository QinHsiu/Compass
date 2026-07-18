# Competitive positioning / 竞品对照

Compass vs projects surveyed in `projects/compass_r.txt`.

**Scope**: Beat open-source peers on resume write/diagnose/patch, job find, interview sim, gap advice.
Skip hard closed/desktop-only forms (e.g. Tauri JobPilot as full desktop app).

| Capability | FaceTomato | Job OK | SIT | JadeAI | Magic Resume | Reactive Resume | 面试鸭 | BossHunter | **Compass** |
|:-----------|:----------:|:------:|:---:|:------:|:------------:|:---------------:|:------:|:----------:|:-----------:|
| Resume patch + evidence gate | partial | ✅ | ✅ | AI edit | MCP patch | editor | ❌ | custom PDF | **✅ gated** |
| Template density | mid | low | low | **50+** | 12 | many | ❌ | few | **12 themed + JSON Resume** |
| Interview sim | ✅ | ✅ | STAR | ❌ | weak | ❌ | 题库 | ❌ | **JD + bank retrieve** |
| Question bank | DIY | low | gen | ❌ | ❌ | ❌ | **9k+** | ❌ | **98+ searchable + extra.jsonl** |
| Job discover | weak | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | autom* | **paste/RSS/career** |
| Gap compass 4Q | ❌ | partial | partial | ❌ | score | ❌ | ❌ | score | **✅ core** |
| Track | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Local skill form | ❌ | ✅ | ✅ | ❌ | MCP | ❌ | ❌ | ❌ | **Skill+Desk+MCP** |

\*BossHunter auto-apply: skipped by design (ToS).

## Open-source integrations (with attribution)

| Asset | Path | Sources doc |
|:------|:-----|:------------|
| Resume themes | `compass_core/assets/templates/` | [SOURCES.md](../packages/compass-core/compass_core/assets/templates/SOURCES.md) |
| Question bank | `compass_core/assets/questions/bank.jsonl` | [SOURCES.md](../packages/compass-core/compass_core/assets/questions/SOURCES.md) |

Inspired by: JSON Resume, Reactive Resume, jsonresume-theme-tech/class, h5bp FE interview questions, tech-interview-handbook, awesome-interview-questions.

## Hard acceptance metrics

| Metric | Target | Status |
|:-------|:-------|:-------|
| E2E ≤4 commands | yes | pipeline |
| Theme count | ≥12 | catalog.json |
| Bank searchable by JD keywords | yes | `questions` CLI + interview |
| Unverified expansion | 0 | gate |
| Diagnose + bank drills | yes | bank_drills.json |
| Template attribution | required | SOURCES.md + HTML footer |

## Intentionally skipped

- Full WYSIWYG 50-template visual designer (JadeAI) — we ship selectable themes + JSON Resume export instead
- CDP auto-apply (BossHunter)
- Operating a scraped 万级八股站点 (面试鸭) — retrieval over curated + user `extra.jsonl`
- Native Windows desktop shell (JobPilot) — Skill + local Desk instead
