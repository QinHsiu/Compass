# 传播提纲 · Compass 技术解读（中文）

## 标题候选

1. 不做编故事的 AI 求职：我们用「证据门禁」重做模拟面试
2. 从 Gradio 到 WebSocket：开源求职罗盘如何补齐实时语音短板
3. 缺口罗盘：比匹配分更有用的四象限求职诊断

## 结构（约 2000 字）

1. **痛点**：简历 AI 瞎编 / 面试工具只会刷题
2. **理念**：证据驱动 — 每条经历可追溯 `evidence_id`
3. **闭环演示**：上传 → JD → Patch → Live 追问 → 缺口罗盘
4. **架构**：compass-core + Studio + Interview Live + Skill/MCP
5. **对比**：相对 DeepInterview/OfferCat — 我们不拼 LiveKit，拼可验证闭环
6. **开源试用**：`docker compose up` / HF Space Demo（仅 fixtures）
7. **Call to action**：Star、Issue、贡献题库 `extra.jsonl`

## 渠道

- 掘金 / 知乎专栏 / 小红书短图（截图 Studio 英雄区 + Live 对话）
- GitHub Discussion：征集 LLM/Agent 面经（合规粘贴）

## 合规提醒

文中强调：不爬登录墙、不自动投递、Demo 不含真实简历。
