# SIRENE API — Annuaire des Entreprises

Official French government API for querying company data. Free, no auth required.

## Endpoint

```
GET https://recherche-entreprises.api.gouv.fr/search
```

## Parameters

| Parameter | Type | Description | Notes |
|---|---|---|---|
| `q` | string | Full-text search | Use empty string `q=` for unfiltered |
| `code_postal` | string | Postal code filter | **Use this, NOT `commune`** (commune returns 0) |
| `activite_principale` | string | NAF code | e.g. `62.01Z` (see naf-codes-creative.md) |
| `per_page` | int | Results per page | **Max 25** (API returns 400 if > 25) |
| `page` | int | Page number | Starts at 1 |

## Response Format

```json
{
  "total_results": 537,
  "total_pages": 22,
  "page": 1,
  "per_page": 25,
  "results": [
    {
      "nom_complet": "EURO INFORMATION DEVELOPPEMENTS (EID)",
      "siege": {
        "numero_voie": "4",
        "type_voie": "RUE",
        "libelle_voie": "FREDERIC-GUILLAUME RAIFFEISEN",
        "code_postal": "67000",
        "libelle_commune": "STRASBOURG"
      },
      "activite_principale": "62.01Z"
    }
  ]
}
```

## Pagination Strategy

```bash
# Calculate pages needed
pages=$(( (total + 24) / 25 ))

# Fetch all pages
for page in $(seq 1 $pages); do
  curl -s "https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=14000&activite_principale=$naf&per_page=25&page=$page" \
    -o "C:/path/${naf}_p${page}.json"
done
```

## Key Fields for Extraction

- `nom_complet` — full company name (may include commercial name in parentheses)
- `siege.numero_voie` + `siege.type_voie` + `siege.libelle_voie` → address
- `siege.code_postal` + `siege.libelle_commune` → city
- `activite_principale` — NAF code (industry classification)
- `siren` — unique company ID
- `categorie_entreprise` — PME, ETI, GE (SMB, mid-size, large)

## Platform-Specific Issues

### Windows (MSYS2/Git Bash)
- **curl output paths:** Use `C:/Users/...` format, NOT `/c/Users/...`. Curl rejects MSYS-style paths with exit code 23.
- **`&` in URLs:** Always wrap the full URL in double quotes in bash loops.

### Hermes sandbox (execute_code)
- Python `urllib.request.urlopen` returns HTTP 400 on this API. Use `curl` via `terminal()` instead.
- The sandbox seems to route HTTP through a proxy that the API rejects.

### Hermes terminal()
- Curl works reliably. Parallelize with `&` and `wait` in bash scripts.
- Use `background=true` + `notify_on_complete=true` for long crawls.
