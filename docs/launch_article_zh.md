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
cp .env.example .env   # 密钥可选
docker compose up --build
# → http://127.0.0.1:8766/  Compass Web（主界面）
```

分层安装：`pip install -e packages/compass-core[live] && pip install -r requirements-web.txt`。  
Hugging Face Space 卡见 `README_SPACE.md`（仅 fixtures）。建议机器 **≥4GB RAM**。

## 3 分钟演示脚本（录屏/直播用）

1. 打开 `http://127.0.0.1:8766/`，侧栏语言选「中文」。
2. **求职准备** → 点「试用示例岗位」→ 等待匹配分与四类结果 Tab。
3. 下滑内嵌 **证据图谱**：只勾选「证据」，搜索某个 `ev_`，点击边查看对端。
4. **模拟面试** → 开始 → 故意答一句无证据的话 → 展示门禁未通过 → 再引用 `evidence_id` 重答。
5. （可选）题库搜 `RAG`，展示中英对照题干。

截图示意：[docs/assets/demo-pipeline.svg](assets/demo-pipeline.svg)。

## Call to action

- Star / Issue：欢迎题库 `extra.jsonl`、主题 CSS、文档与西语文案
- 认领 [GOOD_FIRST_ISSUES](GOOD_FIRST_ISSUES.md)
- 讨论：合规粘贴的 LLM/Agent 面经（不爬登录墙、不自动投递）

把真实经历变成可投递、可面试的证据系统——这就是 Compass。
