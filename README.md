<div align="center">

# Compass

### Evidence-Driven Job Compass
### 证据驱动求职罗盘

<br/>

[![version](https://img.shields.io/badge/version-0.3.0-0F766E?style=for-the-badge&labelColor=1A2332)](VERSION)
[![studio](https://img.shields.io/badge/UI-Gradio%20Studio-0F766E?style=for-the-badge&labelColor=1A2332)](apps/studio)
[![license](https://img.shields.io/badge/license-MIT-5C6B7A?style=for-the-badge&labelColor=1A2332)](LICENSE)

<br/>

**Upload · Match · Patch · Interview · Diagnose**

<br/>

| 中文 | English | 日本語 | Español |
|:----:|:-------:|:------:|:------:|
| 把真实经历变成可投递、可面试的**证据系统** | Turn real experience into **matchable, interview-ready evidence** | 実体験を応募・面接に耐える**証拠**へ | Convierte tu experiencia en **evidencia entrevistable** |

<br/>

`Gradio Studio` · `Cursor Skill` · `CLI` · `MCP` · Local-First

<br/>

[快速开始](#快速开始--quick-start) ·
[Studio](#compass-studio) ·
[能力](#核心能力) ·
[命令](#slash--cli) ·
[迭代](docs/ITERATION.md) ·
[合规](docs/COMPLIANCE.md)

</div>

---

## 快速开始 / Quick Start

```bash
# Windows
.\scripts\install.ps1
pip install -e "packages/compass-core[dev,studio,live,rag]"
pip install -r apps/studio/requirements.txt
pip install -r apps/interview-live/requirements.txt

# Docker（推荐试用）
docker compose up --build
# Studio http://127.0.0.1:7860 · Live http://127.0.0.1:8766

# 本地
python -m compass_core.cli crawl-llm --root content
python -m compass_core.cli studio --root content --port 7860
python -m compass_core.cli live --root content --port 8766
```

HF Space 卡片说明见 [README_SPACE.md](README_SPACE.md)（Demo 仅 fixtures）。

Unix: `./install.sh` then the same `crawl-llm` / `studio` commands.

---

## Compass Studio

实时交互工作台（Gradio）：

| Tab | 做什么 |
|:----|:-------|
| Resume | 上传 PDF / 图片 / 文本 → 证据草稿 |
| Job + Pipeline | 粘贴 JD → 匹配 · 主题简历 · 面试包 · 缺口罗盘 |
| Interview | **打字** 或 **口语**（TTS 读题 + 录音 ASR） |
| Bank | 检索题库 · 一键刷新 LLM/Agent 爬取 |
| About | 多语言说明 |

口语依赖：`edge-tts`（TTS，默认）；`faster-whisper`（ASR，可选）。无 ASR 时可纯文本作答。

---

## 核心能力

| 能力 | 说明 |
|:-----|:-----|
| **缺口罗盘** | 证据 / 叙事 / 技能 / 流程 + 做什么 / 证明物 / 耗时 |
| **证据门禁** | 无 `evidence_id` 不写作成绩；可标 `UNVERIFIED` |
| **12 主题模板** | JSON Resume 兼容 HTML/MD，[来源备注](packages/compass-core/compass_core/assets/templates/SOURCES.md) |
| **LLM/Agent 题库** | 精选 + 公开源爬取，[来源备注](packages/compass-core/compass_core/assets/questions/SOURCES.md) |
| **合规发现** | 粘贴 / RSS / career 页；默认不做平台自动投递 |

闭环：`上传简历 → 岗位 → patch → 面试(文本/语音) → 诊断 → bridge`

```mermaid
flowchart LR
  upload[Upload PDF/Image] --> evidence[evidence/]
  evidence --> jd[Paste JD]
  jd --> pipe[Match Resume Interview Diagnose]
  pipe --> voice[Text or Oral ASR/TTS]
  voice --> gap[Gap Compass]
  gap --> bank[LLM Agent Bank]
```

---

## Slash / CLI

| Skill | CLI | 作用 |
|:------|:----|:-----|
| `/intake` | `intake` | 画像 |
| `/evidence` | `evidence-index` | 证据索引 |
| `/discover` | `discover` | 岗位导入 |
| `/resume` | `resume-patch` | 主题 patch |
| `/interview` | `interview-pack` | 面试包 |
| `/diagnose` | `diagnose` | 缺口罗盘 |
| `/desk` | `desk` | 轻量看板 |
| — | `studio` | **Gradio 主界面** |
| — | `crawl-llm` | 刷新 LLM/Agent 题 |

完整 Skill：[skill/SKILL.md](skill/SKILL.md)

---

## 仓库结构

```
apps/studio/       # Gradio 交互（主 UI）
apps/desk/         # 轻量 HTTP 看板
packages/          # compass-core · compass-mcp
skill/             # Cursor Skill
collectors/        # 合规采集 + 快照
content/           # 本地产物
docs/              # 合规 · 竞品 · 迭代计划
```

---

## 合规 / Compliance

- 题库爬取仅限**公开 raw/文档**；拒绝登录招聘站深度抓取。
- 简历文件仅存本地 `content/`，默认不上云。
- 详见 [docs/COMPLIANCE.md](docs/COMPLIANCE.md)。

---

## License

MIT — [LICENSE](LICENSE)
