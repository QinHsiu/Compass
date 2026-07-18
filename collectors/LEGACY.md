# Collectors legacy notes

Historical scraping demos under `projects/wheels` (BeautifulSoup tutorials, form fillers)
inspired **parsing patterns only**:

- Fetch → parse HTML → extract links/text
- Field mapping for application forms (optional drafts)

They are **outdated** (site selectors break) and must not be copied as production crawlers.

Compass collectors are rewritten with:

- Explicit blocklist for major job boards
- Rate limit + identifiable User-Agent
- paste / rss / public career HTML only

See `docs/COMPLIANCE.md`.
