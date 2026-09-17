<!-- Source: original/SKILL.md (archived 2026-09-10) -->

---
name: company-research
description: "Compile business registries by sector. Export to Excel."
version: 1.0.0
metadata:
  hermes:
    tags: [business, companies, outreach, lead-generation, france, sirene]
    category: research
---

# Company Research

Crawl, filter, and compile company lists for outreach, job applications, or market research. Covers official business registries (France's SIRENE via data.gouv.fr API), sector filtering via NAF/APE codes, deduplication, and Excel export.

## When to Use

- Building a list of companies in a specific city/region for job applications or sales outreach
- Filtering companies by industry sector (NAF/APE codes in France)
- Any task requiring structured company data (name, address, sector) from official sources

## Preferred Workflow

1. **Identify target**: city (postal code), sector(s), and any exclusion filters
2. **Query the API**: use the French government's `recherche-entreprises.api.gouv.fr` endpoint with `code_postal` and `activite_principale` (NAF code)
3. **Filter & deduplicate**: remove national chains, public institutions, and duplicates
4. **Export**: JSON first, then Excel with one sheet per sector + a summary sheet

## API Reference: `recherche-entreprises.api.gouv.fr`

```
Base URL: https://recherche-entreprises.api.gouv.fr/search
Method: GET
Parameters:
  q                     — free-text search (use empty string for no filter)
  code_postal           — postal code (e.g., 14000 for Caen) — USE THIS, not `commune`
  activite_principale   — NAF/APE code (e.g., 62.01Z for programming)
  per_page              — 1–25 (max 25, default 10). Using >25 returns 400 error.
  page                  — page number (1-indexed)
```

### Critical Constraints

- **`per_page` max is 25**, not 50. Values above 25 return HTTP 400 with an error message.
- **Use `code_postal`, NOT `commune`**. The `commune` parameter (whether INSEE code like `14118` or string like `"Caen"`) returns 0 results. `code_postal=14000` works.
- **Always use `curl` from the terminal**, not Python `urllib` from `execute_code` — the sandbox's network stack routes differently and may return HTTP 400 on identical requests. Terminal `curl` is reliable.
- **On Windows git-bash, use `C:/Users/...` paths with curl**, NOT `/c/Users/...`. The `/c/` prefix causes `curl -o` to fail with "No such file or directory" (exit code 23). The `C:/...` form works reliably.

### NAF Codes for Creative/Digital Sectors

See `references/naf-codes-creative-digital.md` for the full mapping. Quick reference:

| Code | Sector |
|------|--------|
| 62.01Z | Programmation informatique |
| 62.02A | Conseil systèmes/logiciels |
| 73.11Z | Agences de publicité |
| 74.10Z | Design spécialisé |
| 74.20Z | Photographie |
| 70.21Z | Conseil RP/communication |
| 59.11Z | Production films/vidéo |
| 59.20Z | Enregistrement sonore/musique |

## Filtering & Deduplication

After fetching results, always:

1. **Skip national chains/public institutions** — maintain a skip list of patterns (LA POSTE, EDF, ORANGE, BANQUE, MAIRIE, etc.)
2. **Deduplicate by normalized name** — companies may appear under multiple NAF codes or with slight name variations. Normalize (uppercase, first 40 chars) and use a `set()`.
3. **Sort by sector then name** for readability.

## Excel Export (openpyxl)

- **Sanitize sheet names**: Excel forbids `/`, `\`, `*`, `?`, `:`, `[`, `]` in sheet titles. Replace `/` with `-` before calling `create_sheet()`.
- Create one "Vue d'ensemble" (summary) sheet with stats, then one sheet per sector, then one "Toutes les entreprises" sheet.
- Apply: frozen header row, auto-filter, alternating row colors, dark header theme.

## Verification

1. Spot-check that addresses are in the target city (check postal codes in raw data)
2. Verify no national chains slipped through the skip filter
3. Confirm sheet names open without Excel warnings
4. Check that sector counts match across summary and detail sheets

## Supporting Files

- `references/naf-codes-creative-digital.md` — complete NAF code mapping for creative/digital sectors
- `references/pagination-batch-pattern.md` — bash template for parallel paginated fetching across multiple NAF codes
