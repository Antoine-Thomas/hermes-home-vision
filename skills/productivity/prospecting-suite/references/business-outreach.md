# Business Outreach

> Source skill: `business-outreach` (v1.0.0). Consolidated into the umbrella skill on 2026-09-10.


End-to-end pipeline for building targeted company lists, enriching them with contact emails, and generating personalized outreach materials.

## When to Use

The user wants to:
- Find companies in a specific city/region by industry sector
- Build a prospecting or candidature list
- Enrich company records with real email addresses
- Generate templated emails for bulk outreach

## Pipeline Overview

1. **Crawl** — query business registries (SIRENE for France) by location + industry codes
2. **Enrich** — find emails via DNS MX check, website scraping, and Hunter.io verification
3. **Generate** — create personalized emails and Excel trackers from templates

---

## Step 1: Crawl — SIRENE API (France)

Use the official `recherche-entreprises.api.gouv.fr` API. See `references/sirene-api.md` for full details.

**Quick reference:**
```bash
curl -s "https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=14000&activite_principale=62.01Z&per_page=25&page=1"
```

**Critical parameters:**
- `code_postal` — use this, NOT `commune` (the commune param returns 0 results)
- `activite_principale` — NAF code (see `references/naf-codes-creative.md`)
- `per_page` — **max 25** (API rejects values > 25 with a 400 error)
- `page` — paginate for full results

**Crawl strategy:**
- Parallelize: 8 concurrent curl requests, 1s delay between batches
- Save each page as `{NAF}_p{page}.json` for resumability
- Use `C:/path/...` format for curl `-o` on Windows (NOT `/c/...` — curl rejects MSYS paths)

**Important:** Python `urllib` from hermes sandbox/execute_code returns HTTP 400 on this API. Use `curl` from `terminal()` instead. Always quote the full URL in double quotes in bash loops to prevent `&` from being interpreted as background operator.

**Parsing:** merge all JSON files, deduplicate by `nom_complet`, filter out large national companies (La Poste, EDF, Orange, banks, retail chains, hospitals, etc.).

## Step 2: Enrich — Email Discovery

Three methods in order of reliability:

### A. Website Scraping (most reliable)
See `references/email-scraping.md` for full details.

1. Clean company name → domain: remove accents, special chars, parentheses, keep [a-z0-9]
2. Try `https://www.{name}.fr` then `.com` with 4 protocol variants
3. Scrape homepage + `/contact` page
4. Extract emails with regex, filter fakes (`user@domain.com`, `votre@email.com`, `@sentry`, `@wixpress`)

**Performance:** 10 threads, ~8 req/s, ~4.5 min for 1 850 companies. Expect ~9-15% hit rate.

### B. DNS MX Verification (medium)
Check if `contact@{domain}.fr` could receive mail via `nslookup -type=mx`. Use `subprocess.run` with `errors='ignore'` on stderr (nslookup outputs non-UTF8 chars on Windows).

### C. Hunter.io (verification only)
Hunter's free tier has very limited coverage for French SMBs. Use only for verification. API: `https://api.hunter.io/v2/email-verifier?email={email}&api_key={key}`.

## Step 3: Generate — Outreach Materials

### Template Variables
Use `{{PRENOM}}`, `{{NOM}}`, `{{ENTREPRISE}}`, `{{SECTEUR}}`, `{{EMAIL}}` in templates.

### Output Formats
- **`.txt`** — plain text body for copy-paste
- **`.eml`** — double-click to open in Outlook/Thunderbird (RFC 822 format)
- **`.csv`** (semicolon-delimited, UTF-8 BOM) — import into Brevo/Mailchimp

### Excel Tracker
Generate a styled `.xlsx` with:
- Sheet "Vue d'ensemble" — stats + sector breakdown
- Sheet "PRIORITAIRES" — only high-confidence emails
- Sheet "Toutes les entreprises" — color-coded by confidence
- One sheet per sector
- Freeze panes, auto-filters, dark-header styling

## Pitfalls

- **`commune` parameter returns 0 results.** Always use `code_postal`.
- **`per_page` > 25 returns 400.** The API error message tells you the limit.
- **Python urllib from execute_code fails (400 Bad Request).** Use curl from terminal.
- **MSYS bash: curl -o with `/c/...` paths fails.** Use `C:/...` format.
- **`&` in bash curl URLs:** always wrap the URL in double quotes inside loops.
- **Fake emails in scraped pages:** filter `@sentry.wixpress.com`, `user@domain.com`, `votre@email.com`, etc.
- **Python `subprocess.run` with nslookup** can produce UnicodeDecodeError on Windows — use `errors='ignore'`.

## References

- `references/sirene-api.md` — Full SIRENE API docs: endpoint, parameters, response format, pagination, platform-specific issues
- `references/naf-codes-creative.md` — NAF codes for creative, digital, and communication sectors with commune codes
- `references/email-scraping.md` — Domain generation, website probing, email extraction patterns, fake email filters, benchmarks
