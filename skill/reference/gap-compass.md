# Gap Compass / 缺口罗盘

Four quadrants — every `/diagnose` report must cover all four.

## 1. Evidence gap 证据缺口

JD requires X but no `evidence_id` covers X.

Action shape: 收集/补做证明物 → 新 evidence 条目 → 再匹配.

## 2. Narrative gap 叙事缺口

Evidence exists but resume/interview wording does not surface it (wrong emphasis, buried metrics).

Action shape: rewrite bullets / STAR with citations — **no new facts**.

## 3. Skill gap 技能缺口

Neither evidence nor quick narrative fix covers a hard requirement.

Action shape: `/bridge` practice plan with deliverable (repo, cert note, blog) and ETA.

## 4. Process gap 流程缺口

Pipeline issues: no tailor per JD, slow follow-up, missing track, weak company research.

Action shape: track status, follow-up date, research checklist.

## Action item schema

```yaml
- quadrant: evidence|narrative|skill|process
  priority: P0|P1|P2
  what: 做什么
  proof: 证明物
  eta: 预计耗时
  related_evidence: [ev_...]
  related_jd_keywords: [...]
```
