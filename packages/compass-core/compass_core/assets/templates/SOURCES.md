# Resume template sources / 简历模板来源备注

Compass ships **12 layout themes** implemented in-house as HTML+Markdown renderers.
They follow the [JSON Resume](https://jsonresume.org/) data conventions and are
**inspired by** (not vendoring binary of) the following open-source projects:

| Theme id | Inspired by / related open source | License | URL |
|:---------|:----------------------------------|:--------|:----|
| `ats_plain` | JSON Resume “elegant/simple” ATS practices; Reactive Resume ATS-friendly layouts | MIT / community | https://jsonresume.org/ · https://github.com/AmruthPillai/Reactive-Resume |
| `tech_single` | jsonresume-theme-tech (ATS tech CV) | MIT | https://github.com/bgaurav7/jsonresume-theme-tech |
| `classic_serif` | jsonresume-theme-class typography ideas | MIT | https://github.com/jsonresume/jsonresume-theme-class |
| `compact_dense` | Awesome-CV / awesomish condensed density | LPPL / MIT theme ports | https://github.com/posquit0/Awesome-CV · https://github.com/YlanAllouche/jsonresume-theme-awesomish |
| `timeline` | Timeline-style sections common in open resume builders | — | community pattern |
| `two_column` | Two-column skill sidebar pattern (Reactive Resume / many JSON Resume themes) | MIT | https://github.com/AmruthPillai/Reactive-Resume |
| `modern_teal` | Modern single-accent tech themes | — | Compass original (JSON Resume schema) |
| `minimal_mono` | Minimal monospace/dev CV aesthetic | — | Compass original |
| `sidebar_skills` | Skills-first sidebar (common OSS builders) | — | community pattern |
| `impact_first` | Metrics-first bullet emphasis (Job OK / evidence-driven) | — | Compass original |
| `research_cv` | Academic/publications-friendly section order | — | Compass original |
| `internship_lite` | Short internship/campus CV | — | Compass original |

## Schema

Interchange format: **JSON Resume** (`https://jsonresume.org/schema/`) via
`compass_core.templates.to_json_resume()` / `from_json_resume()`.

Compass internal resume remains evidence-gated (`evidence_id` on items).

## Attribution rule

When exporting HTML, footers include:
`Layout: {theme} · Schema: JSON Resume · Compass evidence-gated`

Do not remove SOURCES.md when redistributing templates.
