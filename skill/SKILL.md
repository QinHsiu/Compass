---
name: compass
version: 0.2.0
description: >-
  Evidence-driven job compass: interest/career explore (/life, Holland RIASEC),
  job discovery, resume patching with 12 JSON Resume themes, interview simulation
  with searchable open question bank, and gap diagnosis. Activated by /life,
  /intake, /evidence, /discover, /resume, /interview, /diagnose, /bridge, /track,
  or /desk. Use for 职业探索, 生涯规划, 求职, 简历模板, 简历修改, 模拟面试,
  题库检索, JD匹配, 缺口诊断, 投递跟踪 — never invent experience.
---

# Compass / 证据驱动求职罗盘

Local-first workflow: **Intake → Evidence → Discover → Resume → Interview → Diagnose → Bridge/Track**.
Do not invent work history. Every resume bullet and interview answer must cite `evidence_id` or be marked `UNVERIFIED`.

**Root**: Prefer `COMPASS_ROOT` env, else the repo `content/` directory next to this skill's install source.

---

## Quick Start

```
Task Progress:
- [ ] Ensure profile exists (/intake) and evidence index (/evidence)
- [ ] Branch on slash command
- [ ] Run compass_core CLI helpers when available
- [ ] Persist artifacts under content/
- [ ] Enforce evidence gate before writing resume/interview claims
```

If the user omits a slash command, **ask** which command to use before proceeding.

---

## Activation Commands

| Command | Mode |
|---------|------|
| `/life` | Interest explore → career plan (direct or RIASEC quiz) |
| `/intake` | Profile + constraints + import resume text |
| `/evidence` | Split/store verifiable experience items |
| `/discover` | Import/collect jobs → match → shortlist |
| `/resume` | JD-targeted structured patch (no invent) |
| `/interview` | Questions, STAR, follow-ups, scorecard |
| `/diagnose` | Four-quadrant gap compass + next actions |
| `/bridge` | Verifiable upskilling plan (not fake CV lines) |
| `/track` | Application board state machine |
| `/desk` | Start light local board |
| `/studio` | Optional Gradio UI (legacy; prefer Web) |

CLI primary UI: `web` / `live` (WebSocket workbench on :8766) — includes **职业探索** view.  
Also: `life`, `rag-index`, `questions --semantic`, `timeline`, `export-report`, `llm-info`, `crawl-llm`.

Strip the slash command; remaining text is the payload (JD, notes, job_id, etc.).

### Shortest useful path (≤4 commands)

Given existing profile + evidence:

```
/discover <JD or source>
/resume job_id=<id>
/interview job_id=<id>
/diagnose job_id=<id>
```

---

## Evidence Gate (mandatory)

1. Load `content/evidence/index.json`.
2. Before writing a factual claim into resume or interview answer:
   - If claim maps to an evidence item → cite `evidence_id`.
   - Else → label `UNVERIFIED` and **do not** present as proven achievement.
3. Prefer `python -m compass_core.cli gate --claim "..."` or `compass_core.gate.check_claims`.
4. `/bridge` may propose projects/practice **to build** evidence; never backdate them onto the CV as done work.
5. **Skill-gap preflight** (zero-LLM): classify JD skills as `existing` / `supported_by_evidence` / `gap` vs the evidence vault. **Never write `gap` skills into the resume Skills section.**

```bash
python -m compass_core.cli skill-gap --root content --job-id <id>
# or: --jd-file jd.txt
```

`match.json` includes `skill_gap`; `ats_report.json` checklist requires `no_gap_skills_injected`.

---

## Module Workflows

### `/life`

1. User pastes a life/career narrative or points to a file (pdf/txt/md/docx).
2. Run confidence routing (rule-based signals: domain/skills, education/tenure, constraints):

```bash
python -m compass_core.cli life explore --root content --text "..." 
# or --text-file story.txt / --file resume.pdf
```

3. If `route=direct` (confidence ≥ 0.72 and ≥3 signal classes): write detailed plan + RIASEC-inferred scores.
4. Else: present Holland RIASEC Likert quiz (`assets/life/riasec_zh.json`), then:

```bash
python -m compass_core.cli life answer --root content --session <id> --answers-file answers.json
```

5. Both paths produce analysis, dimensional scores, paths, 90-day actions under `content/life/{session_id}/`.
6. Optional refine / export HTML; hand off target roles into Web「求职准备」.

Do not invent credentials. Mark uncertain inferences `UNVERIFIED`. Quiz is adapted RIASEC, not commercial SDS.

### `/intake`

1. Collect: target roles, cities, salary band, visa, notice period, must-have/avoid.
2. Optionally parse pasted resume into draft evidence candidates (user confirms).
3. Write `content/profile/profile.json` using [output-templates/profile.json](output-templates/profile.json).

### `/evidence`

1. Split experiences into atomic items (one outcome / skill / project each).
2. Each item: title, context, actions, metrics, skills[], proof, tags[].
3. Write `content/evidence/{id}.md` and refresh `index.json` via:

```bash
python -m compass_core.cli evidence-index --root content
```

### `/discover`

1. Source: paste | json/csv file | rss URL | career page URL.
2. Run collector (refuse blocklisted hosts):

```bash
python -m compass_core.cli discover --root content --source paste --text-file jd.txt
python -m compass_core.cli discover --root content --source rss --url "https://..."
python -m compass_core.cli discover --root content --source career --url "https://..."
```

3. Match against evidence + profile; write `content/jobs/{job_id}/jd.md` + `match.json` (includes `skill_gap` and **`requirement_matrix`**: per-line direct/partial/gap + `match_explain` band).
4. Present shortlist with coverage %, skill gaps, requirement table (`match_explain.md`), top evidence hits. Optionally re-run:

```bash
python -m compass_core.cli skill-gap --root content --job-id <id>
python -m compass_core.cli match-explain --root content --job-id <id>
```

### `/resume`

1. Require `job_id`. Load JD + match + evidence.
2. Load or create structured resume `content/resumes/{job_id}/resume.json`.
3. Propose JSON Patch / unified diff only for evidence-backed edits. Skills merge = base ∪ `skill_gap.existing` ∪ `skill_gap.supported_by_evidence` — **never** inject `skill_gap.gap`.
4. Pick or override theme (`ats_plain` … `internship_lite`, 12 total). List via CLI:

```bash
python -m compass_core.cli templates --keywords python,kubernetes --role "ML Platform"
```

5. Write `patch.json`, `patch.diff`, `resume.md`, `resume.html`, `resume.jsonresume.json`, `ats_report.json`.
6. Run gate; drop any unverified expansions.

```bash
python -m compass_core.cli resume-patch --root content --job-id <id> --theme tech_single
```

Theme attribution: `packages/compass-core/compass_core/assets/templates/SOURCES.md`.

7. **One-page polish (optional)** — timeline, 问题/方法/结果, papers block, whitespace budget, privacy: [reference/resume-onepage.md](reference/resume-onepage.md). Hooks template: [reference/interview-hooks-template.md](reference/interview-hooks-template.md). Anonymous shape: `content/fixtures/resume_onepage_example.json`.
8. **Privacy**: real resumes / evidence / profile / PDFs stay under gitignored `content/*`. Never commit or push user CV text, phone, email, employer metrics, or hook docs with real stories.

### `/interview`

1. Require `job_id`. Pack JD + matched evidence:

```bash
python -m compass_core.cli interview-pack --root content --job-id <id>
```

2. Generate: warm-up, JD deep-dive, STAR stories (requirement-mapped), stress follow-ups, **retrieved bank questions**, scorecard.
3. Every sample answer cites `evidence_id`.
4. Write `content/interviews/{job_id}/session.md` (+ `pack.json`, `bank_hits.json`, **`scorecard.json`**, **`retracted_claims`** in pack).
5. Persist per-answer rubric after practice turns:

```bash
python -m compass_core.cli scorecard record --root content --job-id <id> --turn 0 \
  --question "..." --answer-file ans.txt --requirement-ids hard_01
python -m compass_core.cli scorecard show --root content --job-id <id>
python -m compass_core.cli scorecard sync --root content --job-id <id>
```

Bank sources: `assets/questions/SOURCES.md`. Extend with `content/questions/extra.jsonl`.

```bash
python -m compass_core.cli questions --root content --keywords python,kubernetes,rag --limit 10
```

### `/diagnose`

1. Require `job_id` (or latest). Aggregate match + resume gaps + interview notes.
2. Fill four quadrants (see [reference/gap-compass.md](reference/gap-compass.md)):
   - Evidence / Narrative / Skill / Process
3. Each action: **做什么 / 证明物 / 预计耗时**.
4. Write `content/diagnoses/{job_id}/report.md`.

```bash
python -m compass_core.cli diagnose --root content --job-id <id>
```

### `/bridge`

1. Read diagnose report gaps.
2. Output practice/project plan that produces new evidence items (repos, blogs, metrics).
3. Write `bridge_plan.md`. Do **not** add fake employment.

### `/track`

1. Update `content/track/board.json` states:
   `wishlist → applied → interviewing → offer | rejected | ghosted`
2. Link `job_id`, dates, next follow-up. Prefer seeding from match band:

```bash
python -m compass_core.cli track --root content --job-id <id> --seed-from-match
python -m compass_core.cli track --root content --list-due
python -m compass_core.cli track --root content --job-id <id> --status applied
```

`/diagnose` auto-seeds `match_band` / `suggested_action` / `follow_up_due` (strong→apply_now +3d, plausible→tailor_then_apply +2d, exploratory→bridge_then_rematch +7d, skip→do_not_apply).

### `/desk`

```bash
python -m compass_core.cli desk --root content --port 8765
```

### `/studio` (recommended UI)

```bash
python -m compass_core.cli studio --root content --port 7860
```

Gradio tabs: Resume upload (PDF/image) · JD pipeline · Interview text/voice · Bank crawl.

---

## Artifact Layout

```
content/
  profile/profile.json
  evidence/{id}.md
  evidence/index.json
  life/{session_id}/input.md|extract.json|scores.json|plan.json|report.md|export/
  jobs/{job_id}/jd.md
  jobs/{job_id}/match.json
  resumes/{job_id}/resume.json|md|patch.*|ats_report.json
  interviews/{job_id}/session.md|pack.json
  diagnoses/{job_id}/report.md|bridge_plan.md
  track/board.json
```

Same `job_id` must be reused across resume / interview / diagnose.

---

## CLI Reference

```bash
python -m compass_core.cli --help
```

Prefer CLI for parse/match/gate/index/collect; use the model for prose inside templates.

---

## Additional Resources

- Templates: [output-templates/](output-templates/)
- Gap compass rules: [reference/gap-compass.md](reference/gap-compass.md)
- STAR guide: [reference/star.md](reference/star.md)
- Examples: [examples.md](examples.md)
- Compliance: ../docs/COMPLIANCE.md
