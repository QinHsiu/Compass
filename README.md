<div align="center">

# Compass

### Evidence-Driven Job Compass
### 证据驱动求职罗盘

<br/>

[![version](https://img.shields.io/badge/version-0.7.0-0F766E?style=for-the-badge&labelColor=1A2332)](VERSION)
[![tests](https://img.shields.io/badge/tests-pytest-0F766E?style=for-the-badge&labelColor=1A2332)](packages/compass-core/tests)
[![web](https://img.shields.io/badge/UI-WebSocket%20Web-0F766E?style=for-the-badge&labelColor=1A2332)](apps/interview-live)
[![license](https://img.shields.io/badge/license-MIT-5C6B7A?style=for-the-badge&labelColor=1A2332)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/QinHsiu/Compass?style=for-the-badge&labelColor=1A2332)](https://github.com/QinHsiu/Compass/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/QinHsiu/Compass?style=for-the-badge&labelColor=1A2332)](https://github.com/QinHsiu/Compass/issues)

<br/>

**Upload · Match · Patch · Interview · Diagnose**

<br/>

| 中文 | English | 日本語 | Español |
|:----:|:-------:|:------:|:------:|
| 把真实经历变成可投递、可面试的**证据系统** | Turn real experience into **matchable, interview-ready evidence** | 実体験を応募・面接に耐える**証拠**へ | Convierte tu experiencia en **evidencia entrevistable** |

<br/>

`Compass Web (WebSocket)` · `Cursor Skill` · `CLI` · `MCP` · Local-First

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

**硬件建议（Docker）**：≥ **4GB RAM**、2 CPU。轻量本地可不装 `[rag]`。  
环境变量模板：[`.env.example`](.env.example)（密钥**可选**；无 Key 仍可跑 Demo）。

```bash
# 1) 分层安装（推荐）
pip install -e "packages/compass-core"                 # 核心 CLI
pip install -e "packages/compass-core[live]"           # Web 主界面
pip install -r requirements-web.txt                    # 钉版本范围
# 可选：
# pip install -e "packages/compass-core[rag]"          # Chroma 语义检索
# pip install -e "packages/compass-core[asr]"          # faster-whisper
# pip install -e "packages/compass-core[pdf,dev,studio]"

# 2) Docker（推荐试用）
cp .env.example .env   # 按需填写
docker compose up --build
# → http://127.0.0.1:8766/
# 可选 Gradio：docker compose --profile gradio up

# 3) 本地 Web
python -m compass_core.cli web --root content --port 8766
```

演示截图见 [docs/assets/demo-pipeline.svg](docs/assets/demo-pipeline.svg)。  
HF Space：[README_SPACE.md](README_SPACE.md) · 传播文：[docs/launch_article_zh.md](docs/launch_article_zh.md) · [Good First Issues](docs/GOOD_FIRST_ISSUES.md) · [Star the repo](https://github.com/QinHsiu/Compass)

依赖复现：见 [`requirements-lock.txt`](requirements-lock.txt)（如何 regenerate 见文件头注释）。
---

## Compass Web（主界面）

宽屏 WebSocket 工作台（`apps/interview-live`）：

| 区 | 做什么 |
|:---|:-------|
| **职业探索** | 经历/文件 → 置信度分流 → 直接规划或 Holland RIASEC 测评 → 六维可视化与交互报告 → 一键进求职准备 |
| 上传简历 | PDF / 图片 / 文本 → 证据草稿 |
| 求职准备 | JD → 匹配 · 主题简历 · 面试包 · 诊断 · 图谱 |
| 实时面试 | WebSocket 追问 + Web Speech + Monaco |
| 题库 | Token / 语义 RAG |
| 证据图谱 | `/timeline` |

```bash
python -m compass_core.cli web --root content --port 8766
```

Gradio Studio 仍可用（可选）：`compass studio`。

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
| `/life` | `life explore\|answer\|refine\|export` | 兴趣探索 → 职业规划（RIASEC） |
| `/intake` | `intake` | 画像 |
| `/evidence` | `evidence-index` | 证据索引 |
| `/discover` | `discover` | 岗位导入 |
| `/resume` | `resume-patch` | 主题 patch |
| `/interview` | `interview-pack` | 面试包 |
| `/diagnose` | `diagnose` | 缺口罗盘 |
| `/desk` | `desk` | 轻量看板 |
| — | `web` / `live` | **Web 主界面** |
| — | `studio` | Gradio（可选） |
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
