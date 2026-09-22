# SIRENE API Response Format

## Example response for `62.01Z` (Programmation informatique) in Caen (14000)

```json
{
  "results": [
    {
      "siren": "380474494",
      "nom_complet": "EURO INFORMATION DEVELOPPEMENTS (EID)",
      "nom_raison_sociale": "EURO INFORMATION DEVELOPPEMENTS",
      "sigle": "EID",
      "activite_principale": "62.01Z",
      "siege": {
        "activite_principale": "62.02B",
        "adresse": "4 RUE FREDERIC-GUILLAUME RAIFFEISEN 67000 STRASBOURG",
        "code_postal": "67000",
        "commune": "67482",
        "libelle_commune": "STRASBOURG",
        "libelle_voie": "FREDERIC-GUILLAUME RAIFFEISEN",
        "numero_voie": "4",
        "type_voie": "RUE",
        "siret": "38047449400016",
        "date_creation": "1991-01-01"
      },
      "date_creation": "1991-01-01",
      "etat_administratif": "A",
      "tranche_effectif_salarie": "51"
    }
  ],
  "total_results": 537,
  "page": 1,
  "per_page": 25,
  "total_pages": 22
}
```

## Key Observations

- **No `site_web` or `email` field** — the API only provides legal registration data
- **`commune` field uses INSEE code** (67482 = Strasbourg), not name
- **`total_results` may differ from actual pages** — some pages return empty results (162 bytes = `{"results":[],...}`) when the real count is lower
- **Pages beyond real data return 162 bytes** (empty results array) — safe to collect and filter later
- **`tranche_effectif_salarie`** gives company size: "51" = 50-99 employees, "12" = 20-49, etc.

## 162-byte Empty Page Pattern

```json
{"results":[],"total_results":339,"page":14,"per_page":25,"total_pages":14}
```

Always parse and check `len(results)` — don't assume every page has data.
