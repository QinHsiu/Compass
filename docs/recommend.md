# Job recommend + multi-source compensation

## Job recommend（公司官网 / 公开 ATS）

配置 `content/companies.yml`（可用仓库示例），然后：

```bash
python -m compass_core.cli recommend jobs --root content --keyword "ML|LLM" --location "Shanghai|Remote" --limit 20
# 等价
python -m compass_core.cli discover --root content --source companies --keyword ML --limit 20
```

每个公司优先用公开 ATS JSON（`greenhouse:` / `lever:` / `ashby:`），否则抓取 `career_url` 官网（JSON-LD JobPosting + 职位链接），并可从页面自动识别 Greenhouse/Lever/Ashby。

结果：匹配排序写入 `content/recommendations/latest.json`，同时入库 Job Warehouse。

**不做**：Boss/拉勾/LinkedIn 登录墙深爬（见 blocklist）。

## 薪资多源（`--live`）

| Source | 含义 |
|:--|:--|
| `offershow` | `COMPASS_OFFERSHOW_API` 兼容网关 |
| `http` | `COMPASS_COMP_LIVE_URL` |
| `levels` | `COMPASS_LEVELS_API` |
| `extra` | `sources.json` → `extra_endpoints[]` |
| `jobs` | 已匹配 JD 文本薪资带 |
| `career` / `ats` / `warehouse` | 官网/ATS 爬取入库后的 raw 薪资 |
| `cache` | 本地 live 缓存 |

```bash
python -m compass_core.cli comp lookup --root content --live \
  --sources offershow,levels,http,jobs,career --query "后端 北京" --i-accept-tos-risk
```

详见 `docs/comp_live.md`。
