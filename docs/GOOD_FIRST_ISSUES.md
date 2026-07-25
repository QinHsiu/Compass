# Good First Issues

欢迎认领。提交前请阅读 [CONTRIBUTING.md](../CONTRIBUTING.md)，**勿提交** `content/` 下个人简历/面试日志。

| # | 标题 | 标签 | 说明 |
|:--|:-----|:-----|:-----|
| 1 | 增补 LLM/Agent 题库 5 条 | `bank` `good first issue` | 向 `assets/questions/` 或 `content/questions/extra.jsonl` 追加合规公开题，含 `id/topic/q/tags/source`，并尽量补 `i18n_zh.json` |
| 2 | Web 移动端 CSS 微调 | `ui` `good first issue` | 在 `apps/interview-live/static/app.css` 的窄屏断点下改善侧栏/结果区，附 375px 截图 |
| 3 | 文档错别字 / 链接检查 | `docs` `good first issue` | 扫 README、COMPLIANCE、launch 文，修死链与中英不一致 |
| 4 | Timeline 边 case | `core` `good first issue` | 无 resume.json 仅有 oral_log 时，`build_timeline` 仍应产出 interview 节点；补 pytest |
| 5 | 西语文案 | `i18n` `good first issue` | 为 Web `i18n.js` 的 Español 补齐漏翻键名，保持语气一致 |
| 6 | ~~图谱筛选 UX~~ | `ui` | ✅ v0.18：`fConn` + localStorage |
| 7 | `.env.example` 文案 | `docs` `good first issue` | 为 DeepSeek / Ollama 各补一段「复制即用」注释示例（勿提交真实密钥） |
| 8 | ~~行业题库起步~~ | `bank` | ✅ v0.18：`industry_packs.jsonl` + `questions --industry` |
| 9 | rag-eval 查询扩充 | `core` `good first issue` | 向 `content/fixtures/demo/rag_queries.jsonl` 再加 3 条带 `expect_ids` 的查询（hit@k 已写入 obs gauges） |
| 10 | Demo 截图更新 | `docs` `good first issue` | 用最新 Web UI 重导出 `docs/assets/demo-pipeline.svg`（或提供 png） |
| 11 | finance/consulting 题再扩 5 条 | `bank` `good first issue` | 向 `assets/questions/industry_packs.jsonl` 追加合规题（含 hint） |
| 12 | Prom 面板示例 | `docs` `observability` | 给 `obs export-prom` / Desk `/metrics` 写一段 Grafana 抓取说明 |

开 Issue 时请使用模板：`.github/ISSUE_TEMPLATE/`。
