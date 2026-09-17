# Contacts Prospection — Workflow complet

## Vue d'ensemble

Pipeline de nettoyage → enrichissement → segmentation → prospection pour
une base de contacts (Google CSV export, CSV générique, ou autre source).

## Étape 1 : Filtrer les contacts (CSV → contacts propres)

Utiliser le script `scripts/filtrer-contacts.py` qui applique :
- **Domaines bloqués** : facebookmail.com, meetic.com, lindenlab.com, skype.com,
  microsoft.com, m.facebook.com, lists.*, newsletter.*, etc.
- **Mots-clés interdits** : no-reply, noreply, notification, service, support,
  jobs@, info@, newsletter, contact@, hello@, admin@, webmaster@
- **Mots non-nominatifs** dans la partie locale : productions, project, info,
  contact, net, com, org, la, le, de, of, etc.
- **Caractères bizarres** : ^, °, ¨
- **Gibberish** : chaînes >25 car. sans séparateur, ratio voyelles < 15%
- **Pas de nom identifiable** : email sur domaine public sans prénom+nom ni
  structure prenom.nom dans la partie locale

### Google CSV export (contacts.google.com)

Colonnes à mapper : `E-mail 1 - Value` → email, `First Name` → prénom,
`Last Name` → nom, `Organization Name` → entreprise.

### Règles de conservation

- Garder si : prenom ET/OU nom explicite (pas une copie de l'email)
- Garder si : email a structure `prenom.nom` ou `prenom_nom`
- Garder si : domaine professionnel (pas gmail/hotmail/yahoo/etc.)
- Supprimer si : aucun nom + domaine public + pas de structure nom dans l'email

### Script

```bash
python filtrer-contacts.py
# → contacts-gardes.csv + contacts-supprimes.csv
```

## Étape 2 : Enrichir avec Hunter.io

### Setup API

```bash
# Créer un compte gratuit sur https://hunter.io
# Récupérer la clé API dans Dashboard → API
export HUNTER_API_KEY="votre_clé"
```

### Vérification des emails

Le plan Free Hunter permet 100 vérifications/mois et 25 recherches/mois.
Prioriser la vérification sur les segments A+B (contacts à fort potentiel).

Utiliser `scripts/enrichir-contacts.py` qui :
- Vérifie la délivrabilité de chaque email (endpoint `email-verifier`)
- Pour les contacts avec entreprise connue, cherche un email pro
  (endpoint `email-finder` avec first_name + last_name + domain)
- Ajoute les colonnes : `Email_Pro`, `Source_Email`, `Score_Email_Pro`,
  `Verification_Statut`, `Verification_Score`

```bash
python enrichir-contacts.py
# → contacts-enrichis.csv
```

### Interprétation des résultats

| Statut | Action |
|--------|--------|
| `valid` (score ≥ 80) | ✅ Prêt pour campagne |
| `accept_all` | ⚠️ Domaine qui accepte tout — tester avant envoi massif |
| `invalid` (score 0) | ❌ Supprimer de la liste |
| `unknown` | 🔍 Vérifier manuellement |

## Étape 3 : Segmenter (A/B/C)

Utiliser le scoring dans `scripts/segmenter-contacts.py` :

- **Segment A** (score ≥ 40) : Domaine pro, entreprise connue, poste identifié,
  structure prenom.nom + nom complet. → Fort potentiel, approche directe.
- **Segment B** (score 20-39) : Email prenom.nom sur domaine public,
  nom explicite mais pas d'entreprise. → Potentiel moyen, approche réseau.
- **Segment C** (score < 20) : Pas de nom identifiable, domaine public,
  pas d'entreprise. → Newsletter large uniquement.

Critères de scoring :
- Domaine pro : +30
- Entreprise : +25
- Poste/titre : +20
- Structure prenom.nom dans l'email : +15
- Prénom + nom explicites : +15
- Prénom = copie de l'email : -10

## Étape 4 : Générer les emails d'approche

Pour chaque segment, adapter le ton et le contenu :

- **Segment A** : Ton professionnel, direct. Mentionner le design défensif,
  proposer un café ou un échange de compétences. Email personnalisé avec
  référence à l'entreprise du destinataire.
- **Segment B** : Ton chaleureux, local. Mentionner Caen, proposer un échange
  informel. Templates semi-personnalisables.
- **Segment C** : Ton léger, contenu uniquement. Newsletter avec lien de
  désabonnement. Pas de vente directe.

### Structure type d'un email d'approche (Segment A)

```
Objet : [Hook pertinent] — [contexte local] ?

Bonjour [équipe/Prénom],

[1 phrase d'accroche : qui je suis, lien avec le destinataire]

[1-2 phrases sur le design défensif / sentinelle IA — l'USP]

[1 phrase sur ce que je cherche : échange, collaboration, café]

[Signature avec site + téléphone]
```

### Règles

- Toujours mentionner le design défensif et l'IA auto-réparatrice
- Proposer un café ou un appel — jamais de vente directe au 1er contact
- Inclure le site web et le téléphone dans la signature
- Vérifier que l'email du destinataire n'est pas une adresse DPO/RGPD
  (ex: privacy@ — risque de non-réponse)

## Pièges courants

1. **PagesJaunes/Google Maps en curl** : Ces sites sont 100% JavaScript.
   Le scraping curl ne fonctionne pas. Privilégier la vérification directe
   des sites web des entreprises (HTTP 200 + détection de localisation).

2. **Contacts inventés par les LLM** : Les subagents sans accès web réel
   peuvent générer des données fabriquées (téléphones séquentiels,
   agences hors région). TOUJOURS vérifier chaque contact par HTTP réel.

3. **Nom du contact = email** : Dans les exports Google Contacts, le champ
   "First Name" contient parfois l'email entier. Le détecter et le nettoyer.

4. **Suffixes numériques** : `juliebessard.28` → nettoyer en `juliebessard`
   avant d'extraire le nom.

5. **Ne pas faire de concaténation split** : Les noms concaténés sans
   séparateur (romainbuhan, simonbonnet) ne peuvent pas être splités de
   façon fiable par heuristique. Mieux vaut les laisser tomber que de
   produire des faux positifs (spidrman → "Spid Rman").

## Fichiers produits

| Fichier | Contenu |
|---------|---------|
| `contacts-gardes.csv` | Contacts propres après filtrage |
| `contacts-supprimes.csv` | Contacts rejetés + motif |
| `contacts-segmentes.csv` | Contacts classés A/B/C + scores |
| `contacts-enrichis.csv` | Contacts + colonnes Hunter (vérification + email pro) |
| `emails-approche-*.md` | Templates d'emails personnalisés par contact |
