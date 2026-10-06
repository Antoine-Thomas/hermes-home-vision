# Export CSV vers Brevo (import de contacts)

## Format d'import attendu

- En-tete : `EMAIL` en MAJUSCULES, puis `FIRSTNAME,LASTNAME,COMPANY` (colonnes Brevo
  standard ; toute colonne supplementaire devient un attribut custom, ex.
  `SOURCE,CONSENT_DATE` — l'attribut doit exister cote Brevo sinon l'import le cree).
- Encodeage : **UTF-8 sans BOM**, separateur virgule, fins de ligne **LF**.
- Une adresse par ligne, une seule adresse par champ, aucune ligne vide.
- Plan Free : 300 emails/jour. 0-300 -> 1 jour, 301-600 -> 2 jours, 601-900 -> 3 jours,
  >900 -> plan payant.

## Separation consentement (regle non negociable)

Toujours produire des fichiers distincts et jamais melanges :

- `contacts_brevo_CONFIRMES.csv` (EMAIL,FIRSTNAME,LASTNAME,COMPANY,SOURCE,CONSENT_DATE)
  = consentement explicite **documente** (colonne opt-in, date, preuve). Si aucun
  fichier source ne contient de champ de consentement, le fichier reste vide
  (en-tete seul) — un contact vu dans une campagne passee sans champ opt-in n'est
  PAS confirme.
- `contacts_brevo_A_VERIFIER.csv` (EMAIL,FIRSTNAME,LASTNAME,COMPANY,SOURCE)
  = contacts decouverts (crawl, API publiques, export) sans consentement.
- `contacts_brevo_TEMPLATE.csv` = 3 lignes d'exemple si CONFIRMES est vide.
- Dedoublonnage casse-insensible **dans** chaque fichier et **entre** fichiers
  (priorite CONFIRMES). Croiser aussi avec les blacklists/opt-out existants
  (`blacklist.json`, tracking `stop`/`bounced`/`negative`) avant d'ecrire.

## Filtrage des adresses

Rejeter : syntaxe invalide (regex stricte, un seul `@`), domaines jetables
(mailinator, yopmail, guerrillamail, 10minutemail, jetable.org...), domaines
reserves (`example.com/org/net`, `test.com`, `invalid`, `localhost`), domaines
parking (`domainmarket.com`, `wixpress.com`, `sentry.io`), locals techniques
(`noreply`, `postmaster`, `abuse`, `mailer-daemon`, `test`).

## Validation a passer avant livraison

Verifier en binaire : pas de BOM (`\xef\xbb\xbf`), pas de `\r`, en-tete exact,
zero ligne vide, zero doublon, un seul `@` par ligne. Afficher un echantillon
anonymise (5 lignes, email tronque `ab***@gm***.com`) — jamais d'adresse complete
ni dans le chat ni dans les logs.

## Pieges Windows/MSYS rencontres

- Ecrire les CSV en Python avec `newline=""` + `lineterminator="\n"` : sinon CRLF
  et fichier rejete par Brevo.
- Le stdout de Python redirige sous Windows est ouvert en mode texte : `print("\n".join(x)) > fichier`
  ecrit des `\r\n`. Lire ces listes en bash avec `tr -d '\r'` avant de les passer a
  `gh api` ou a un chemin de fichier, sinon les appels echouent silencieusement
  (fichiers de sortie vides, 1 seule entree parse).
- Les tool calls natifs (python, gh, git) ne traduisent pas les chemins MSYS :
  passer `C:/Users/...` et non `/c/Users/...` a Python.
- Un scan recursif de `%APPDATA%` complet depasse le timeout : limiter aux dossiers
  utiles (mail, Documents, Desktop, Downloads, OneDrive, Projets, dossiers data
  applicatifs) et exclure installs/tools/models/caches.

## Sources a ecarter ou a traiter a part

- Exports LinkedIn scrapes (ToS + RGPD), crawls SIRENE/sites web, listes
  personnelles (amis) reutilisees : a classer hors du fichier d'envoi, avec alerte
  RGPD et proposition de re-consentement (double opt-in) plutot qu'un import direct.
- Emails publics d'API (GitHub `users/<login>`, champ `email`) = adresses
  professionnelles publiques : categorie "a verifier", jamais "confirme".
