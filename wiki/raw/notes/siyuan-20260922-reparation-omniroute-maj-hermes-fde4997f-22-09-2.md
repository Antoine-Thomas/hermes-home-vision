---
source_url: siyuan://20260921223640-38gbwri/20260922171319-sjwqa3t
ingested: 2026-09-22
sha256: 6d1ca66160ca979e1bad67830a1e46dcc3f8121ae0bc650cfe3b2878afe28903
---

# Réparation OmniRoute + MAJ Hermes fde4997f - 22-09-2026

---
title: Réparation OmniRoute + MAJ Hermes fde4997f - 22-09-2026
date: 2026-09-22T17:13:19+02:00
lastmod: 2026-09-22T17:20:26+02:00
---

# Réparation OmniRoute + MAJ Hermes fde4997f - 22-09-2026

# Réparation OmniRoute + MAJ Hermes fde4997f

Intervention du 22-09-2026, ~16:30-17:20 (Paris). Point de départ : diagnostic fourni (proxy NIM down, providers morts, providers à désactiver) — **plusieurs points de ce diagnostic se sont révélés périmés ou inexacts**. Détail ci-dessous, avec les preuves brutes.

## Partie 1 — OmniRoute

### Le diagnostic de départ était périmé

|Symptôme annoncé|Réalité mesurée|Preuve|
| ----------------------------------------------------| ---------------------------------------------------------------------------------------------------------------------------------| ------------------------------------------------------------------------------------|
|openai : proxy 127.0.0.1:20200 down (ECONNREFUSED)|**Le proxy était UP** depuis 16:22:45 (PID 10560)|`curl :20200/v1/models`​ → HTTP 200 en 0,125 s ; `netstat` LISTENING PID 10560|
|cloudflare-ai : Account ID manquant|Vrai **avant** le redémarrage, pas après. Les 2 connexions passaient `POST /api/providers/<id>/test`​ → `{"valid":true}`|43 lignes « Account ID » toutes entre 13:34:36 et 14:16:46Z ; 0 après 14:23:27Z|
|felo-web : HTTP 400/429|Aucune connexion `felo-web`​ dans `/api/providers` — c'est un provider ProxyEgress, sans connexion à désactiver|`GET /api/providers` → 13 connexions, aucune felo|
|opencode : clé manquante / tier limité|Vrai **au niveau modèle** : `opencode/claude-fable-5`​ → 402 « requires an opencode API key » ; `oc/nemotron-3-ultra-free` → 403 « free tier can only be used from within OpenCode »|2 appels réels|
|gemini : fonctionne|Faux à ce moment-là : 429 « All credentials for model gemini-3-flash-preview are cooling down », `credentials_cooling: 1` (=pool d'1 seul compte)|appels directs répétés|

Toutes les lignes d'erreur citées (ECONNREFUSED, Account ID, felo, opencode, 402/403/429) sont datées **13:34 → 14:16Z**, c'est-à-dire **avant** le redémarrage de la pile à 16:22-16:23 (heure locale). Elles provenaient de la passe de sonde des candidats, pas du trafic d'eco.

### Le vrai tueur du daemon

```
2026-09-22T13:34:36.763Z app | [ERROR] [502]: Cloudflare Workers AI requires an Account ID...
2026-09-22T13:34:36.768Z app | ⨯ unhandledRejection: Cloudflare Workers AI requires an Account ID...
```

Un appel à un modèle cloudflare-ai déclenche un `unhandledRejection`​ non géré côté OmniRoute → mort du daemon (le log s'arrête sans ligne `Shutdown`), donc eco et nvidia-stack tombent avec lui. C'est la seule panne « réelle » de ce lot.

### Le 503 « 16/16 » n'est pas le proxy

Mesure décisive, même requête, même clé, même minute :

- via le proxy local :20200 → **503** « ResourceExhausted: Worker local total request limit reached (16/16) »
- en direct amont `integrate.api.nvidia.com`​ → **503 aussi** (4 échecs sur 6)
- le même proxy, même modèle → **200 en 0,94 s** avec content `pong`

Les deux chemins échouent pareillement : c'est une **limite de débit côté NVIDIA (par clé/modèle)** , intermittente, pas le proxy local. Le code du proxy (`data/nvidia/nvidia-nim-proxy.py`​, 203 lignes, `ThreadingHTTPServer`) n'impose aucun plafond. Le « double processus » (PID 13252 → 10560) est une chaîne cmd → python → python, un seul port tenu.

**Attention** : mes propres sondes ont fabriqué une partie des 503. Les grappes `16/16`​ dans `app.log` (14:32 et 14:34Z) correspondent exactement à mes appels de contrôle. Ne pas conclure d'une rafale 503 sur la santé d'un combo.

### Actions réalisées

1. **Proxy NIM** : aucune relance nécessaire (déjà up). Les deux tâches de relance (`Hermes_NVIDIA_NIM_Proxy`​, `OmniRoute-AutoLaunch`​, `OmniRoute-Watchdog`) sont saines.
2. **Combo eco** : **laissé intact à 3 membres** (option A de la consigne). Les retirer aurait réduit eco à la seule cible gemini — elle-même en cooldown 429 — c'est-à-dire au scénario « combo à 1 cible → tout part sur le payant ». Membres vérifiés : `gemini/gemini-3-flash-preview`​, `openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`​, `openai/nvidia/nemotron-3.5-lightning-30b-a3b`.
3. **Providers désactivés** (PATCH `isActive:false`, sans suppression, donc réversible) :

|Connexion|id|Motif|Preuve|
| ------------------------------| --------------------------------------| ----------------------------| -------------------------------|
|Compte OpenCode 1 (opencode)|634c3ee7-0ffe-46a4-a764-a2083f5b4215|402 crédits épuisés|`testStatus: credits_…`​ après PATCH ; `opencode/claude-fable-5` → 402|
|cloudflare-ai main-2|462ed5aa-1901-4013-befa-7754a693d781|502 + `unhandledRejection` qui tue le daemon|ligne 13:34:36 ci-dessus|
|cloudflare-ai main|487d9090-1f94-4bc5-84f3-8243f49ce3c5|idem|idem|

Relecture après écriture : **8 → 5 connexions actives**, exactement ces 3 changées (backup : `hermes/cache/scratch/providers_avant_desactivation_20260922_163818.json`​).  
Aucun combo ne référence de modèle cloudflare-ai ou opencode sur le chemin d'eco (vérifié sur les 5 combos).  
Réactivation : `PATCH /api/providers/<id>`​ avec `{"isActive": true}`​ + `Authorization: Bearer $OMNIROUTE_API_KEY`.

Note : `felo-web`​ n'existe pas comme connexion → rien à désactiver. Sa correction réelle serait de retirer les candidats morts de `CANDIDATES`​ dans `scripts/probe_omniroute.py` (non fait ici, hors périmètre).

### Tests finaux

|Test|Résultat|
| -----------------------------------------| ---------------------------------------------------------------------------|
|eco (3 essais espacés, fenêtre calme)|**HTTP 200** × 3 — 2,73 / 0,76 / 1,18 s, servi par `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`|
|nvidia-stack|**HTTP 200** (17,8-17,9 s), servi par `nvidia/nemotron-3-super-120b-a12b`|
|gemini en direct|429 cooldown (pool = 1 compte) — limitation structurelle connue|
|eco en fin d'intervention|503 sur sa cible 2 (16/16) alors que **cette même cible répond 200 en 0,91 s en direct** → limite transitoire, pas de casse|

## Partie 2 — Mise à jour Hermes

### Avant

- `hermes --version`​ : **v0.21.4 (2026.9.21) · upstream c7c2df1a**, install method `git`, arbre git propre.
- `updates.pre_update_backup: false` → l'updater ne sauvegarde rien par défaut.
- `gateway.multiplex_profiles: true`​ sur les 3 profils, alors que la config documentée le veut à `false`​ (**le défaut a basculé en 0.21.x**) → repinné à `false` (default, veille, watch).
- **Le HEAD attendu par la consigne (**​**​`e2f8a0731bf26e95b31e35d73e71e183a1045b81`​**​ **) n'existe pas** : `origin/main`​ portait `fde4997f580c3480798fdf9c7e92c0079d6e03d6`.
- `hermes profile stop`​ **n'existe pas** (sous-commandes réelles : list/use/create/delete/…). La voie correcte est `hermes gateway stop`​ / `hermes -p <profil> gateway stop`.

### Sauvegardes faites (avant toute modification)

`config.yaml`​, `.env`​ (racine + veille + watch), `config.yaml`​ des profils, `memories/`​, et les 3 `state.db`​ **via l'API sqlite** **​`backup()`​** ​ (cohérent même avec un écrivain actif) — suffixe `.bak.pre_update_20260922_164000`​. Plus le snapshot rapide de l'updater : `state-snapshots/20260922-144131-pre-update` (270 Mo).

### Le piège majeur : `--backup` archive 178 Go

`hermes update --backup`​ zippe **tout** HERMES_HOME, soit **178 Go** dont 162 Go de `data/`​ (poids SDXL, vidéo, RAG). Mesuré : 15,6 Go écrits en ~17 min alors que l'archive était encore au début de l'arborescence → plusieurs heures et plusieurs dizaines de Go. Un orphelin de **12,5 Go** (`backups/.pre-update-2026-09-22-155230.zip.22900-17076.partial`​, 15:52Z) témoigne qu'un run antérieur a subi la même chose.  
→ Run arrêté, partial supprimé (16,5 Go récupérés), relancé avec `--no-backup`​, ce qui correspond au comportement déjà configuré sur ce host (`pre_update_backup: false`).

### Arrêt contrôlé avant l'update

- Garde-fou venv (`hermes update --list-venv-holders`​) : 5 PID à libérer (2 `serve`​, 2 `gateway`​, le proxy NIM lancé depuis le venv). **Ma propre session CLI n'est pas listée** (elle est exclue).
- Tâches planifiées **suspendues** le temps du run car elles recréent un détenteur du venv : `Hermes_Gateway`​ (PT15M → 16:50), `Hermes_Gateway_HealthCheck`​ (PT5M), `Hermes_NVIDIA_NIM_Proxy` (PT15M → 16:48:48). Réactivées après.

### Résultat

|Élément|Valeur|
| -------------------------| ---------------------------------------------------------------------------------|
|HEAD avant|`c7c2df1a536d62b45fda8907bb1898981721794d`|
|HEAD après|**​`fde4997f580c3480798fdf9c7e92c0079d6e03d6`​** (= origin/main, 414 commits)|
|`hermes --version` après|**v0.21.4 (2026.9.21) · upstream fde4997f** (même numéro de version : pull de 414 commits sur la même ligne de release)|
|Test ping|`hermes -z "Réponds uniquement par: pong-after-update"`​ → **pong-after-update**|
|Config après migration|`_config_version 45`​ sur les 3 profils ; model/fallbacks intacts ; `multiplex=false` conservé|
|Rollback|**non nécessaire**|

### Point ouvert : installation des dépendances différée

Le code a été remplacé, mais l'étape « dépendances » se refuse tant qu'un processus tient `hermes.exe`​ — ici **ma propre session d'agent** :

```
⚠ Could not quarantine hermes.exe (PermissionError: another process is holding it open).
✗ Cannot continue the update: live Hermes launcher(s) could not be moved aside: hermes.exe
  The dependency install has been deferred: close the process(es) above, then run any `hermes` command to finish it automatically.
```

Contrôle réel du delta : `pyproject.toml`​ vs `venv`​ → **un seul paquet « manquant »,**  **​`ptyprocess`​**​ **, et il est exclu sur Windows** (`sys_platform != 'win32'`). Le venv est donc complet pour cette plateforme ; Hermes tourne (gateway PID 6740, test ping OK). La reprise se fera d'elle-même au prochain lancement hors session, ou immédiatement depuis un terminal ordinaire :

```
cd /d "C:\Users\searc\AppData\Local\hermes\hermes-agent"
"C:\Users\searc\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -m pip install -e ".[all]"
```

### État des services après l'intervention

|Service|Port|État|
| ----------------| -------| --------------------------------------------------------------|
|Gateway Hermes|—|running (PID 6740) ; profils default + veille + watch servis|
|Serve backend|9119|LISTENING (PID 15496)|
|OmniRoute|20128|LISTENING (PID 15640, jamais arrêté)|
|Proxy NIM|20200|LISTENING (PID 3672, relancé)|

## À surveiller / décisions laissées à l'utilisateur

1. **Orphelin de 12,5 Go** : `hermes/backups/.pre-update-2026-09-22-155230.zip.22900-17076.partial` — supprimable (archive partielle inutilisable).
2. **​`multiplex_profiles`​**​ repinné à `false`​ sur les 3 profils (conforme à la config documentée, le défaut 0.21.x est `true`). À ce stade le host gateway sert quand même les 3 profils (« served by the default multiplexer »).
3. **Limite NIM par clé** : la clé `NVIDIA_API_KEY_GEMMA4`​ sature par vagues (`16/16`​). Réelle et non réparable côté proxy. Piste : `data/nvidia/.env`​ contient 2 autres clés (`NVIDIA_API_KEY_SVD`​, `NVIDIA_API_KEY_SD`) — non testées pour du chat.
4. **Candidats morts du probe** : `cloudflare-ai/*`​, `felo/*`​, `oc/*`​, `opencode/*`​ font échouer ~11-14 cibles par passe horaire et abîment la santé perçue d'eco. Les retirer de `CANDIDATES`​ dans `scripts/probe_omniroute.py`​ (et sa copie `Projets/hermes-home-vision/scripts/`) réduirait le bruit — non fait ici.
5. **Gemini** : pool d'**1 seul compte** → `429 all 1 active accounts cooling down` à répétition. Élargir demande une seconde connexion adossée à un autre compte Google.

## Nettoyage post-update (22-09-2026, 17:20-18:05)

- Suppression de 3 partials de backup abandonnes : `.pre-update-2026-09-22-140901.zip.22740-11720.partial`​ (1,66 Go), `-153513`​ (1,82 Go), `-155230`​ (12,50 Go) = 14,9 Go. `backups/`​ passe de 16 Go a 243 Mo. Piege : ces fichiers commencent par un point, donc `Get-ChildItem "$env:LOCALAPPDATA\hermesackups\*.partial*"`​ ne les voit pas (fichiers caches) — mon premier `ls` a fait la meme erreur.
- `scripts/probe_omniroute.py`​ (+ copie `Projets/hermes-home-vision/scripts/`​) : 9 candidats morts retires (5 x `oc/*`​, 2 x `opencode/*`​, `oc/kimi-k3`​, `cloudflare-ai/*`​), liste 17 -> 8 entrees. `felo/*`​ n'etait pas present dans CANDIDATES. Backups `.bak-20260922`​ pour les deux fichiers. Verifications : py_compile OK, deux copies identiques (sha256 51331bd3d6cc0d07), les 3 cibles d'eco toujours candidates, aucun job cron ne cite les noms retires, et `script: probe_omniroute.py`​ du job `5c9dd16aaa37`​ est bien resolu vers `%LOCALAPPDATA%\hermes\scripts\` (hermes_cli/cron.py:571-587).
- Restent des candidats morts non demandes : `gemini/gemini-2.5-flash`​ et `-lite`​ (404 cote Google), `zc/glm-5.3`​ (spawn ENOENT), `pollinations/*`​ (401, connexion desactivee). Note : `provider_for()`​ renvoie `oc`​ par defaut, donc un modele pollinations vivant serait attribue au provider `oc` (bug latent, sans effet aujourd'hui).
- Cause du 503 d'eco qualifiee : en appel parallele direct sur le proxy, `ResourceExhausted: Worker local total request limit reached (551/16)` — compteur de fenetre a 551 pour un plafond de 16 sur la cle NVIDIA/modele nano-omni. Ce n'est pas un probleme de parallelisme ni de proxy. Le probe horaire teste les 8 candidats (ThreadPool 4) dont les 2 cibles NIM d'eco et gemini : il consomme le quota dont eco depend.
- Structure des porteurs du venv : chaque service tourne en 2 processus — un superviseur `venv\Scripts\python.exe`​ et un travailleur sous `.hermes-runtime\python\generation-...`​. Mesure : gateway 12508 (superviseur) / 6740 (travailleur, 13,8 s CPU) ; backend 3168 / 15496 (tient 9119) ; proxy NIM 10996 / 3672 (tient 20200). C'est pourquoi `hermes update --list-venv-holders` remonte 6 porteurs.
- Marqueeur `.update-incomplete`​ (`{"attempts": 3}`) toujours present : il ne se purge qu'une fois le venv libre (arrêt des 6 porteurs + fermeture de la session CLI), pas pendant que la pile tourne.
