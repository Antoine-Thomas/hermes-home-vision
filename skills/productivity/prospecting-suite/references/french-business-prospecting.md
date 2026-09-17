# French Business Prospecting

> Source skill: `french-business-prospecting` (v1.0.0). Consolidated into the umbrella skill on 2026-09-10.


Crawl French businesses by sector and location via the official `recherche-entreprises.api.gouv.fr` API, enrich with email addresses, and generate candidature/spontaneous-application materials.

## When to Use

User wants to find businesses in a French city/region for prospecting, job applications, or market research. Triggers on: "trouver des entreprises à [ville]", "crawl entreprises", "candidatures", "prospection [ville]", "annuaire entreprises [code postal]".

## Pipeline Overview

1. **Crawl** — Query the SIRENE API by postal code + NAF codes
2. **Enrich** — Discover email addresses via 3 methods (DNS MX, domain scraping, Hunter.io)
3. **Generate** — Produce Excel file + email templates for candidatures

---

## Step 1: Crawl (API SIRENE)

### API Endpoint

```
https://recherche-entreprises.api.gouv.fr/search
```

### Critical Parameters

| Parameter | Example | Notes |
|---|---|---|
| `q` | `""` or `"agence"` | Free-text search (can be empty) |
| `code_postal` | `14000` | **Use this, NOT `commune`** — `commune` returns 0 results |
| `activite_principale` | `62.01Z` | NAF code filter |
| `per_page` | `25` | **MAX is 25** (not 50!) — API rejects with error if >25 |
| `page` | `1` | Pagination starting at 1 |

### Execution

**Always use `curl` from the terminal, never Python `urllib`.** On Windows, Python urllib returns HTTP 400 for these requests even when curl succeeds (proxy/config issue).

**Use Windows paths with curl `-o`**, not MSYS paths:
```bash
# CORRECT:
curl -s "..." -o "C:/Users/searc/Desktop/output.json"

# WRONG (MSYS paths fail silently with curl -o):
curl -s "..." -o "/c/Users/searc/Desktop/output.json"
```

**Escape `&` in shell loops** — wrap the full URL in double quotes or the shell interprets `&` as backgrounding:
```bash
# CORRECT:
curl -s "https://...?q=&code_postal=14000&per_page=25"

# WRONG (shell backgrounding on bare &):
curl -s https://...?q=&code_postal=14000&per_page=25
```

### Relevant NAF Codes (Creative/Digital Sector)

| Code | Label |
|---|---|
| 62.01Z | Programmation informatique |
| 62.02A | Conseil systèmes/logiciels |
| 62.02B | Tierce maintenance info |
| 63.11Z | Traitement données/hébergement |
| 63.12Z | Portails Internet |
| 73.11Z | Agences de publicité |
| 73.12Z | Régie publicitaire |
| 73.20Z | Études de marché/sondages |
| 74.10Z | Design spécialisé |
| 74.20Z | Photographie |
| 70.21Z | Conseil RP/communication |
| 18.13Z | Pré-presse |
| 58.19Z | Édition |
| 59.11Z | Production films/vidéo |
| 59.12Z | Post-production |
| 59.20Z | Enregistrement sonore/musique |

### Pagination Strategy

1. First call with `per_page=25&page=1` to get `total_results`
2. Compute `pages = (total_results + 24) // 25`
3. Loop pages 1..N, fetch each
4. Parallelize: 8 concurrent curl calls per batch, 1s delay between batches
5. Use bash `&` + `wait` pattern

### Response Parsing

Each result has:
- `nom_complet` — Full company name
- `siege.numero_voie`, `siege.type_voie`, `siege.libelle_voie` — Address parts
- `activite_principale` — NAF code
- `siege.code_postal` — Postal code

**No email or website field exists in this API** — enrichment must be done separately.

### Filtering

Skip large nationals: LA POSTE, EDF, ORANGE, SNCF, BANQUE, ASSURANCE, CARREFOUR, AUCHAN, etc. Also skip public institutions (MAIRIE, PREFECTURE, UNIVERSITE, CHU, LYCEE).

---

## Step 2: Email Discovery

Three methods, in order of speed:

### A. DNS MX Generation (fastest, ~30% hit rate)

For each company:
1. Clean the name: remove parens, accents, special chars → lowercase alphanumeric
2. Guess domains: `nomclean.fr`, `nomclean.com`
3. Check MX record: `nslookup -type=mx domain`
4. If MX exists, propose: `contact@domain`, `info@domain`, `bonjour@domain`

Pitfall: `subprocess.run` with nslookup can throw UnicodeDecodeError on Windows — use `errors='ignore'` in decode or wrap in try/except.

### B. Direct Domain Scraping (~15% hit rate, 5-10s/company)

For each company:
1. Guess domain: `www.nomclean.fr`
2. Try loading `https://www.domain` and `http://www.domain` (skip SSL verify)
3. Extract emails from homepage HTML: `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`
4. Also try `/contact` page
5. Filter out image-like emails (`.png@`, `.jpg@`, sentry keys)

### C. Hunter.io (most reliable, requires API key)

User needs free account at hunter.io → API key. Then:
```
GET https://api.hunter.io/v2/domain-search?domain=example.com&api_key=KEY
```

---

## Step 3: Generate Deliverables

### Excel File

Use `openpyxl`. Style: dark header (#1A1A2E / #0F3460), accent (#E94560), Segoe UI font, alternating row shading.

Structure:
- "Vue d'ensemble" sheet: stats, sector breakdown
- "Toutes les entreprises" sheet: all data
- One sheet per sector (max 31 chars, replace `/` with `-`)

Columns: Nom | Adresse | Ville | Secteur | Code NAF

### Email Templates

Use `{{VARIABLES}}` for personalization:
- `{{PRENOM}}`, `{{NOM}}` — extracted from company name
- `{{ENTREPRISE}}` — full company name
- `{{SECTEUR}}` — NAF label
- `{{EMAIL}}` — discovered email (or placeholder `[EMAIL_A_TROUVER]`)

Template should be:
- **Sobre** — one accent color, no over-design (matches user preference for simplicity)
- Professional, in French
- Include: who you are, what you offer (4 pillars), portfolio links, CTA
- Unsubscribe footer

### Publipostage Script

Python script that reads JSON + template → generates one `.txt` file per company in an `emails_candidatures/` folder.

---

## Pitfalls

- **`commune` parameter: always 0 results** — use `code_postal` instead
- **`per_page > 25`: API returns error** — "Veuillez indiquer un paramètre `per_page` entre `1` et `25`"
- **Python urllib: HTTP 400 on this API** from both `execute_code` sandbox and terminal scripts — use `curl` exclusively
- **MSYS paths with curl `-o`**: `/c/Users/...` silently fails — use `C:/Users/...`
- **Shell `&` in URL**: escape or wrap entire URL in double quotes
- **N/A sheet names**: Excel rejects `/`, `\`, `*`, `?`, `:`, `[`, `]` — replace `/` with `-`
- **openpyxl not pre-installed**: `pip install openpyxl` before generating Excel
- **`nslookup` Unicode errors on Windows**: wrap subprocess output decode with `errors='ignore'`

## Related Skills

- `xlsx` — Excel generation with openpyxl
- `email` / `email-campaign` — sending campaigns

## Support Files

- `templates/pagination-script.sh` — Bash template for parallel paginated API crawling
- `references/api-response-format.md` — SIRENE API response structure and quirks
