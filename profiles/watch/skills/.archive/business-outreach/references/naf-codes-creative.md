# NAF Codes — Creative & Digital Sectors (France)

NAF (Nomenclature d'Activités Française) codes for the creative, digital, and communication industries. Use these with the SIRENE API's `activite_principale` parameter.

## Information Technology

| Code | Label | Typical companies |
|---|---|---|
| `62.01Z` | Programmation informatique | Software dev, web agencies, app developers |
| `62.02A` | Conseil en systèmes et logiciels | IT consulting, digital transformation |
| `62.02B` | Tierce maintenance de systèmes | IT maintenance, support |
| `62.03Z` | Gestion d'installations informatiques | IT facility management |
| `62.09Z` | Autres activités informatiques | Miscellaneous IT services |
| `63.11Z` | Traitement de données, hébergement | Data centers, cloud hosting |
| `63.12Z` | Portails Internet | Web portals, SaaS platforms |
| `63.99Z` | Autres services d'information | Information services n.e.c. |

## Advertising & Communication

| Code | Label | Typical companies |
|---|---|---|
| `73.11Z` | Activités des agences de publicité | Ad agencies, creative agencies |
| `73.12Z` | Régie publicitaire de médias | Media buying, ad networks |
| `73.20Z` | Études de marché et sondages | Market research, polling |
| `70.21Z` | Conseil en relations publiques | PR agencies, corporate comms |

## Design & Creative

| Code | Label | Typical companies |
|---|---|---|
| `74.10Z` | Activités spécialisées de design | Graphic design, UX/UI, product design |
| `74.20Z` | Activités photographiques | Photography studios, photo agencies |
| `18.13Z` | Activités de pré-presse | Prepress, typesetting, layout |

## Media Production

| Code | Label | Typical companies |
|---|---|---|
| `58.19Z` | Autres activités d'édition | Publishing (non-book) |
| `59.11Z` | Production de films et de programmes TV | Film, TV, video production |
| `59.12Z` | Post-production | Editing, VFX, color grading |
| `59.20Z` | Enregistrement sonore et édition musicale | Recording studios, music production |

## Complete Curl Example

```bash
# Fetch all design companies in Caen (14000)
curl -s "https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=14000&activite_principale=74.10Z&per_page=25"
```

## Common Commune Codes (Normandy)

| City | Postal | INSEE Code |
|---|---|---|
| Caen | 14000 | 14118 |
| Hérouville-Saint-Clair | 14200 | 14327 |
| Mondeville | 14120 | 14437 |
| Ifs | 14123 | 14341 |
| Ouistreham | 14150 | 14488 |
