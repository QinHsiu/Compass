# Compliance / 合规

## Allowed by default

- User-pasted JD text / files
- CSV / JSON / JSONL job list import into Job Warehouse
- Public RSS / Atom feeds the user configures
- Public company career / listing HTML pages (rate-limited, identifiable User-Agent)
- Public ATS JSON APIs (Greenhouse / Lever / Ashby / SmartRecruiters board specs)
- Public remote job APIs the user opts into (`discover --source feeds`: Remotive / Arbeitnow; configurable `content/feeds.yml`)
- Local session files the user exports themselves (`session import`)
- User-exported job-board HTML parsed via `session scout-html --i-accept-tos-risk` (no login automation)

## Not enabled by default

- Login cookies / CDP automation against major job boards (Boss Zhipin, 拉勾, LinkedIn, …)
- Bulk scraping behind authentication walls (including Boss salary CDP / font bypass)
- Auto-submit applications
- Bulk Levels.fyi / OfferShow reverse-engineered crawlers — use user gateway or `comp ingest-live` (see `docs/comp_live.md`)
- Sending OpenTelemetry traces to a remote endpoint (opt-in via env)
- Third-party Crawl4AI / JobSpy / Oxylabs as runtime dependencies (patterns may be ported first-party)

## Opt-in experimental (v0.12+)

Authenticated list parsing may run only when **all** of the following hold:

1. User passes `--i-accept-tos-risk` (or sets `COMPASS_ACCEPT_TOS_RISK=1`).
2. Session material is user-provided (`content/sessions/*.storage_state.json`) — Compass does not log in for you.
3. Code path stays under `collectors/experimental/` / `compass_core.auth_collect` (fixture HTML preferred in CI).

## Opt-in live compensation (v0.15+)

Real-time salary (`comp lookup --live` / `comp refresh`) may call **user-configured** OfferShow-compatible HTTP APIs or generic `COMPASS_COMP_LIVE_URL`.

- Official OfferShow / OfferHero are **WeChat mini-programs**; the vendor asks third parties not to bulk-scrape. Compass does **not** ship a WeChat reverse-engineered crawler.
- Preferred paths: configure your own gateway, or `comp ingest-live` from a capture you exported for personal use.
- Local JD salary bands (`--sources jobs`) do not need network.

Compass will not implement credential stuffing, captcha farms, or ToS-bypass services.

## Design rules

1. Collectors must refuse known login-required deep scrape targets by default (see `collectors/blocklist.json`).
2. Never store API keys or session files in git commits under `content/`.
3. Evidence gate: do not invent work history; mark unverifiable claims `UNVERIFIED`.
4. Job Warehouse / MCP `jobs.search` reads **local** data only — not a hosted third-party 18万岗 dump.
5. APM: default spans stay in `logs/spans.jsonl`; OTLP only when `OTEL_EXPORTER_OTLP_ENDPOINT` or `COMPASS_OTEL=1`.
6. Job intel: never present single-source or implausible salary/hours/reputation claims as facts; mark `UNVERIFIED` / `rejected` (see `docs/intel.md`).

## Research-only extensions

Experimental auto-apply adapters may live under `collectors/experimental/` but must stay disabled unless the user explicitly opts in and accepts ToS risk. They are **out of main path**.
