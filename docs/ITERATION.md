# Iteration plan / 自迭代计划

## Goal
连贯、简洁、高效：上传简历 → 岗位 → 匹配/改简历 → 文本&口语面试 → 缺口诊断；LLM/Agent 题库持续更新。

## Loop

| Round | Gap found | Fix | Done |
|:------|:----------|:----|:-----|
| R1 | 无实时交互 UI | Gradio Studio (`apps/studio`) | ✅ |
| R2 | 简历仅文本 | PDF/图片 ingest (`ingest.py`) | ✅ |
| R3 | 题库缺 LLM/Agent | `crawl_llm` + seed 30 + 公开源 | ✅ |
| R4 | 面试无口语 | edge-tts + faster-whisper ASR | ✅ |
| R5 | README 普通 | 多语言英雄首页 | ✅ |
| R6 | 可选：OCR 依赖重 | 降级提示 + 粘贴兜底 | ✅ |
| R7 | 下一轮 | 浏览器内 Web Speech 降级、更多 Agent 源 | ⏳ |

## Stop criteria
- Studio 五 Tab 可走通 demo JD
- 口语：TTS 有声；无 whisper 时可纯文本
- 题库含 llm/agent topic 且可检索
- pytest 绿

## Commands
```bash
python -m compass_core.cli crawl-llm --root content
python -m compass_core.cli studio --root content --port 7860
```
