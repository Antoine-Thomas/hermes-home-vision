---
name: imap-mailbox-labeling
description: "Use when bulk-labeling a mailbox into IMAP labels."
version: 1.0.0
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [email, imap, gmail, labels, triage, x-gm-labels]
---

# IMAP Mailbox Labeling

Classer une boîte entière dans des étiquettes DÉJÀ existantes, sans API OAuth et
sans rien détruire : inventaire en lecture seule, mapping thème→label, test sur
1 mail, puis application par lots avec vérification avant/après.

## When to Use

Déclencheurs (FR/EN) : « classe les mails par thème dans les labels existants »,
« étiquette cette boîte », « range ma boîte de réception par sujet », « bulk-label
my mailbox », « classify my inbox into existing Gmail labels ».

- « Classe les mails par thème dans les labels existants »
- « Étiquette cette boîte », « range ma boîte de réception par sujet »
- Toute opération de masse sur des labels Gmail/IMAP (une boîte de 20k+ mails se
traite en quelques minutes avec cette méthode)

Hors périmètre : triage thread par thread avec brouillons de réponse (autre
métier), envoi de campagnes email.

## Règles toujours actives (contrat utilisateur)

Ces règles priment sur toute envie de « finir le travail » : la livraison de
l'étape N est l'attente explicite du go pour N+1.

1. **Étape 1 en LECTURE SEULE** : inventaire des labels existants, volumétrie,
   thèmes détectés, proposition de mapping thème→label. Puis STOP.
2. **Ne jamais créer de label** sans accord explicite. Vérifier d'abord que la
   cible existe côté IMAP : un label absent de `LIST` n'est pas écrivable.
3. **Ne jamais COPY**, ne jamais retirer `\Inbox` (archivage), ne jamais écrire
   `\Seen` sans demande explicite. Seul `+X-GM-LABELS` est appliqué.
4. **Ne pas toucher aux labels déjà posés** : on ajoute, on ne remplace pas.
5. **Test obligatoire avant le lot** : montrer le plan définitif (volume par
   mapping) PUIS un test réel sur 1 mail non critique avec avant/après. Attendre
   le go.
6. **Signaler les écarts** entre le volume annoncé et le volume du plan définitif,
   et la part non classable (tri manuel). Jamais de lissage.

## Procédure

### 1. Vérifier l'accès

Mot de passe d'application IMAP dans le `.env` du profil (`EMAIL_ADDRESS`,
`EMAIL_PASSWORD`, `EMAIL_IMAP_HOST`). Ne jamais afficher la valeur : le script la
lit lui-même. `X-GM-EXT-1` doit figurer dans `M.capabilities`.

### 2. Inventaire (lecture seule)

```bash
python scripts/gmail_imap_label_inventory.py [chemin/.env] [sortie.json]
```

Donne : dossiers visibles en IMAP, étiquettes réellement portées avec comptages
(via `X-GM-LABELS` sur `[Gmail]/Tous les messages`), sondes de catégories, top
expéditeurs, volumétrie par année, comptage des messages sans label utilisateur.

- `LIST` = seules les cibles écrivables ; le balayage `X-GM-LABELS` révèle en plus
  les étiquettes absentes de `LIST`.
- « Non classé » = message dont les étiquettes ne contiennent aucun label
  utilisateur (hors `\Inbox`, `\Seen`, `\Important`, `\Starred`, `\Sent`,
  `\Draft`, `\Muted`, `[Imap]/*`).
- Les catégories Gmail (Promotions, Réseaux sociaux, Forums, Notifications) sont
  trouvables par recherche mais ne sont PAS des dossiers IMAP : ni COPY ni STORE
  ne peuvent y placer un mail. À annoncer avant d'en faire une cible.

### 3. Thèmes et mapping

Règles par domaine puis par objet, ordre de priorité explicite, en gardant la
raison de chaque affectation (domaine X / objet Y) pour pouvoir auditer le plan.

- Motifs trop larges interdits : une règle sur le local-part `hello` capture
  `hello@bing.com`, `hello@creativemarket.com`, `hello@ollama.com` et gonfle un
  thème métier. Viser le domaine complet (`hellowork.com`, `indeed.com`).
- Le thème le plus gros est souvent l'auto-envoi (expéditeur = le compte lui-même :
  alertes de site, stats, mails de test). L'isoler et le proposer à part, ne pas
  le fondre dans un thème métier.
- Verrouiller le plan par UID : comptage par thème, unicité des UID, et contrôle
  « aucun mail cible ne porte déjà un label utilisateur ».

### 4. Test sur 1 mail, puis go

Mail test = un des mails mappables, ancien, déjà lu, sans label utilisateur, non
critique. Montrer : étiquette ajoutée, étiquettes d'origine intactes, `\Inbox`
toujours présent, total de la boîte inchangé, comptage du label avant/après.

### 5. Application par lots

```bash
python scripts/gmail_imap_label_apply.py plan.json "TECH=Professionnel;ADMIN=plus important" --confirm
```

```python
M.select('"[Gmail]/Tous les messages"', readonly=False)
M.uid("store", ",".join(chunk_250).encode(), "+X-GM-LABELS", '("%s")' % raw_label)
```

- `+X-GM-LABELS` est additif et atomique : pas de doublon, pas d'autre étiquette
  modifiée. C'est la voie à préférer à COPY.
- **Sans le `+`, `X-GM-LABELS` REMPLACE l'ensemble des étiquettes** et détruit
  l'existant. Toujours préfixer par `+`.
- Le UID n'est valide que dans le dossier sélectionné : se placer sur
  `[Gmail]/Tous les messages` avant le STORE.
- Nom de label non-ASCII = UTF-7 modifié, comme les noms de dossier : `Reçus` →
  `Re&AOc-us`, `candidatures réponses` → `candidatures r&AOk-ponses`. Le script
  d'application encode tout seul ; ne jamais encoder à la main.
- 250 UID par commande, un mapping à la fois, ~0,2 s entre commandes.

### 6. Vérification (à exécuter et à montrer)

- Aucune perte/duplication : `SELECT` All Mail → EXISTS identique avant/après.
- Comptage par label : `SELECT "<nom brut du label>"` → EXISTS après = avant +
  volume attendu du mapping.
- Relecture du message : `UID FETCH <uid> (UID FLAGS X-GM-LABELS)`.
- Rapport : volume par mapping, échantillon de 5 mails par label, 0 suppression,
  liste des mails ambigus laissés pour tri manuel.

## Pièges

- **UID vs numéro de séquence** : un `UID FETCH` qui ne demande pas `UID` renvoie
  le n° de séquence en premier champ (`b'381 (X-GM-LABELS ("\\Inbox"))'`).
  Indexer là-dessus produit des identifiants invalides, et le `UID STORE` lancé
  dessus répond `OK` SANS rien changer (aucune réponse FETCH, `data == [None]`) :
  no-op silencieux. Toujours demander `UID` dans les items et extraire
  `re.search(rb"UID (\d+)", meta)` ; contrôler un identifiant par
  `UID SEARCH UID <n>` (`b''` = inexistant) avant de s'en servir.
- **Un `OK` n'est pas une preuve** : relire le message cible (labels + flags)
  avant d'annoncer un classement. `OK` + `[None]` = cible inexistante.
- **SEARCH non-ASCII** lève `'ascii' codec can't encode character` : imaplib encode
  en ascii. Compter les labels depuis le balayage `X-GM-LABELS` au lieu de
  chercher par nom accentué.
- **Parsing des réponses FETCH** : un item est soit un tuple `(méta, littéral)`,
  soit des bytes. Accumuler les méta ; extraire `X-GM-LABELS (...)` par comptage de
  parenthèses équilibrées (les valeurs peuvent contenir guillemets et `\`).
- **`BODY.PEEK` obligatoire** en lecture : sans PEEK, Gmail marque lu (et le
  rapport « rien marqué lu » devient faux).
- **`[Imap]/Drafts`, `[Imap]/Sent`, `[Imap]/Trash`** apparaissent dans
  `X-GM-LABELS` (étiquettes miroir d'un client externe) : ce ne sont pas des
  thèmes, ne pas les cibler.

## Fichiers joints

- `references/gmail-imap-quirks.md` — encodage UTF-7 des labels, catégories non
  écrivables, espaces UID par dossier, sondes `X-GM-RAW`, snippets de parsing.
- `scripts/gmail_imap_label_inventory.py` — inventaire complet lecture seule.
- `scripts/gmail_imap_label_apply.py` — application par lots avec garde-fous et
  vérification avant/après.

## Notes

Recouvre partiellement les références Gmail/IMAP d'`email-suite` (user-owned, donc
non modifiable par la curation) : si les deux divergent, c'est ce skill qui porte
la procédure de classement de masse.
