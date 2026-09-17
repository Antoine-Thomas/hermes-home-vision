---
name: research-content
description: "Router: blog/RSS monitoring, company registry (SIRENE), prediction markets (Polymarket)."
version: 1.0.0
metadata:
  hermes:
    tags: [research, rss, blogs, monitoring, companies, sirene, lead-generation, prediction-markets, polymarket]
    category: research
---

# Research Content

One router for content discovery and market-data research: blog/RSS feed
monitoring, company-registry compilation, and prediction-market queries.

Consolidates the former `blogwatcher`, `company-research`, and `polymarket`
skills (archived under `.archive/research/`). Each original SKILL.md is
preserved verbatim under `references/` with an archive-source header; their
supporting reference/script files are copied alongside.

## When to Use

- Monitor blogs / RSS/Atom feeds for updates -> `references/blogwatcher.md`
- Compile company lists by sector (SIRENE/NAF), export to Excel -> `references/company-research.md`
- Query Polymarket odds, prices, orderbooks, history -> `references/polymarket.md`

## Routing

| Request | Reference |
|---|---|
| Blog/RSS feed tracking, scan, read/unread, OPML import | `references/blogwatcher.md` |
| Company registry crawl (SIRENE, NAF codes, Excel export) | `references/company-research.md` |
| Prediction markets (Polymarket odds/prices/history) | `references/polymarket.md` |

## Quick Start

```bash
# Blog/RSS monitoring (blogwatcher-cli) — full usage in references/blogwatcher.md
blogwatcher-cli add "My Blog" https://example.com
blogwatcher-cli scan && blogwatcher-cli articles

# Company registry (SIRENE) — curl, NOT Python urllib
curl -s "https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=14000&activite_principale=62.01Z&per_page=25&page=1"

# Polymarket — helper in scripts/polymarket.py; endpoints in references/api-endpoints.md
python scripts/polymarket.py --search "will X happen"
```

## References

- `references/blogwatcher.md` — verbatim original (install, commands, env vars, examples).
- `references/company-research.md` — verbatim original (SIRENE API, dedup, Excel export).
- `references/polymarket.md` — verbatim original (3 APIs, concepts, rate limits).
- `references/naf-codes-creative-digital.md` — NAF/APE code mapping (from company-research).
- `references/pagination-batch-pattern.md` — SIRENE pagination bash template.
- `references/api-endpoints.md` — Polymarket endpoints + curl examples.

## Scripts

- `scripts/polymarket.py` — Polymarket query helper (from polymarket).

## Key Pitfalls

- SIRENE: use `code_postal` (never `commune`); `per_page` max 25; use `curl`, not Python `urllib`.
- SIRENE on Windows git-bash: use `C:/Users/...` paths with `curl -o`, not `/c/Users/...`.
- Polymarket Gamma API double-encodes `outcomePrices`/`clobTokenIds` — parse with `json.loads`.
- Blogwatcher DB lives at `~/.blogwatcher-cli/blogwatcher-cli.db`; binary is `blogwatcher-cli`.
