# `/resume` 一页精修规范（无个人信息）

Local-first. **Never invent experience.** Never commit or push resume payloads, profile, evidence bodies, PDFs, or interview hooks that contain real PII / employment history.

Use with Compass `/intake` → `/evidence` → `/discover` → `/resume` → `/diagnose`. This doc standardizes **layout + narrative** polish after structured `resume-patch`.

---

## Privacy / git safety (mandatory)

| Do | Do not |
|----|--------|
| Keep real resumes under `content/resumes/` (gitignored) | `git add` / `commit` / `push` any real CV |
| Keep evidence under `content/evidence/` (gitignored) | Commit phone, email, company metrics as “examples” |
| Ship only anonymous fixtures under `content/fixtures/` | Paste user PDF text into skill docs or CHANGELOG |
| Before commit: `git status --ignored` and review paths | Force-add (`-f`) ignored resume paths |

Extra ignore patterns (repo `.gitignore`): `*简历*`, `*_onepage*.pdf`, `*_resume_preview.png`, contact extract dumps.

If unsure whether a file is personal: **do not stage it**.

---

## When to run this polish

- User asks for 一页 PDF / 社招排版 / 时间线调整 / 面试钩子 / 布局留白
- After `/resume` JSON patch, before投递
- Target role narrative is clear (e.g. 应用算法 · 偏 SFT) but page looks empty or timeline jumps

---

## Narrative rules

1. **One spine**: header role → summary → skills order → work overview → projects must share one thesis. Side tracks (RAG, papers) must be labeled 扩展/参与 if not the spine.
2. **Projects = 问题 / 方法 / 结果** (or Problem / Method / Result). Each project 2–3 bullets max on one page.
3. **Timeline order**: sort projects by start date ascending; concurrent projects keep 代表作 first, then peer work in the same window. Never list a later project before an earlier one unless user explicitly wants impact-first (then annotate).
4. **Role honesty**: 独立负责 vs 参与 must match evidence. Do not upgrade “参与” to owner.
5. **Metrics**: only from evidence; prepare口径表 for precise decimals. Gate claims with `compass_core.cli gate`.
6. **Papers layout**:
   - One muted lead line: domain · authorship · cites · public repo host (no private URLs required)
   - Bullet: `ShortName｜Venue Year Oral/Poster（CCF X）：中文一句话贡献`
   - Optional next line (muted, indented): full English title only — avoid stuffing long GitHub URLs that orphan-wrap
7. **Interview hooks** (local file only): map each buried phrase → likely questions → STAR prep → `evidence_id`. Store under `content/resumes/{job_id}/` (ignored). Template: [interview-hooks-template.md](interview-hooks-template.md).

---

## One-page PDF layout rules

1. **Fonts**: prefer Microsoft YaHei (or SimHei fallback). Contact/个人信息行 ≥ ~9pt (not ≤8pt).
2. **Header**: name + target role; contact line separate; left accent bar optional; no PII in committed templates.
3. **Sections**: title + accent underline; consistent left/right title–date rows.
4. **Wrap**: break on CJK punctuation / spaces / `/` in URLs; rebalance short tail lines (no single-char or ≤6-char orphans).
5. **Long title + date**: if title does not fit beside date, wrap title full-width and put date alone right-aligned — do not crush one glyph onto its own line.
6. **Whitespace budget**: about **1 line top spare + ≤2 lines bottom spare**. Prefer soft-gap scaling between sections over stuffing fake bullets.
7. **Density**: if page feels empty, first increase soft gaps / body size slightly; only then add evidence-backed bullets.

---

## Quality checklist (Compass)

```
Task Progress:
- [ ] Target role one-liner matches summary / skills / project order
- [ ] Projects chronological (or explicitly impact-ordered)
- [ ] Every metric maps to evidence_id (or marked UNVERIFIED)
- [ ] Gate probe: invent a false claim → must fail
- [ ] Optional: paste anonymized target JD → match + diagnose
- [ ] Write local quality_review.md under content/resumes/ (gitignored)
- [ ] Confirm git status: no resume/evidence/profile/PDF staged
```

Excellent bar (same as session review): spine coherency, measurable outcomes, honest scope, skills↔projects mutual proof, papers verifiable without leaking private docs.

---

## Suggested local artifacts (all gitignored)

```
content/resumes/{job_id}/
  resume.json | resume.md | resume_sft_onepage.pdf
  export_onepage_pdf.py   # user-local renderer OK
  interview_hooks_*.md
  quality_review_*.md
```

Committed repo should only contain this reference + anonymous fixtures — never the above with real data.
