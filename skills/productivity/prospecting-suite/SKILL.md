---
name: prospecting-suite
description: "FR/B2B prospecting: crawl SIRENE, find emails, clean+segment contacts, build outreach."
version: 1.0.0
metadata:
  hermes:
    tags: [prospecting, lead-generation, business, outreach, email, contacts, csv, segmentation, SIRENE, france, b2b]
    category: productivity
    related_skills: [email-campaign, maps]
---

# Prospecting Suite

End-to-end B2B/FR prospecting: build targeted company lists from business
registries (SIRENE), enrich them with real email addresses, clean and
segment the contact database, and generate outreach materials.

Consolidates the former `business-outreach`, `contact-filtering`, and
`french-business-prospecting` skills (archived under `.archive/productivity/`).

## When to Use

- Find companies in a city/region by industry sector ("entreprises à [ville]", "crawl entreprises").
- Build a prospecting or candidature list; enrich it with contact emails.
- Clean a raw contact CSV (remove spam, bots, pseudos) and segment A/B/C tiers.
- Generate templated outreach / candidature emails and Excel trackers.

## Three Phases

| Phase | What it does | Reference |
|---|---|---|
| 1. Crawl | SIRENE API by postal code + NAF code | `references/french-business-prospecting.md` |
| 2. Enrich | Email discovery (DNS MX, website scrape, Hunter.io) | `references/business-outreach.md` |
| 3. Clean + Segment | Filter raw CSV, score contacts, remove junk | `references/contact-filtering.md` |

`french-business-prospecting.md` covers the full FR candidature pipeline
(crawl → enrich → deliverables). `business-outreach.md` covers the generic
crawl/enrich/generate pipeline and email-scraping details.
`contact-filtering.md` covers cleaning and segmentation of any contact CSV.

## Quick Start

```bash
# 1. Crawl SIRENE (curl, NOT Python urllib) — see references/sirene-api.md
curl -s "https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=14000&activite_principale=62.01Z&per_page=25&page=1"

# 2. Filter a contact CSV — see references/contact-filtering.md
python scripts/filter-contacts.py contacts.csv --output cleaned.csv
```

## Key Pitfalls

- Use `code_postal`, never `commune` (returns 0 results); `per_page` max is 25.
- Always use `curl` from `terminal()` for SIRENE, never Python `urllib` (HTTP 400).
- Quote full URLs in double quotes in bash loops (`&` is a background operator).
- Outbound email sending/templates live in the `email-campaign` skill, not here.

## References

- `references/business-outreach.md` — generic crawl + enrich + outreach generation.
- `references/contact-filtering.md` — CSV cleaning, filtering, scoring, segmentation.
- `references/french-business-prospecting.md` — FR candidature pipeline.
- `references/sirene-api.md`, `references/naf-codes-creative.md`, `references/email-scraping.md` — crawl/enrich details.
- `references/google-contacts-csv-format.md`, `references/api-response-format.md` — formats.
- `templates/pagination-script.sh` — SIRENE pagination helper.
