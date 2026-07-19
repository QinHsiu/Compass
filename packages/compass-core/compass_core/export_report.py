"""Export interview / diagnose reports as HTML (and optional PDF)."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path


def _read(path: Path) -> str:
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def _evidence_ids(text: str) -> list[str]:
    return sorted(set(re.findall(r"ev_[a-zA-Z0-9_]+", text or "")))


def build_report_payload(root: Path, job_id: str) -> dict:
    diag = root / "diagnoses" / job_id
    interview = root / "interviews" / job_id
    job = root / "jobs" / job_id
    match = {}
    if (job / "match.json").is_file():
        match = json.loads((job / "match.json").read_text(encoding="utf-8"))
    report_md = _read(diag / "report.md")
    bridge_md = _read(diag / "bridge_plan.md")
    session_md = _read(interview / "session.md")
    oral_rows = []
    oral = interview / "oral_log.jsonl"
    if oral.is_file():
        for ln in oral.read_text(encoding="utf-8").splitlines():
            if not ln.strip():
                continue
            try:
                oral_rows.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    blob = "\n".join([report_md, session_md, json.dumps(oral_rows, ensure_ascii=False)])
    return {
        "job_id": job_id,
        "title": match.get("title") or job_id,
        "company": match.get("company") or "",
        "score": match.get("score"),
        "report_md": report_md,
        "bridge_md": bridge_md,
        "session_md": session_md,
        "oral_rows": oral_rows,
        "evidence_ids": _evidence_ids(blob),
        "quadrants": _extract_quadrants(report_md),
    }


def _extract_quadrants(report_md: str) -> list[str]:
    found = []
    for name in ("Evidence", "Narrative", "Skill", "Process"):
        if f"Quadrant: {name}" in report_md or name in report_md:
            found.append(name)
    out = []
    for n in ("Evidence", "Narrative", "Skill", "Process"):
        if n in found and n not in out:
            out.append(n)
    return out or ["Evidence", "Narrative", "Skill", "Process"]


def _quad_blurb(name: str, report_md: str) -> str:
    """Pull a short snippet near the quadrant heading if present."""
    patterns = [
        rf"Quadrant:\s*{name}[^\n]*\n([\s\S]{{0,280}})",
        rf"##[^\n]*{name}[^\n]*\n([\s\S]{{0,280}})",
    ]
    for p in patterns:
        m = re.search(p, report_md or "", re.I)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()[:220]
    labels = {
        "Evidence": "证据是否可追溯、是否有 evidence_id",
        "Narrative": "叙事是否清晰、是否能量化结果",
        "Skill": "技能与岗位硬性要求的覆盖度",
        "Process": "流程/准备动作是否可执行",
    }
    return labels.get(name, "")


def render_report_html(payload: dict) -> str:
    title = html.escape(str(payload.get("title") or payload.get("job_id")))
    company = html.escape(str(payload.get("company") or ""))
    job_id = html.escape(str(payload.get("job_id")))
    score = payload.get("score")
    eids = payload.get("evidence_ids") or []
    report_md = payload.get("report_md") or ""
    eid_rows = "".join(
        f"<tr><td><code>{html.escape(e)}</code></td><td>cited</td></tr>" for e in eids
    ) or "<tr><td colspan='2'>（无）</td></tr>"

    quad_cards = []
    for qn in payload.get("quadrants") or []:
        blurb = html.escape(_quad_blurb(qn, report_md))
        quad_cards.append(
            f"<div class='quad'><h3>{html.escape(qn)}</h3><p>{blurb}</p></div>"
        )
    quads_html = "".join(quad_cards)

    report = html.escape(report_md or "（无诊断报告）")
    bridge = html.escape(payload.get("bridge_md") or "")
    oral_bits = []
    for i, row in enumerate(payload.get("oral_rows") or [], 1):
        gate = html.escape(str(row.get("gate") or ""))
        ans = html.escape((row.get("answer") or "")[:400])
        oral_bits.append(f"<li><strong>#{i}</strong> gate={gate}<br/>{ans}</li>")
    oral_html = "".join(oral_bits) or "<li>（尚无口语日志）</li>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<title>Compass Report · {title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
body{{font-family:"Noto Sans SC",system-ui,sans-serif;background:#f5f8fc;color:#1c2434;margin:0;padding:24px;line-height:1.55}}
h1{{color:#2b6de5;margin:0 0 8px}} .muted{{color:#6b7280}}
.card{{background:#fff;border:1px solid #e6ebf2;border-radius:12px;padding:16px;margin:12px 0}}
.quads{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin:12px 0}}
@media(max-width:640px){{.quads{{grid-template-columns:1fr}}}}
.quad{{background:linear-gradient(180deg,#f7faff,#eef4ff);border:1px solid #d9e4f7;border-radius:14px;padding:14px}}
.quad h3{{margin:0 0 8px;color:#2b6de5;font-size:1rem}}
.quad p{{margin:0;font-size:.9rem;color:#334155}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}
th,td{{border:1px solid #e6ebf2;padding:8px 10px;text-align:left}}
th{{background:#eef4ff}}
pre{{white-space:pre-wrap;background:#fafcff;border:1px solid #e6ebf2;border-radius:8px;padding:12px;font-size:.9rem}}
code{{background:#eef4ff;padding:1px 6px;border-radius:4px}}
@media print{{body{{background:#fff;padding:0}} .card,.quad{{break-inside:avoid}}}}
</style></head><body>
<h1>面评 / 缺口报告</h1>
<p class="muted">{title} @ {company} · job_id <code>{job_id}</code> · 匹配分 {html.escape(str(score))}</p>
<div class="card">
  <strong>四象限</strong>
  <div class="quads" id="quadrant-cards">{quads_html}</div>
</div>
<div class="card"><strong>证据引用表</strong>
<table><thead><tr><th>evidence_id</th><th>status</th></tr></thead><tbody>{eid_rows}</tbody></table>
</div>
<div class="card"><strong>诊断报告</strong><pre>{report}</pre></div>
{f'<div class="card"><strong>Bridge 计划</strong><pre>{bridge}</pre></div>' if bridge else ''}
<div class="card"><strong>口语回合摘要</strong><ul>{oral_html}</ul></div>
<p class="muted">Generated by Compass · local-first · evidence-gated</p>
</body></html>
"""


def export_report(root: Path, job_id: str, *, want_pdf: bool = True) -> dict:
    """Write diagnoses/{job_id}/export/report.html (+ report.pdf when possible)."""
    payload = build_report_payload(root, job_id)
    out_dir = root / "diagnoses" / job_id / "export"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "report.html"
    html_path.write_text(render_report_html(payload), encoding="utf-8")
    result = {
        "job_id": job_id,
        "html": str(html_path),
        "pdf": None,
        "evidence_n": len(payload.get("evidence_ids") or []),
        "quadrants": payload.get("quadrants") or [],
        "warning": "",
    }
    if want_pdf:
        pdf_path = out_dir / "report.pdf"
        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(True, 12)
            pdf.set_font("Helvetica", size=14)
            pdf.multi_cell(0, 8, "Compass Report (summary)")
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 6, f"Role: {payload.get('title')} @ {payload.get('company')}")
            pdf.multi_cell(0, 6, f"job_id: {job_id}  score: {payload.get('score')}")
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, "1. Quadrants")
            pdf.set_font("Helvetica", size=11)
            for qn in payload.get("quadrants") or []:
                pdf.multi_cell(0, 6, f"- {qn}")
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, "2. Evidence IDs")
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 6, ", ".join(payload.get("evidence_ids") or [])[:800] or "(none)")
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, "3. See HTML for full Chinese text")
            pdf.set_font("Helvetica", size=10)
            pdf.multi_cell(0, 5, str(html_path))
            excerpt = re.sub(r"[^\x00-\x7F]+", " ", payload.get("report_md") or "")[:1200]
            pdf.multi_cell(0, 5, excerpt or "(see HTML)")
            pdf.output(str(pdf_path))
            result["pdf"] = str(pdf_path)
        except ImportError:
            result["warning"] = "fpdf2 not installed; HTML only. pip install fpdf2"
        except Exception as e:
            result["warning"] = f"pdf failed: {e}"
    return result
