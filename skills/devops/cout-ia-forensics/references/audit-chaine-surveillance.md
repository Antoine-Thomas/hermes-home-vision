# Auditer la chaine de surveillance : ou lire ce que le job a FAIT

Carte d'etat et recettes verifiees pour repondre a « qu'a fait ce job depuis 24 h ? », « combien
d'alertes Telegram sont parties ? », « ce profil a-t-il tourne ? », « pourquoi le repli a-t-il ete
saute ? ». Tout est en lecture seule. Sous Windows, racine = `%LOCALAPPDATA%\hermes`.

## Definitions de job et verdict par job

- `cron/jobs.json` (profil principal) et `profiles/<profil>/cron/jobs.json`.
- Champs qui portent le verdict : `last_run_at`, `last_status`, `failure_streak`, `last_error`,
  `last_delivery_error`, `deliver` (cible, ex. `telegram:<chat_id>`).
- **Lire aussi l'etat, pas seulement le statut** : `state: paused` / `completed` ou `enabled: false`
  = job desactive, et il garde `last_status: ok` avec des chiffres anciens. Un job au quart d'heure
  « arreter depuis une semaine » se voit a `last_run_at`, jamais a `last_status`.
- Nom du job et identifiant ne coincident pas dans la question de l'utilisateur (« veille-hebdo »
  peut etre le nom d'un job vivant dans `profiles/veille/cron/jobs.json`) : chercher l'id, puis
  verifier le profil qui l'heberge.

## Historique reel : `cron/executions.db`

SQLite, une ligne par run. Colonnes utiles : `job_id`, `source`, `status` (`completed` / `failed`),
`started_at`, `finished_at`, `error`, `delivery_outcome` (`delivered` / `suppressed` / `failed`),
`handoff_pending`.

- C'est la SEULE source qui dit si une alerte est partie : `delivered` = message remis,
  `suppressed` = etouffe par l'anti-spam du job, `failed` = livraison en echec. Le texte du fichier
  de sortie, lui, ne dit rien de la remise.
- Recette « 24 h » : lire toutes les lignes, parser `finished_at` en `datetime` **en Python**,
  filtrer sur la fenetre, puis compter `delivery_outcome` et lister les `finished_at` des
  `delivered`. Reponse type : « 90 runs, 16 livrees, 74 etouffees, 0 echec ».
- Ne pas conclure sur `sum(delivery_outcome='delivered')` fait en SQL si le filtre de temps est
  reste en SQL : voir le piege ci-dessous.

### Piege : un filtre de temps SQL sur une colonne texte matche TOUT

Les horodatages sont stockes naifs (`AAAA-MM-JJTHH:MM:SS[.ffffff]`, sans fuseau). Les comparer en SQL
(`WHERE finished_at >= ?`) a un cutoff ISO porteur de fuseau, ou a un nombre, renvoie la totalite de
la table et fabrique un faux compteur de 24 h (ecart mesure : 131 runs / 45 alertes annonces contre
90 / 16 reels). Parser chaque valeur en `datetime` puis filtrer et compter en Python.

### Ce qui n'est PAS un historique

- `cron/output/<job_id>/<AAAA-MM-JJ_HH-MM-SS>.md` : dossier ROTATIONNE (~50 fichiers, soit ~13 h
  pour un job au quart d'heure). Un fichier `Status: silent` = tick sans alerte. Utile pour le TEXTE
  des alertes recentes, jamais pour une fenetre de 24 h.
- Le fichier d'etat d'une sonde (`data/route_ia_fix/<sonde>.json`) : instantane (dernier code,
  `checked_at`, `last_alert_ts`), pas d'historique.
- `cron/ticker_heartbeat` et `cron/ticker_last_success` (epoch) : sante du planificateur seulement.
- `cron/usage_audit.jsonl` : detail par run (cout, modele) quand il faut chiffrer l'effort du job.

### Piege : une cible figee n'est pas une cible saine

Comparer les `checked_at` entre cibles d'un meme fichier d'etat. Une entree qui ne bouge plus depuis
la veille signifie que la sonde ne couvre PLUS cette cible : la liste des cibles est dans le script
du job (`COMBOS = [...]`, boucle de sondage). Le rapport ecrit « non surveille » — jamais « 0 panne »,
qui laisserait croire a une cible stable. Verifier aussi qu'un job de rafraichissement dont depend la
cible n'est pas `paused`.

## Profils, credentials, quotas

- Un profil vit sous `profiles/<nom>/` : `config.yaml`, `.env`, `cron/jobs.json`, `logs/`,
  `state.db`, parfois `auth.json`.
- **Absence de `profiles/<nom>/auth.json` = le profil partage le pool du profil principal**
  (`auth.json` a la racine). Ce n'est PAS « profil sans credential » : la preuve se lit dans les
  logs du profil (« Fallback skip: <provider>/<modele> credential pool is exhausted »).
- Sondes en lecture seule : `hermes auth list` (une ligne par entree du pool, avec la marque
  `exhausted (<code>)` le cas echeant), `hermes auth status <provider>` (`logged in`), et
  `hermes status` (modele et provider par defaut, presence de chaque cle API, PID du gateway,
  `Serves: <profils>`, nombre de jobs actifs).
- Semantique du pool (`agent/credential_pool.py` ; message de saut dans
  `agent/chat_completion_helpers.py`) : une entree n'est indisponible que si `last_status == exhausted`
  avec cooldown non expire (ou un cooldown par modele). `failure_reason: billing` seul ne bloque PAS —
  il ne fixe que la duree du cooldown au PROCHAIN echec. Un `request_count: 0` veut dire « jamais un
  appel reussi » : a rapporter meme si l'entree est visible et `hermes auth status` repond
  `logged in`. Dire les deux faits (visible / jamais reussi) au lieu de trancher « bloque ».
- Quotas OmniRoute : `provider_connections` (`test_status`, `error_code`, `last_error`,
  `rate_limited_until`, `is_active`), `quota_snapshots` (par connexion : `remaining_percentage`,
  `is_exhausted`, `next_reset_at`), `settings.autoRefreshProviderQuota`. Les `rate_limited_until`
  sont en **UTC** : convertir en local avant de dire « c'est reset ». `autoRefreshProviderQuota=false`
  explique l'absence de pourcentage journalier hors des connexions a snapshot — le dire plutot que
  d'inventer un quota.
- Lecture SQLite d'un service vivant : `sqlite3.connect(pathlib.Path(p).as_uri() + "?mode=ro", uri=True)`.
  Un chemin natif a antislashs insere tel quel apres `file:` fait echouer la connexion (et l'echec
  ressemble a une base illisible).

## Etat reel des bots Telegram d'un gateway

- `Serves: docs-writer, veille, watch` liste les profils CONFIGURES, pas les bots vivants.
- L'etat reel se lit dans `profiles/<nom>/logs/gateway.log` : une reprise reussie ecrit
  `polling confirmed healthy` ; un `Fatal telegram adapter error ... (telegram_polling_conflict)`
  suivi de `Disconnected from Telegram` et de RIEN ensuite = bot mort, a signaler comme tel (5
  retries espaces = ~200 s d'attente avant abandon) ; des `failed`/`recovered` repetes sur
  `telegram_network` dans `profiles/<nom>/logs/agent.log` = transport reseau qui bascule entre
  l'IP litterale et le hostname, pas une panne d'application.
