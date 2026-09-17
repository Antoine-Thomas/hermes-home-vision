# Google Contacts → prospects.csv

Conversion d'un export Google Contacts (format CSV natif) vers le format
de campagne `email,prenom,nom,entreprise`.

## Format d'export Google Contacts

L'export Google Contacts produit un CSV avec des colonnes spécifiques :
- `First Name`, `Last Name` → prénom, nom
- `E-mail 1 - Value` → email principal
- `Organization Name` → entreprise
- `Organization Title`, `Organization Department` → ignorés
- `Phone X - Value` → téléphones (ignorés pour la campagne email)
- `Labels` → groupes Google (ex: `* myContacts`, `* starred`)
- `Photo` → URL de la photo de profil

## Script de conversion

```python
import csv

INPUT = "contacts.csv"       # Export Google Contacts
OUTPUT = "prospects.csv"     # Format campagne

contacts = []

with open(INPUT, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        email = (row.get("E-mail 1 - Value") or "").strip()
        if not email:
            continue

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

print(f"{len(contacts)} entrées avec email → {len(unique)} uniques")
```

## Particularités

- **Google CSV utilise des guillemets** pour les champs contenant des sauts
  de ligne (adresses postales). `csv.DictReader` les gère nativement.
- **Contacts sans email ignorés** (beaucoup de contacts téléphoniques).
- **Déduplication par email** (minuscule) — Google peut avoir des doublons.
- **Contacts email-seulement** : si le contact n'a qu'un email sans nom,
  Google met parfois l'email dans le champ `First Name`. Le script le
  conserve tel quel.

## Alternative : Google People API

Pour une synchronisation automatique sans export manuel, utiliser
l'API Google People avec OAuth 2.0. Le script `sync-google-contacts.py`
(à la racine du projet) implémente cette approche avec :
- `google-auth-oauthlib` pour l'auth OAuth
- `google-api-python-client` pour l'API People
- Token pickle pour éviter la réauthentification

Prérequis : projet Google Cloud avec People API activée + credentials OAuth
Desktop.
