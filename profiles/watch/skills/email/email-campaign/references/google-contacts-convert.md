# Google Contacts Export → prospects.csv

Convertir un export Google Contacts (fichier CSV Google) vers le format `prospects.csv` utilisé par la campagne d'emailing.

## Format source (Google)

Colonnes d'intérêt dans l'export Google :
- `First Name` → prénom
- `Last Name` → nom
- `E-mail 1 - Value` → email
- `Organization Name` → entreprise

Note : l'export Google peut contenir des champs avec des sauts de ligne (champs entre guillemets). Le module `csv.DictReader` de Python les gère correctement.

## Script de conversion

```python
import csv

INPUT = r"C:\Users\...\contacts.csv"
OUTPUT = r"C:\Users\...\prospects.csv"

contacts = []

with open(INPUT, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        email = (row.get("E-mail 1 - Value") or "").strip()
        if not email:
            continue  # ignore les contacts sans email

        prenom = (row.get("First Name") or "").strip()
        nom = (row.get("Last Name") or "").strip()
        entreprise = (row.get("Organization Name") or "").strip()

        contacts.append({
            "email": email,
            "prenom": prenom,
            "nom": nom,
            "entreprise": entreprise,
        })

# Déduplication par email
seen = set()
unique = []
for c in contacts:
    key = c["email"].lower()
    if key not in seen:
        seen.add(key)
        unique.append(c)

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["email", "prenom", "nom", "entreprise"])
    writer.writeheader()
    writer.writerows(unique)

print(f"{len(contacts)} entrées avec email → {len(unique)} contacts uniques")
```

## Nettoyage post-conversion

Après conversion, vérifier et supprimer manuellement :
- Emails de notifications automatiques (`notification@facebookmail.com`, `noreply@...`)
- Contacts sans prénom identifiable
- Adresses génériques (`info@`, `contact@`)
