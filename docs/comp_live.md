# Live compensation / 实时薪资

## Why not “直接爬 OfferShow 小程序”

官方入口在 **微信小程序**（校招 OfferShow / 社招 OfferHero），帮助中心明确要求第三方勿频繁爬取。Compass 因此采用：

1. **可配置实时 API**（你自建 / 社区兼容网关）
2. **抓包/导出导入**（你在合法自用前提下导出 JSON）
3. **本地 JD 薪资带**（已入库岗位原文中的薪资区间）

## Quick start

```bash
# 1) 配置 OfferShow 兼容网关（示例）
set COMPASS_OFFERSHOW_API=https://your-gateway.example.com
set COMPASS_OFFERSHOW_TOKEN=xxx
# 或复制 assets 示例到 content：
# copy packages/.../assets/comp_sources.example.json content/comp/sources.json

# 2) 实时查询（必须显式接受 ToS 风险）
python -m compass_core.cli comp lookup --root content --live --query "字节+后端+北京" --i-accept-tos-risk

# 3) 强制刷新缓存
python -m compass_core.cli comp refresh --root content --query "ML Platform 上海" --i-accept-tos-risk

# 4) 无网关时：导入你从小程序/Charles 导出的 JSON
python -m compass_core.cli comp ingest-live --root content --file offershow_capture.json
```

## Expected OfferShow-compatible JSON

```json
{
  "data": [
    {
      "company": "字节跳动",
      "job": "后端开发",
      "city": "北京",
      "salary": "30-40k*15",
      "level": "2-1"
    }
  ]
}
```

Also accepts `results` / `rows` / `offers` / JSONL / CSV with headers `company,title,city,salary`.

## Multi-source flags (`--sources`)

`offershow,http,levels,extra,jobs,career,ats,warehouse,cache`

- `levels` → `COMPASS_LEVELS_API`
- `extra` → `content/comp/sources.json` `extra_endpoints[]`
- `career` / `warehouse` → salary tokens from Job Warehouse after `recommend jobs`

## Env

| Var | Meaning |
|:--|:--|
| `COMPASS_OFFERSHOW_API` | Base URL for live search |
| `COMPASS_OFFERSHOW_TOKEN` | access_token if required |
| `COMPASS_OFFERSHOW_SEARCH_PATH` | default `/salary/query` |
| `COMPASS_COMP_LIVE_URL` | Generic JSON search URL |
| `COMPASS_COMP_LIVE_TTL` | Cache TTL seconds (default 3600) |
| `COMPASS_ACCEPT_TOS_RISK=1` | Same as `--i-accept-tos-risk` |

## MCP

`comp_lookup(..., live=true)` when wired with accept flag via env.
