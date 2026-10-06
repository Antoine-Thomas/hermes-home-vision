# Reengagement Brevo (double opt-in) — demande de consentement avant tout import

Quand Brevo refuse l'import faute d'opt-in certifiable et que les contacts sont des personnes
deja sollicitees (portfolio, candidatures, crawl) sans consentement marketing : un SEUL mail de
demande de consentement, depuis le domaine propre, avec un seul bouton vers le formulaire Brevo ;
c'est le formulaire (double opt-in) qui horodate l'accord, et lui seul alimente ensuite la liste
importable.

## Canal d'envoi

- Expediteur `dev@searching-murphy.com`, SMTP o2switch `mail.searching-murphy.com:465` (SSL).
- Identifiants dans `%LOCALAPPDATA%\hermes\.env` : `REENG_SMTP_HOST`, `REENG_SMTP_PORT`,
  `REENG_SMTP_USER`, `REENG_SMTP_PASSWORD`. Sans `REENG_SMTP_HOST` le script replie sur Gmail
  `EMAIL_*` — mauvaise boite pour ce flux, donc verifier la cle avant d'envoyer.
- Un mail individuel par contact, jamais de CC/BCC. Un seul lien d'action (le bouton du
  formulaire). Desabonnement par reponse « stop » (lien `mailto:` + en-tete `List-Unsubscribe`),
  puisque l'envoi ne passe pas par Brevo.
- Objet et corps : `Un nouveau projet — tu veux suivre ?`, tutoiement, balise
  `{{ PRENOM | fallback: '' }}` resolue par le script (prenom vide -> `Salut,`).

## Utiliser le script existant, ne pas en reecrire un

`send_reengagement_gmail.py` (dossier `reengagement_gmail/`) fusionne et dedoublonne les CSV de
contacts, valide les emails, extrait l'URL du formulaire depuis le template, teste la connexion
SMTP et journalise chaque tentative. Modes exclusifs, un obligatoire :

- `--dry-run` — listes, dedoublonnage, lien du formulaire, reglages SMTP prevus. Aucune connexion.
- `--smtp-check` — TLS 465 + authentification, 0 mail.
- `--test-email <adresse>` — UN seul test, objet prefixe `[TEST]`.
- `--send [--limit N] [--start-at N] [--yes]` — envoi reel, confirmation interactive sans
  `--yes`. Reprise : les contacts deja `sent` dans le journal sont sautes. Pause par defaut 8 s
  (+ jitter), ~1 h pour ~390 contacts.
- **Noms d'options reels — ne pas les confondre.** Le delai se regle par `--pause 8` : il n'y a
  PAS de `--rate`, et PAS d'option `--exclude-*` a passer. L'exclusion d'opt-out est INTEGREE au
  script : `load_exclusions()` charge `optout.csv` (obligatoire — absent = refus de demarrer, exit 2,
  aucune connexion SMTP), puis `exclusions_manuelles.csv` et tous les `bounce_*.csv` du dossier de
  campagne, et filtre apres fusion/dedoublonnage. Ne pas se contenter de la presence des fichiers :
  mesurer l'exclusion REELLE au `--dry-run` (decompte par fichier, total d'exclusions uniques,
  contacts retires), car une adresse exclue absente des listes lues par le script ne retire personne
  — un fichier d'exclusion dont aucune adresse ne figure dans les contacts vaut 0 exclusion, pas
  « applique ». En shell non interactif, `--send` sans `--yes` sort en 3 sans envoyer : proposer la
  commande avec `--yes`.

```bash
cd <campaign_dir>/reengagement_gmail
python send_reengagement_gmail.py --test-email <adresse perso de l'utilisateur>
```

## Repondre a « est-ce qu'ils ont ete envoyes ? »

Lire le journal `reengagement_sent.json` et compter `results[].mode` : `test` = tests a soi-meme,
`mass` = envois reels a la liste. Le bloc `summary` ne decrit que la derniere execution — ne pas
le citer comme le total.

## Blocklister une adresse dans Brevo

Le CSV local ne protege que le script d'envoi ; Brevo protege tout le reste. Une adresse opt-out doit
vivre des deux cotes.

- **Fiche unique** : `CRM > Contacts` > ouvrir le contact > section **Canaux** > **Email** >
  **Blockliste**. Verifier que le statut passe de « Inscrit » a « Blockliste ».
- **Plusieurs contacts** : `CRM > Contacts` > cocher les contacts (ou case d'en-tete puis
  « Selectionner tous les contacts ») > **Blocklist** > saisir le nombre selectionne pour confirmer.
  Cette voie ne blockliste que les campagnes EMAIL.
- **En masse depuis un fichier** : `CRM > Contacts` > **Importer des contacts** > charger un fichier ne
  contenant QUE la colonne email > l'associer a `EMAIL` > cocher **Ajouter les contacts email importes
  a la blocklist**. Un fichier et un import separes par canal si SMS/WhatsApp sont concernes.
- **API** (reproductible, scriptable) : `POST https://api.brevo.com/v3/contacts` avec l'en-tete
  `api-key` et `{"email": "...", "emailBlacklisted": true, "updateEnabled": true}` — sans
  `updateEnabled`, une adresse deja existante renvoie une erreur au lieu d'etre mise a jour.
- **Deux pieges** : le deblocage/reinscription de masse est impossible cote Brevo — et contraire a la
  loi pour un opt-out explicite, donc ne jamais reinscrire ; un import de campagne ne doit jamais
  melanger le fichier d'exclusion et la liste cible, l'import ecrasant le statut du contact.
- Brevo alimente aussi sa propre blocklist automatiquement (desinscriptions, plaintes spam, hard
  bounces) : la consulter pour recouper, pas pour remplacer le fichier local.

## Pieges

- Un mail de demande de consentement n'est pas un mail produit : pas de balise de desabonnement
  d'ESP, aucune relance des non-repondants (le mail promet un seul envoi et l'absence de suite).
- Ne jamais importer la liste dans Brevo avant le consentement : le formulaire est le seul point
  d'entree, l'import ne contient que les inscrits.
- Le mail part depuis le domaine, pas depuis Gmail : ne pas reutiliser l'expediteur de campagne
  Gmail pour ce flux.
