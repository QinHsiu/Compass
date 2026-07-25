# Exp loop — Compass competitive refresh

```text
target_score:
  task: compass_competitive_parity_round14
  metric: ship_top_first_party_deltas_from_online_scan
  threshold: cover_letter + apply_email + track_patterns + STAR+R
  eval_set: packages/compass-core/tests/test_exp_loop_v022.py
```

## Round 1 — analysis

### Online competitors (retrieved 2026-07-25)

| Source | Signal |
|:-------|:-------|
| santifer/career-ops (~56k★, v1.13) | Cover letter angles, apply email drafts, rejection patterns, STAR+R |
| srbhr/Resume-Matcher (~27k★) | Cover letter + interview prep from tailored resume |
| profitelai/hireforge | Cover letter, LinkedIn optimizer, outreach (scrape deferred) |
| Chozzc/Lujie-Careerkit | Multi-resume + post-interview AI review |

### Badcase clusters vs Compass ≤0.21

1. **Outbound drafts missing** — match/resume strong, but no cover/email path  
2. **No rejection targeting** — track board stores status, no pattern rollup  
3. **Storybank STAR only** — competitors use STAR+Reflection for reuse  

### Multi-plans (ranked)

| Id | Plan | EV | Cost | Chosen |
|:---|:-----|:---|:-----|:------:|
| P1 | cover-letter + apply-email drafts | High | S | **Top-1** |
| P2 | track --patterns | High | S | bundled |
| P3 | storybank reflection | Med | XS | bundled |
| P4 | LinkedIn optimizer / scrape | Low (compliance) | — | reject |
| P5 | Celery / LangGraph | Low vs moat | L | defer |
| P6 | Browser auto-apply | Out of scope | — | reject |

## Mini-validation

`pytest packages/compass-core/tests/test_exp_loop_v022.py` → **4 passed** (+ storybank empty).

## Evaluation vs target

| Metric | Result |
|:-------|:-------|
| cover-letter CLI + evidence bullets | pass |
| apply-email modes | pass |
| track --patterns | pass |
| STAR+R reflection | pass |
| **target_score** | **met** |

## Decision

**stop** Round 1 — target met. Remaining: Web UI buttons for cover/email, LinkedIn headline draft without scrape (optional next loop).

## Commands

```bash
python -m compass_core.cli cover-letter --root content --job-id <id> --angle why
python -m compass_core.cli apply-email --root content --job-id <id> --mode recruiter
python -m compass_core.cli track --root content --patterns
python -m compass_core.cli storybank rebuild --root content
```
