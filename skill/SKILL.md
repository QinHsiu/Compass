---
name: compass
version: 0.2.0
description: >-
  Evidence-driven job compass: job discovery, resume patching with 12 JSON Resume
  themes, interview simulation with searchable open question bank, and gap
  diagnosis. Activated by /intake, /evidence, /discover, /resume, /interview,
  /diagnose, /bridge, /track, or /desk. Use for 求职, 简历模板, 简历修改, 模拟面试,
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
| `/intake` | Profile + constraints + import resume text |
| `/evidence` | Split/store verifiable experience items |
| `/discover` | Import/collect jobs → match → shortlist |
| `/resume` | JD-targeted structured patch (no invent) |
| `/interview` | Questions, STAR, follow-ups, scorecard |
| `/diagnose` | Four-quadrant gap compass + next actions |
| `/bridge` | Verifiable upskilling plan (not fake CV lines) |
| `/track` | Application board state machine |
| `/desk` | Start light local workbench |
| `/studio` | Launch Gradio Studio (upload / voice / pipeline) |

CLI companions: `live` (WebSocket realtime interview), `rag-index` / `questions --semantic`, `timeline`, `llm-info`, `crawl-llm`.

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

---

## Module Workflows

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

3. Match against evidence + profile; write `content/jobs/{job_id}/jd.md` + `match.json`.
4. Present shortlist with coverage %, gaps, top evidence hits.

### `/resume`

1. Require `job_id`. Load JD + match + evidence.
2. Load or create structured resume `content/resumes/{job_id}/resume.json`.
3. Propose JSON Patch / unified diff only for evidence-backed edits.
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

### `/interview`

1. Require `job_id`. Pack JD + matched evidence:

```bash
python -m compass_core.cli interview-pack --root content --job-id <id>
```

2. Generate: warm-up, JD deep-dive, STAR stories, stress follow-ups, **retrieved bank questions**, scorecard.
3. Every sample answer cites `evidence_id`.
4. Write `content/interviews/{job_id}/session.md` (+ `pack.json`, `bank_hits.json`).

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
2. Link `job_id`, dates, next follow-up.

```bash
python -m compass_core.cli track --root content --job-id <id> --status applied
```

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
