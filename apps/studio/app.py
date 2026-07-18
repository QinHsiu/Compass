"""Compass Studio — Gradio interactive workbench (qmjianli-inspired layout)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_PKG = Path(__file__).resolve().parents[2] / "packages" / "compass-core"
if _PKG.is_dir() and str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

import gradio as gr

from compass_core.crawl_llm import refresh_llm_agent_bank
from compass_core.diagnose import diagnose_and_save
from compass_core.evidence import build_index
from compass_core.ingest import extract_text, split_resume_to_evidence_drafts
from compass_core.interview import interview_and_save
from compass_core.match import match_and_save
from compass_core.paths import ensure_dirs
from compass_core.questions import load_bank, search_questions
from compass_core.resume import apply_and_save
from compass_core.track import upsert
from compass_core.voice import VOICES, synthesize_speech, transcribe_audio


def _root() -> Path:
    env = os.environ.get("COMPASS_ROOT")
    if env:
        root = Path(env)
    else:
        root = Path(__file__).resolve().parents[2] / "content"
    ensure_dirs(root)
    (root / "questions").mkdir(parents=True, exist_ok=True)
    return root


def _write_evidence_drafts(root: Path, drafts: list[dict]) -> int:
    ev_dir = root / "evidence"
    ev_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for d in drafts:
        eid = d["id"]
        md = (
            f"# {d['title']}\n\n"
            f"- **id**: `{eid}`\n"
            f"- **tags**: {', '.join(d.get('tags') or [])}\n"
            f"- **skills**: {', '.join(d.get('skills') or [])}\n"
            f"- **proof**: uploaded resume extract\n\n"
            f"## Context\n\nUploaded segment.\n\n"
            f"## Actions\n\n{d.get('body', '')[:1500]}\n\n"
            f"## Metrics\n\n(pending user confirmation)\n"
        )
        (ev_dir / f"{eid}.md").write_text(md, encoding="utf-8")
        n += 1
    build_index(root)
    return n


def ui_ingest_resume(file_obj, paste_text: str):
    root = _root()
    warnings = []
    text = (paste_text or "").strip()
    if file_obj is not None:
        path = file_obj if isinstance(file_obj, str) else getattr(file_obj, "name", None)
        if path:
            result = extract_text(path)
            warnings.extend(result.get("warnings") or [])
            if result.get("text"):
                text = result["text"]
            elif not text:
                return "解析失败", "\n".join(warnings), ""
    if not text:
        return "请上传 PDF/图片/文本或粘贴简历", "\n".join(warnings), ""
    drafts = split_resume_to_evidence_drafts(text)
    n = _write_evidence_drafts(root, drafts)
    preview = text[:3000]
    return f"已写入 {n} 条证据草稿 → {root/'evidence'}", "\n".join(warnings) or "OK", preview


def ui_run_pipeline(jd_text: str, theme: str):
    root = _root()
    if not (jd_text or "").strip():
        return "请粘贴岗位 JD", "", "", "", ""
    m = match_and_save(root, jd_text.strip())
    r = apply_and_save(root, m.job_id, theme=theme or None)
    i = interview_and_save(root, m.job_id)
    d = diagnose_and_save(root, m.job_id)
    upsert(root, m.job_id, "wishlist", note="studio pipeline")
    resume_md = (root / "resumes" / m.job_id / "resume.md").read_text(encoding="utf-8")
    session = (root / "interviews" / m.job_id / "session.md").read_text(encoding="utf-8")
    report = (root / "diagnoses" / m.job_id / "report.md").read_text(encoding="utf-8")
    summary = (
        f"匹配分 {m.score} · 主题 {r.get('theme')} · 题库命中 {i.get('bank_n')} · "
        f"job_id `{m.job_id}`"
    )
    html_path = root / "resumes" / m.job_id / "resume.html"
    return summary, resume_md, session, report, str(html_path) if html_path.is_file() else ""


def ui_search_bank(query: str, limit: int):
    hits = search_questions(
        query or "llm agent rag",
        keywords=["llm", "agent", "rag"],
        limit=int(limit or 10),
        extra_root=_root(),
    )
    lines = [
        f"- `{h['id']}` [{h['topic']}] {h['q']} _(source: {h.get('source')})_" for h in hits
    ]
    return f"题库总量 {len(load_bank(_root()))}\n\n" + "\n".join(lines)


def ui_refresh_crawl():
    stats = refresh_llm_agent_bank()
    src = Path(stats["path"])
    dst = _root() / "questions" / "llm_agent.jsonl"
    if src.is_file():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    return json.dumps(stats, ensure_ascii=False, indent=2)


def ui_load_interview_q(job_id: str, idx: int):
    root = _root()
    jid = (job_id or "").strip()
    if not jid:
        jobs = sorted((root / "jobs").glob("*/match.json"))
        if not jobs:
            return "无岗位，请先在「智能求职」跑流水线", None, ""
        jid = jobs[-1].parent.name
    pack_path = root / "interviews" / jid / "pack.json"
    if not pack_path.is_file():
        interview_and_save(root, jid)
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    hits = pack.get("bank_hits") or []
    deep = pack.get("hard_requirements") or []
    questions = [h["q"] for h in hits] or [f"结合要求：{x}" for x in deep[:5]]
    if not questions:
        questions = [f"为什么适合 {pack.get('title')}？请引用 evidence_id。"]
    i = int(idx or 0) % len(questions)
    q = questions[i]
    tts = synthesize_speech(q, voice=VOICES["zh-female"])
    return (
        f"**第 {i+1}/{len(questions)} 题** · `{jid}`\n\n{q}\n\n{tts.get('warning') or ''}",
        tts.get("path"),
        jid,
    )


def ui_submit_answer(job_id: str, question_md: str, text_ans: str, audio):
    root = _root()
    asr_text = ""
    warn = ""
    if audio is not None:
        path = audio if isinstance(audio, str) else getattr(audio, "name", None)
        if path:
            tr = transcribe_audio(path)
            asr_text = tr.get("text") or ""
            warn = tr.get("warning") or ""
    answer = (text_ans or "").strip() or asr_text
    if not answer:
        return f"未收到答案。{warn}", None
    from compass_core.gate import check_claims

    results = check_claims([answer], root)
    gate = results[0] if results else None
    feedback = (
        f"**证据门禁**: {'通过 · ' + gate.status if gate and gate.ok else '未通过'}  \n"
        f"{gate.reason if gate else ''}  \n"
        f"**evidence_ids**: {gate.evidence_ids if gate else []}  \n"
        f"**语音识别**: {asr_text or '（未使用）'}  \n"
        f"{warn}"
    )
    speak = "回答已记录。" + (
        "已关联证据。" if gate and gate.ok else "请补充 evidence_id 或标 UNVERIFIED。"
    )
    tts = synthesize_speech(speak, voice=VOICES["zh-male"])
    jid = (job_id or "session").strip()
    out = root / "interviews" / jid
    out.mkdir(parents=True, exist_ok=True)
    with (out / "oral_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "q": question_md,
                    "answer": answer,
                    "asr": asr_text,
                    "gate": gate.status if gate else None,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
    return feedback, tts.get("path")


THEME_CHOICES = [
    ("ATS 简洁白", "ats_plain"),
    ("技术单栏", "tech_single"),
    ("经典衬线", "classic_serif"),
    ("高密度紧凑", "compact_dense"),
    ("现代青绿", "modern_teal"),
    ("成果优先", "impact_first"),
    ("实习轻量", "internship_lite"),
    ("极简等宽", "minimal_mono"),
]

# Layout cues from CN resume landings (e.g. qmjianli.com): brand hero, feature strip, blue accent
CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');

:root {
  --cm-blue: #2b6de5;
  --cm-blue-deep: #1a4fbf;
  --cm-ink: #1c2434;
  --cm-muted: #6b7280;
  --cm-line: #e6ebf2;
  --cm-bg: #f5f8fc;
  --cm-card: #ffffff;
}

.gradio-container {
  max-width: 1120px !important;
  margin: 0 auto !important;
  font-family: "Noto Sans SC", "DM Sans", sans-serif !important;
  color: var(--cm-ink) !important;
  background: var(--cm-bg) !important;
}

.main, .contain { background: transparent !important; }
footer { display: none !important; }

.cm-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 4px 8px; border-bottom: 1px solid var(--cm-line);
  margin-bottom: 8px;
}
.cm-logo {
  font-weight: 700; font-size: 1.35rem; letter-spacing: -0.03em;
  color: var(--cm-blue); font-family: "DM Sans", "Noto Sans SC", sans-serif;
}
.cm-logo span { color: var(--cm-ink); font-weight: 600; margin-left: 2px; }
.cm-top-meta { color: var(--cm-muted); font-size: 0.85rem; }

.cm-hero {
  position: relative;
  border-radius: 18px;
  padding: 36px 40px 32px;
  margin: 16px 0 20px;
  overflow: hidden;
  background:
    radial-gradient(900px 280px at 85% 20%, rgba(43,109,229,0.18), transparent 60%),
    linear-gradient(135deg, #ffffff 0%, #eef4ff 55%, #e8f1ff 100%);
  border: 1px solid #d9e4f7;
  box-shadow: 0 10px 30px rgba(26, 79, 191, 0.06);
}
.cm-hero h1 {
  margin: 0 0 10px; font-size: 2.15rem; line-height: 1.2;
  font-weight: 700; letter-spacing: -0.03em; color: var(--cm-ink);
}
.cm-hero h1 em { font-style: normal; color: var(--cm-blue); }
.cm-hero .sub {
  margin: 0 0 18px; max-width: 34em; color: var(--cm-muted);
  font-size: 1.02rem; line-height: 1.55;
}
.cm-cta-row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 18px; }
.cm-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px; border-radius: 999px;
  background: #fff; border: 1px solid #c9d8f5;
  color: var(--cm-blue-deep); font-size: 0.86rem; font-weight: 500;
}
.cm-feats {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
}
@media (max-width: 860px) {
  .cm-feats { grid-template-columns: repeat(2, 1fr); }
  .cm-hero { padding: 28px 22px; }
  .cm-hero h1 { font-size: 1.7rem; }
}
.cm-feat {
  background: rgba(255,255,255,0.78);
  border: 1px solid #dde7f8;
  border-radius: 12px;
  padding: 12px 12px 10px;
}
.cm-feat b { display: block; font-size: 0.92rem; margin-bottom: 4px; color: var(--cm-ink); }
.cm-feat span { font-size: 0.8rem; color: var(--cm-muted); line-height: 1.4; }

.tabs { border: none !important; }
.tab-nav {
  background: #fff !important;
  border: 1px solid var(--cm-line) !important;
  border-radius: 14px !important;
  padding: 6px !important;
  gap: 4px !important;
  margin-bottom: 14px !important;
  box-shadow: 0 4px 16px rgba(28,36,52,0.04);
}
.tab-nav button {
  border-radius: 10px !important;
  font-weight: 500 !important;
  color: var(--cm-muted) !important;
  border: none !important;
}
.tab-nav button.selected {
  background: var(--cm-blue) !important;
  color: #fff !important;
  box-shadow: 0 4px 12px rgba(43,109,229,0.28);
}

.cm-panel {
  background: var(--cm-card);
  border: 1px solid var(--cm-line);
  border-radius: 16px;
  padding: 4px 6px 10px;
  box-shadow: 0 6px 20px rgba(28,36,52,0.04);
}
.cm-section-title {
  font-size: 1.05rem; font-weight: 700; margin: 8px 4px 2px; color: var(--cm-ink);
}
.cm-section-desc {
  color: var(--cm-muted); font-size: 0.9rem; margin: 0 4px 12px; line-height: 1.5;
}

button.primary, .primary {
  background: linear-gradient(180deg, #3b7cf0, var(--cm-blue)) !important;
  border: none !important;
  box-shadow: 0 6px 16px rgba(43,109,229,0.28) !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
}
textarea, input, .wrap { border-radius: 10px !important; }
label span { font-weight: 500 !important; color: #374151 !important; }

.cm-templates {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
  margin: 8px 0 14px;
}
@media (max-width: 860px) { .cm-templates { grid-template-columns: repeat(2, 1fr); } }
.cm-tpl {
  border-radius: 12px; border: 1px solid #d7e2f5; background: #fff;
  padding: 14px 12px; min-height: 88px;
  background-image: linear-gradient(180deg, #f8fbff, #fff 40%);
}
.cm-tpl strong { display:block; font-size: 0.9rem; margin-bottom: 6px; }
.cm-tpl em { font-style: normal; font-size: 0.75rem; color: var(--cm-muted); }
.cm-tpl .bar { height: 4px; width: 42%; border-radius: 4px; margin-bottom: 8px; background: var(--cm-blue); }
.cm-tpl .bar.g { background: #0f766e; }
.cm-tpl .bar.o { background: #2563eb; width: 58%; }
.cm-tpl .bar.k { background: #334155; width: 35%; }
"""

HERO_HTML = """
<div class="cm-top">
  <div class="cm-logo">Compass<span>求职罗盘</span></div>
  <div class="cm-top-meta">Local-First · 证据门禁 · 不出站</div>
</div>
<div class="cm-hero">
  <h1>专业求职准备，<em>证据驱动</em>每一步</h1>
  <p class="sub">上传简历、匹配岗位、主题排版、模拟面试（文字/口语）、缺口诊断——参考主流简历平台的清晰动线，保留本地隐私与可追溯证据。</p>
  <div class="cm-cta-row">
    <span class="cm-chip">免费本地制作</span>
    <span class="cm-chip">ATS 友好主题</span>
    <span class="cm-chip">LLM / Agent 题库</span>
    <span class="cm-chip">口语面试 TTS/ASR</span>
  </div>
  <div class="cm-feats">
    <div class="cm-feat"><b>自动解析</b><span>PDF / 图片 / 文本一键入库为证据草稿</span></div>
    <div class="cm-feat"><b>风格主题</b><span>12 套排版，一键切换 JSON Resume</span></div>
    <div class="cm-feat"><b>隐私安全</b><span>数据留在本机 content/，默认不上云</span></div>
    <div class="cm-feat"><b>缺口罗盘</b><span>四象限诊断 + 可执行补强动作</span></div>
  </div>
</div>
"""

TPL_STRIP = """
<div class="cm-section-title">热门简历主题预览</div>
<p class="cm-section-desc">布局灵感来自专业简历站的模板陈列；导出时页脚保留开源主题归因。</p>
<div class="cm-templates">
  <div class="cm-tpl"><div class="bar"></div><strong>ATS 简洁白</strong><em>投递友好 · 单栏</em></div>
  <div class="cm-tpl"><div class="bar g"></div><strong>技术单栏</strong><em>工程师 · 平台岗</em></div>
  <div class="cm-tpl"><div class="bar o"></div><strong>左右分栏</strong><em>技能侧栏 · 视觉强</em></div>
  <div class="cm-tpl"><div class="bar k"></div><strong>成果优先</strong><em>指标前置 · 证据引用</em></div>
</div>
"""


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Compass · 求职罗盘") as demo:
        gr.HTML(HERO_HTML)

        with gr.Tabs():
            with gr.Tab("上传简历"):
                with gr.Column(elem_classes=["cm-panel"]):
                    gr.HTML(
                        '<div class="cm-section-title">导入你的简历</div>'
                        '<p class="cm-section-desc">支持 PDF、图片与文本。内容将拆成证据草稿，指标请人工确认后使用。</p>'
                    )
                    with gr.Row():
                        file_in = gr.File(
                            label="上传文件（PDF / 图片 / TXT / Word）",
                            file_types=[
                                ".pdf",
                                ".png",
                                ".jpg",
                                ".jpeg",
                                ".webp",
                                ".txt",
                                ".md",
                                ".docx",
                            ],
                        )
                        paste = gr.Textbox(
                            label="或直接粘贴简历正文",
                            lines=14,
                            placeholder="把简历文本粘贴到这里…",
                        )
                    btn_ing = gr.Button("开始解析并入库", variant="primary")
                    with gr.Row():
                        status = gr.Textbox(label="状态", lines=2)
                        warns = gr.Textbox(label="提示", lines=2)
                    preview = gr.Textbox(label="解析预览", lines=10)
                    btn_ing.click(ui_ingest_resume, [file_in, paste], [status, warns, preview])

            with gr.Tab("智能求职"):
                with gr.Column(elem_classes=["cm-panel"]):
                    gr.HTML(TPL_STRIP)
                    gr.HTML(
                        '<div class="cm-section-title">岗位匹配 → 优化 → 面试 → 诊断</div>'
                        '<p class="cm-section-desc">粘贴 JD，一键完成短名单匹配、主题简历、面试题包与缺口罗盘。</p>'
                    )
                    jd = gr.Textbox(
                        label="岗位描述 JD",
                        lines=12,
                        placeholder="公司：…\n职位：…\n岗位职责：…\n任职要求：…",
                    )
                    theme = gr.Dropdown(
                        choices=THEME_CHOICES,
                        value="tech_single",
                        label="简历主题",
                    )
                    btn_pipe = gr.Button("一键生成求职方案", variant="primary")
                    summary = gr.Textbox(label="结果摘要", lines=2)
                    with gr.Accordion("简历稿", open=True):
                        resume_out = gr.Markdown()
                    with gr.Accordion("面试题包", open=False):
                        session_out = gr.Markdown()
                    with gr.Accordion("缺口诊断", open=False):
                        report_out = gr.Markdown()
                    html_path = gr.Textbox(label="HTML 简历路径（可浏览器打开）")
                    btn_pipe.click(
                        ui_run_pipeline,
                        [jd, theme],
                        [summary, resume_out, session_out, report_out, html_path],
                    )

            with gr.Tab("模拟面试"):
                with gr.Column(elem_classes=["cm-panel"]):
                    gr.HTML(
                        '<div class="cm-section-title">文字 + 口语双模式</div>'
                        '<p class="cm-section-desc">先跑「智能求职」。可打字作答，或录音识别；题目支持语音播报。</p>'
                    )
                    with gr.Row():
                        job_id = gr.Textbox(label="岗位 ID（留空=最近一次）")
                        q_idx = gr.Number(value=0, precision=0, label="题号")
                    btn_q = gr.Button("抽取题目并播报", variant="primary")
                    q_md = gr.Markdown()
                    q_audio = gr.Audio(label="题目语音", type="filepath")
                    with gr.Row():
                        ans_text = gr.Textbox(
                            label="文字作答", lines=6, placeholder="结合 evidence_id 作答…"
                        )
                        ans_audio = gr.Audio(label="口语作答（录音）", type="filepath")
                    btn_ans = gr.Button("提交回答", variant="primary")
                    feedback = gr.Markdown()
                    fb_audio = gr.Audio(label="反馈语音", type="filepath")
                    btn_q.click(ui_load_interview_q, [job_id, q_idx], [q_md, q_audio, job_id])
                    btn_ans.click(
                        ui_submit_answer,
                        [job_id, q_md, ans_text, ans_audio],
                        [feedback, fb_audio],
                    )

            with gr.Tab("题库中心"):
                with gr.Column(elem_classes=["cm-panel"]):
                    gr.HTML(
                        '<div class="cm-section-title">LLM / Agent 重点题库</div>'
                        '<p class="cm-section-desc">检索内置与爬取题库；可一键刷新公开源（合规）。</p>'
                    )
                    with gr.Row():
                        q = gr.Textbox(value="llm agent rag tool memory", label="搜索关键词")
                        lim = gr.Slider(3, 30, value=12, step=1, label="条数")
                    with gr.Row():
                        btn_s = gr.Button("搜索题库", variant="primary")
                        btn_c = gr.Button("刷新 LLM/Agent 爬取")
                    bank_out = gr.Textbox(lines=14, label="检索结果")
                    crawl_out = gr.Textbox(lines=6, label="爬取日志")
                    btn_s.click(ui_search_bank, [q, lim], [bank_out])
                    btn_c.click(ui_refresh_crawl, [], [crawl_out])

            with gr.Tab("关于"):
                with gr.Column(elem_classes=["cm-panel"]):
                    gr.Markdown(
                        """
### Compass · 证据驱动求职罗盘

界面动线参考专业简历平台（如 [全民简历](https://www.qmjianli.com/)）的清晰分层：品牌区 → 能力条 → 工具 Tab。  
差异点：本地优先、证据门禁、缺口罗盘、不做平台自动投递。

| 语言 | 一句话 |
|:-----|:-------|
| 中文 | 把真实经历变成可投递、可面试的证据系统 |
| English | Turn real experience into matchable, interview-ready evidence |
| 日本語 | 実体験を応募・面接に耐える証拠へ |

CLI：`python -m compass_core.cli studio`  
Skill：`/discover` → `/resume` → `/interview` → `/diagnose`
                        """
                    )
    return demo


def main():
    port = int(os.environ.get("COMPASS_PORT", "7860"))
    demo = build_app()
    print(f"[Compass Studio] starting http://127.0.0.1:{port}/", flush=True)
    demo.launch(
        server_name="127.0.0.1",
        server_port=port,
        inbrowser=False,
        theme=gr.themes.Default(primary_hue="blue", neutral_hue="slate"),
        css=CSS,
        show_error=True,
    )


if __name__ == "__main__":
    main()
