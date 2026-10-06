# Cout paye du repli : analyse et watchdog

Source de verite : `state.db` (table `sessions`), JAMAIS le log du routeur — le log donne des requetes, pas des montants. Lecture en `mode=ro`.

## Lire la facture reelle

- Filtre « payant » : `billing_provider in ('deepseek','openrouter')`. Les etages gratuits portent `billing_provider='omniroute'` ou `'custom'` (endpoint local declare par sa seule `base_url`), avec `estimated_cost_usd = 0` — c'est ce partage qui rend la depense attribuable.
- `ended_at` est NULL pour la plupart des sessions, **y compris anciennes** : la duree n'est pas stockee. Donner l'heure de depart + `api_call_count` comme proxy, et ecrire « duree non exploitable » plutot que d'inventer un chiffre.
- Requetes utiles : totaux et periode ; `group by model` ; `group by billing_provider` ; `group by date(started_at,'unixepoch','localtime')` ; top 10 `order by estimated_cost_usd desc` ; volumes `sum(input_tokens/output_tokens/cache_read_tokens/cache_write_tokens)`.

## Fiabilite du champ cout (a dire explicitement quand on rapporte un montant)

- `cost_status='estimated'` avec `cost_source='official_docs_snapshot'` (grille tarifaire officielle embarquee dans `agent/usage_pricing.py`) ou `'provider_models_api'` (models.dev) = **estimation au prix liste, pas une facture** ; `cost_status='unknown'` = montant speculatif.
- `actual_cost_usd` n'est pas rempli : **aucun rapprochement avec une facture**. Sans acces a la console de facturation du fournisseur, la comparaison au releve reel est **inconnue** — le dire tel quel, ne jamais presenter un estime comme « facture ».
- Les jetons de **cache sont tarifes** : le bareme porte `cache_read_cost_per_million` / `cache_write_cost_per_million`, et `prompt_tokens = input + cache_read + cache_write`. Sur un usage agent intensif, `cache_read_tokens` domine le volume d'un ordre de grandeur (contexte relu a chaque appel) : c'est le premier poste a regarder.
- Le module previent lui-meme qu'un proxy/relais servant le meme id de modele peut facturer autrement : une estimation « prix liste » n'engage pas le montant debite.

## Attribuer la part « repli » (croisement avec les logs)

- Les logs tournent vite : dater chaque `agent.log*` (`head -1` / `tail -1`) AVANT de conclure, et traiter tout ce qui precede la fenetre comme **inconnu**.
- Sequence de provider par session : les lignes `agent.conversation_loop: API call #N: model=… provider=… in=… out=…` se regroupent par session et revelent l'oscillation gratuit <-> payant DANS une meme session (sessions « mixtes » : majorite d'appels payants, quelques tentatives gratuites).
- Erreurs fournisseur reelles : `ERROR … Streaming failed before delivery: <modele>: provider — … [503]: ResourceExhausted …` (worker local sature), `[504]`, `[502]`, `[403]`. **Un `grep 503` nu ne vaut rien** : il matche aussi les compteurs de jetons (`total=166503`) — apparier sur `ERROR`.
- Conclure sur ce qui est mesure (« X % des appels de la fenetre sur le lien paye »), pas sur une extrapolation si la fenetre ne couvre pas la periode.

## Conception d'un watchdog de cout (cron `no_agent`)

Regles validees ; a reprendre pour tout compteur cumule surveille :

- Criterer sur l'**increment du cumul** (`sum(estimated_cost_usd)` compare au dernier scan), jamais sur `started_at > dernier_scan` : une bascule payante dans une session DEJA ouverte (demarree avant la borne) echappe definitivement a ce critere.
- **Un seul appel de mesure par profil et par scan** (deux lectures successives peuvent se contredire et fausser le delta).
- `delta < 0` (cumul qui baisse : sessions purgees) = reset du repere, **journalise, sans alerte**. Profil sans repere = repere pose explicitement et journalise — jamais de saut muet.
- Premier scan (etat absent) = balayage des 24 h avec un message DEDIE (« historique 24 h : X $ (modele …) ») ; scans suivants = « hausse depuis le dernier scan ». Un point de depart silencieux rend le watchdog aveugle a tout ce qui precede.
- Anti-spam 1/h conserve, MAIS l'increment supprime doit etre **reporte sur l'alerte suivante** (sinon il disparait en silence), et pas de « retour a la normale » tant qu'un increment reste a signaler.
- Etat JSON : repere par profil, journal borne (20 dernieres entrees), dernier scan. Message : profils, modeles, montants — aucun jeton, aucune cle.
- Deployer puis **relancer le job et citer sa sortie reelle** : un correctif de watchdog n'est valide que par un run de production (le run manuel du script ne delivre rien ; c'est le job qui poste).

## Tester un watchdog sans toucher a la production

- Copie du script avec la CONSTANTE de chemin remplacee par un dossier de test (`pathlib.Path(r"<prod>")` -> `pathlib.Path(r"<testdir>")`), base SQLite **synthetique** (ne pas copier un `state.db` de plusieurs centaines de Mo), fichier d'etat dedie.
- Prouver la non-interference par SHA256 des fichiers de production avant/apres. Nuance a rapporter : le `state.db` reel bouge de lui-meme pendant une session en cours — le dire, ne pas le presenter comme un effet du test.
- Cas a couvrir : balayage initial ; bascule EN COURS de session (cout modifie sur une ligne dont `started_at` reste ANTERIEUR au dernier scan) ; anti-spam (silence, puis alerte apres recul de `last_alert_ts`) ; retour a la normale puis silence ; delta negatif ; profil sans repere ; anti-fuite (0 jeton dans sorties et etats).

## Reglages qui pesent sur la facture (a proposer, jamais appliquer d'office)

Ordre des replis (les combos gratuits morts font basculer sur le paye), `agent.api_max_retries` (chaque tentative renvoie le contexte), `compression.threshold` (un contexte plus court = moins de `cache_read`), duree des sessions (300 a 2 000 appels dans une meme session), `prompt_caching.cache_ttl`. Chaque levier se propose avec son risque : moins de replis = plus d'echecs visibles ; compression plus agressive = perte de detail plus tot et un appel de resume de plus.
