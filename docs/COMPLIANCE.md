# Compliance / 合规

## Allowed by default

- User-pasted JD text / files
- CSV / JSON job list import
- Public RSS / Atom feeds the user configures
- Public company career / listing HTML pages (rate-limited, identifiable User-Agent)

## Not enabled by default

- Login cookies / CDP automation against major job boards (e.g. Boss Zhipin, LinkedIn Easy Apply bots)
- Bulk scraping behind authentication walls
- Auto-submit applications

## Design rules

1. Collectors must refuse known login-required deep scrape targets (see `collectors/blocklist.json`).
2. Never store API keys in `content/` git commits.
3. Evidence gate: do not invent work history; mark unverifiable claims `UNVERIFIED`.

## Research-only extensions

Experimental auto-apply adapters may live under `collectors/experimental/` but must stay disabled unless the user explicitly opts in and accepts ToS risk. They are **out of main path**.
