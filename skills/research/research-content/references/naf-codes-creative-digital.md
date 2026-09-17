# NAF Codes — Creative & Digital Sectors

Full mapping of NAF/APE codes for the creative, digital, and communication sectors in France. Use with `recherche-entreprises.api.gouv.fr` via the `activite_principale` parameter.

## Information Technology

| Code | Label (FR) | Label (EN) |
|------|-----------|------------|
| 62.01Z | Programmation informatique | Computer programming |
| 62.02A | Conseil en systèmes et logiciels informatiques | IT systems/software consulting |
| 62.02B | Tierce maintenance de systèmes et d'applications | Third-party systems maintenance |
| 62.03Z | Gestion d'installations informatiques | IT facilities management |
| 62.09Z | Autres activités informatiques | Other IT activities |
| 63.11Z | Traitement de données, hébergement | Data processing, hosting |
| 63.12Z | Portails Internet | Web portals |
| 63.99Z | Autres services d'information n.c.a. | Other information services |

## Advertising & Marketing

| Code | Label (FR) | Label (EN) |
|------|-----------|------------|
| 73.11Z | Activités des agences de publicité | Advertising agencies |
| 73.12Z | Régie publicitaire de médias | Media ad sales |
| 73.20Z | Études de marché et sondages | Market research & polling |
| 70.21Z | Conseil en relations publiques et communication | PR & communications consulting |

## Design & Photography

| Code | Label (FR) | Label (EN) |
|------|-----------|------------|
| 74.10Z | Activités spécialisées de design | Specialized design |
| 74.20Z | Activités photographiques | Photography |
| 18.13Z | Activités de pré-presse | Pre-press |

## Media Production

| Code | Label (FR) | Label (EN) |
|------|-----------|------------|
| 58.11Z | Édition de livres | Book publishing |
| 58.19Z | Autres activités d'édition | Other publishing |
| 59.11Z | Production de films et de programmes pour la télévision | Film/TV production |
| 59.12Z | Post-production de films et de programmes | Post-production |
| 59.20Z | Enregistrement sonore et édition musicale | Sound recording & music publishing |

## Usage

```bash
curl -s "https://recherche-entreprises.api.gouv.fr/search?q=&code_postal=14000&activite_principale=62.01Z&per_page=25" | python -c "
import sys,json
data = json.load(sys.stdin)
for r in data.get('results', []):
    print(r.get('nom_complet',''))
"
```

**Note**: `per_page` max is 25, not 50. Use `code_postal` (not `commune`) for location filtering.
