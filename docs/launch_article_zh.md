# 不做编故事的 AI 求职：我们用「证据门禁」重做模拟面试

> 适合发布于掘金 / 知乎。Demo 仅使用匿名 fixtures，请勿上传真实简历到公开 Space。

## 痛点

市面上的 AI 求职工具大致分两类：一类帮你「润色」简历，结果往往编出从未做过的项目；另一类刷题式模拟面试，像题单不像考官。求职者真正需要的是：**每一条经历可追溯、可验证，并能一路走到面试追问与缺口诊断。**

## 理念：证据驱动

Compass 把每段经历写成带 `evidence_id` 的证据条目。简历 Patch、面试作答、诊断建议都必须引用这些 ID；说不清来源的内容会被门禁标出。这不是又一个「更会写」的模型，而是一套**本地优先的证据系统**。

## 闭环演示（5 分钟）

1. **上传 / fixtures**：把真实经历拆成证据草稿（Demo 用内置样例）
2. **JD 匹配**：粘贴岗位描述，得到匹配分与硬性缺口
3. **简历 Patch**：主题排版 + 证据引用，不发明指标
4. **Interview Live**：WebSocket 实时问答，自适应追问；无 Key 时规则降级
5. **缺口罗盘**：证据 / 叙事 / 技能 / 流程四象限 + 做什么 / 证明物 / 耗时
6. **证据图谱**：一眼看到 evidence → 简历条目 → 面试引用

```text
Studio(Gradio) ──┐
                 ├── compass-core（gate / match / RAG / followup）
Interview Live ──┘
Skill / CLI / MCP 同一套数据：content/
```

## 相对竞品我们拼什么

DeepInterview、alading、OfferCat、offerMaster 等在实时语音上很强。Compass **不拼 LiveKit 全家桶**，而是拼：

- 最长闭环：上传 → 匹配 → Patch → 面试 → 诊断
- 独有证据门禁与四象限缺口罗盘
- 多形态：Gradio Studio + Interview Live + Cursor Skill + CLI + MCP
- Docker / 多 LLM BYOK / Chroma RAG 已齐

刻意不做：摄像头监考、企业招聘官 SaaS、200+ 碎片工具——避免稀释求职者本地隐私定位。

## 开源试用

```bash
git clone https://github.com/QinHsiu/Compass.git
cd Compass
docker compose up --build
# Studio http://127.0.0.1:7860  → 点「一键 Demo 流水线」
# Live   http://127.0.0.1:8766  → 证据图谱 / 实时面试
```

或：`pip install -e "packages/compass-core[dev,studio,live,rag]"` 后 `python -m compass_core.cli studio --root content`。

Hugging Face Space 卡见仓库 `README_SPACE.md`（仅 fixtures）。

## Call to action

- Star / Issue：欢迎题库 `extra.jsonl`、主题 CSS、文档与西语文案
- 认领 [GOOD_FIRST_ISSUES](GOOD_FIRST_ISSUES.md)
- 讨论：合规粘贴的 LLM/Agent 面经（不爬登录墙、不自动投递）

把真实经历变成可投递、可面试的证据系统——这就是 Compass。
