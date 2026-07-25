# Compliance / 合规

## Allowed by default

- User-pasted JD text / files
- CSV / JSON / JSONL job list import into Job Warehouse
- Public RSS / Atom feeds the user configures
- Public company career / listing HTML pages (rate-limited, identifiable User-Agent)
- Public ATS JSON APIs (Greenhouse / Lever / Ashby board slugs)
- Local session files the user exports themselves (`session import`)

## Not enabled by default

- Login cookies / CDP automation against major job boards (Boss Zhipin, 拉勾, LinkedIn, …)
- Bulk scraping behind authentication walls
- Auto-submit applications
- Sending OpenTelemetry traces to a remote endpoint (opt-in via env)

## Opt-in experimental (v0.12+)

Authenticated list parsing may run only when **all** of the following hold:

1. User passes `--i-accept-tos-risk` (or sets `COMPASS_ACCEPT_TOS_RISK=1`).
2. Session material is user-provided (`content/sessions/*.storage_state.json`) — Compass does not log in for you.
3. Code path stays under `collectors/experimental/` / `compass_core.auth_collect` (fixture HTML preferred in CI).

Compass will not implement credential stuffing, captcha farms, or ToS-bypass services.

## Design rules

1. Collectors must refuse known login-required deep scrape targets by default (see `collectors/blocklist.json`).
2. Never store API keys or session files in git commits under `content/`.
3. Evidence gate: do not invent work history; mark unverifiable claims `UNVERIFIED`.
4. Job Warehouse / MCP `jobs.search` reads **local** data only — not a hosted third-party 18万岗 dump.
5. APM: default spans stay in `logs/spans.jsonl`; OTLP only when `OTEL_EXPORTER_OTLP_ENDPOINT` or `COMPASS_OTEL=1`.

## Research-only extensions

Experimental auto-apply adapters may live under `collectors/experimental/` but must stay disabled unless the user explicitly opts in and accepts ToS risk. They are **out of main path**.
