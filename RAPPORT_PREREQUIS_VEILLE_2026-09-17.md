# Rapport — Finalisation des prérequis du 2ᵉ agent veille

Date : 2026-09-17 · Machine : OMATHS (Windows 11) · Hermes Agent v0.21.3 (2026.9.14, upstream 97962358)
Objectif de session : finaliser les prérequis du profil `veille`. **A2A reste désactivé.**
Périmètre : préparation uniquement — aucune activation, aucune clé ajoutée, aucun élagage sans validation.

Rapport précédent : `RAPPORT_CHANTIERS_A2A_2026-09-17.md` (4 chantiers livrés).

---

## Phase 0 — Vérification d'entrée (bloquante)

Statut : **OK — les 4 points passent.** Aucun arrêt de procédure.

| Contrôle | Attendu | Mesuré | Verdict |
|---|---|---|---|
| MEMORY.md | ~2076 / 2100 chars | 2076 / 2100 (`check_memory.ps1`) | ✓ |
| USER.md | ~1193 / 1300 chars | 1193 / 1300 (`check_memory.ps1`) | ✓ |
| `hermes doctor` | clean | 0 régression, 4 issues préexistants | ✓ (baseline) |
| Version | 0.21.3 | v0.21.3 · config v45 · `Up to date` | ✓ |
| Port 9900 | muet | aucun listener | ✓ |
| Clés `A2A_*` | 0 | 0 dans `.env`, 0 dans l'environnement du shell | ✓ |

### Détail mémoire

- `MEMORY.md` : 2076 chars, 2120 octets, 6 séparateurs `§`, **7 sections** —
  Environnement / Hermes / Second cerveau / Outils clés / Préférences / Règles transversales / Vidéo.
  Séparateurs et découpage conformes à l'état post-incident. Fin de ligne LF.
- `USER.md` : 1193 chars (lecteur `check_memory.ps1`), 1171 chars en lecture Python universelle,
  1232 octets sur disque. Écart de 22 = 22 fins de ligne CRLF conservées par `Get-Content -Raw`.
  **Écart de mesure, pas un écart de contenu** — à noter pour l'incident du 16/09.
- Deux lecteurs, deux seuils : `check_memory.ps1` alerte à 2100/1300, `config.yaml` limite à
  2200/1375. Les deux sont sous leur seuil respectif. La valeur citée ici est celle de
  `check_memory.ps1` (lecteur autoritaire côté script, cf. skill `hermes-operations`).

### Détail doctor

0 régression. Les 4 issues sont **préexistants** et sans rapport avec la session :

1. Browser tools (agent-browser) — 2 vulnérabilités npm
2. web workspace — 6 vulnérabilités npm
3. WhatsApp bridge — 4 vulnérabilités npm
4. `hermes setup` — clés API manquantes pour l'accès complet aux outils

Attendu et conforme : `⚠ a2a (system dependency not met)` — gate de configuration, pas une
dépendance manquante (A2A volontairement désactivé).

### Baseline de non-régression relevée

- Skills bureau : **98 enabled, 7 disabled** (3 hub-installed, 25 builtin, 77 local) — 105 au total.
- Services : backend 9119 → HTTP 200 ✓ ; RAG 8200 → HTTP 404 sur `/` (serveur vivant) ✓ ;
  SiYuan 6806 → HTTP 401 (auth requise, service vivant) ✓ ; OmniRoute 20128 → HTTP 307 ✓.
- `ESTOP` : absent ✓ (fonctionnement normal).
- Dépôts git : `Desktop/hermes_install` propre ; `hermes-agent` propre (aucun diff = patch annulé,
  pas de patch à moitié appliqué).

### Observations hors périmètre (état trouvé, aucune action prise)

1. **Gateway `default` non démarré.** `hermes gateway status` → `✗ No gateway process detected`.
   Log : arrêt propre le **17/09/2026 à 00:02:07** — `Received UNKNOWN as a planned gateway stop —
   exiting cleanly`, `parent_pid=21884 parent_cmdline='(unknown)'`. `gateway_state.json` est en
   `"gateway_state":"draining"`. C'est le motif documenté « gateway orphelin dont le parent
   (Task Scheduler) est mort ». **Antérieur à cette session** (00:02 vs session ouverte à 12:04) :
   ce n'est pas une régression, mais le bot Telegram du profil `default` est muet depuis.
   Le gateway `watch` tourne (PID 22876, démarré 16/09 19:19:13).
2. **Deux tâches gateway pour le profil par défaut** : `Hermes_Gateway` (schtasks, état Ready,
   dernier run 16/09 19:18:35) et `HermesGateway` (sans underscore, `Hidden`, déclenche
   `pwsh -NoProfile -Command "hermes gateway start"` au logon, dernier run 13/09 16:23:32).
   `HermesGateway` ressemble à un vestige supersédé. À traiter ou non — décision opérateur.
3. **9 tâches planifiées `Hermes*`** recensées : check memory, désaturer memoire, Reindex RAG,
   serve backend, Hermes-PurgeReports, HermesGateway, Hermes_Gateway, Hermes_Gateway_watch,
   Hermes_NVIDIA_NIM_Proxy.
4. **`Hermes-PurgeReports`** : `LastTaskResult=1` (échec) le 17/09 à 02:00 — sans rapport avec
   la session, à examiner séparément.
5. Profil `veille` : créé, isolé, **gateway arrêté**, `.env` présent mais **vide de toute clé**
   (en-tête de commentaires uniquement). `config.yaml` : `default: eco`, `provider: omniroute`,
   `base_url: http://127.0.0.1:20128/v1`, `plugins.enabled: []`. `SOUL.md` = 667 octets (défaut).

---

## Phase 1 — Proxy NVIDIA NIM (diagnostic réalisé, décision en attente)

### Verdict : ENCORE UTILE — mais hors du chemin par défaut, et actuellement mort.

Le proxy n'est pas un vestige : il est référencé par une connexion OmniRoute **active** et par un
combo dédié. Il est en revanche **hors du chemin par défaut** (le modèle Hermes `eco` ne l'utilise
pas) et **en panne silencieuse** depuis le 13/09.

### Ce qui consomme le port 20200 — un seul consommateur, identifié

| Élément | Constat |
|---|---|
| Connexion provider OmniRoute `NVIDIA NIM (Proxy)` | `id=1910f7a8-8037-4e0a-9024-674fde7df9b7`, `provider=openai`, `auth_type=apikey`, **`is_active=1`**, `test_status=active` |
| URL déclarée | `provider_specific_data.baseUrl = http://127.0.0.1:20200/v1` |
| Dernier test OmniRoute | `last_tested = 2026-09-17T08:51:42Z`, `updated_at = 2026-09-17T08:52:41Z` |
| Combo dépendant | `nvidia-stack` — 3 modèles, tous `providerId: "openai"` (donc via le proxy) |
| Modèles du combo | `nvidia/nemotron-3.5-lightning-30b-a3b`, `nvidia/nemotron-3-super-120b-a12b`, `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
| Autres références | **aucune** — pas dans `config.yaml`, pas dans `.env` (hors `NVIDIA_API_KEY_GEMMA4`, lu *par* le proxy), aucune occurrence dans `scripts/`, aucune autre tâche planifiée |
| Combo `eco` (défaut Hermes) | 0 modèle nvidia → le défaut ne dépend pas du proxy |

### Preuve de panne : 272 appels échoués, encore hier soir

`ECONNREFUSED 127.0.0.1:20200` enregistré dans `proxy_logs` (200) et `call_logs` (72).

| Jour | Échecs |
|---|---|
| 2026-09-16 | 45 (dont 20:59:51Z = 22:59 heure locale, **après** le redémarrage d'OmniRoute de 22:09) |
| 2026-09-12 | 7 |
| 2026-09-10 | 20 |
| 2026-09-09 | 5 |
| 2026-09-08 | 19 |
| 2026-09-07 | 85 |
| 2026-09-03 | 18 |
| 2026-09-02 | 1 |

Aucun échec le 17/09 : le combo `nvidia-stack` n'a simplement pas été sollicité depuis.

### État exact de la tâche planifiée

| Champ | Valeur |
|---|---|
| Nom | `Hermes_NVIDIA_NIM_Proxy` |
| État / Enabled | `Ready` / **`Enabled: True`** |
| Déclencheur | `MSFT_TaskLogonTrigger` — **au logon uniquement**, `StartBoundary 2026-09-08T19:11:00` |
| Action | `wscript.exe "…\data\nvidia\nvidia-nim-launch.vbs"` |
| LastRunTime | **13/09/2026 16:23:29** |
| LastTaskResult | `0` |
| NextRunTime | **vide** |
| NumberOfMissedRuns | 0 |
| LogonType | `InteractiveToken`, `DisallowStartIfOnBatteries: true` |

Dernier logon machine : **13/09/2026 16:23:29** (Event 7001) — la tâche a donc bien tiré à ce logon
et rien depuis, faute de nouvelle session. Elle n'a **aucune répétition ni redémarrage sur échec** :
une fois le process mort, il ne revient qu'au prochain logon.

Le lanceur `nvidia-nim-launch.vbs` est idempotent (si 20200 écoute déjà, il sort) et démarre le proxy
détaché, fenêtre masquée (`0, False`).

### État du proxy lui-même

- Port 20200 : **aucun listener**. `curl http://127.0.0.1:20200/health` → échec de connexion.
- **Aucun fichier de log** dans `data/nvidia/` : le proxy écrit sur stdout, la fenêtre est masquée →
  la sortie est perdue. C'est ce qui rend la panne invisible.
- Clé : `NVIDIA_API_KEY` n'est posée ni au niveau utilisateur ni machine ; le script retombe sur
  `data/nvidia/.env` → `NVIDIA_API_KEY_GEMMA4` (présente). Le lancement est donc fonctionnel une
  fois relancé.
- Rôle du proxy : traduire les noms de modèles préfixés `openai/` envoyés par OmniRoute vers le
  format NVIDIA NIM et relayer vers `https://integrate.api.nvidia.com/v1`.

### Ce qui est cassé concrètement

Toute utilisation du combo `nvidia-stack` échoue immédiatement (connexion refusée), sans message
visible côté Hermes puisque l'échec est consommé par OmniRoute. Le coût est réel : 3 modèles
NVIDIA (dont Nemotron 3 Super 120B et Lightning 30B) sont annoncés dans le catalogue OmniRoute
mais inutilisables.

### Options soumises à décision

| # | Option | Contenu | Effet |
|---|---|---|---|
| A | **Relancer et durcir** | Redémarrer le proxy maintenant + corriger la tâche : ajouter `-StartWhenAvailable` et une répétition (ex. toutes les 15 min avec `-MultipleInstances IgnoreNew`), rediriger la sortie du proxy vers un log | Le combo `nvidia-stack` redevient utilisable ; l'état du proxy devient observable |
| B | **Retirer proprement** | Désactiver la tâche (désactivation explicite, pas de suppression) + désactiver la connexion provider `NVIDIA NIM (Proxy)` et le combo `nvidia-stack` côté OmniRoute | Plus d'appels condamnés ; les 3 modèles NVIDIA disparaissent du catalogue utilisable |
| C | **Statut quo documenté** | Ne rien changer, acter que le combo est HS et que la tâche ne tire qu'au logon | Zéro modification, mais la panne silencieuse demeure |

Aucune action n'a été effectuée : lecture seule. Décision opérateur requise.

### DÉCISION OPÉRATEUR : option A retenue (relancer et durcir)

#### 1a — Relance : FAIT

| Contrôle | Avant | Après |
|---|---|---|
| Port 20200 | aucun listener | `127.0.0.1:20200 LISTENING` (PID 19300) |
| `GET /health` | injoignable | `{"status":"ok"}` |
| Process | 0 | 2 (25244 = shim venv, 19300 = serveur) |
| Test OmniRoute `POST /api/providers/<id>/test` | — | `valid:true`, `latencyMs:113`, `testedAt 2026-09-17T10:15:19Z` |

#### 1b — Durcissement de la tâche : FAIT

Backup XML avant modification dans `data/nvidia/backups/` **et** `hermes_install/backups/taches/`,
md5 identiques (`a632db4e…`). Un second backup est pris automatiquement par le script.

| Champ | Avant | Après |
|---|---|---|
| `StartWhenAvailable` | `False` | **`True`** |
| Déclencheur | `LogonTrigger` seul | `LogonTrigger` **conservé** (`StartBoundary` inchangé) **+ `Repetition`** |
| Répétition | — | **`Interval = PT15M`**, `StopAtDurationEnd = true`, pas de `Duration` → répétition sans fin |
| `MultipleInstancesPolicy` | `IgnoreNew` | `IgnoreNew` (inchangé) |
| `ExecutionTimeLimit` | `PT72H` | `PT72H` (inchangé) |
| Action | `wscript.exe nvidia-nim-launch.vbs` | identique |

Script ré-exécutable livré : `data/nvidia/creer_tache_nim_proxy.ps1` (source de vérité de l'état
cible, rejouable après incident). Test `Start-ScheduledTask` : `LastTaskResult=0`, le VBS idempotent
n'a pas créé de doublon (1 seul listener, 1 seule instance).

**Nuance importante** : `NextRunTime` reste vide après la modification. La répétition d'un
déclencheur *logon* ne s'arme qu'à compter du prochain logon. Autrement dit le durcissement est
correct mais **inerte jusqu'au prochain logon** : si le proxy meurt maintenant, il ne sera relancé
qu'à la prochaine session utilisateur. Voir la proposition de correctif ci-dessous.

#### 1d — Vérification end-to-end

| Appel | Résultat |
|---|---|
| Direct proxy `POST /v1/chat/completions` (lightning) | **HTTP 200**, réponse NVIDIA réelle (9,6 s à froid, puis 12,0 s) |
| Via OmniRoute `openai/nvidia/nemotron-3.5-lightning-30b-a3b` | **HTTP 200 en 1,42 s** |
| Via OmniRoute `openai/nvidia/nemotron-3-super-120b-a12b` | **HTTP 200 en 0,66 s** |
| Via OmniRoute `openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | **HTTP 200 en 2,21 s** |
| `ECONNREFUSED 127.0.0.1:20200` depuis la relance (10:20Z) | **0** dans `proxy_logs`, **0** dans `call_logs` |

#### Deux défauts distincts découverts en vérifiant (non corrigés)

**Défaut 1 — le combo `nvidia-stack` est mal câblé.** Ses 3 modèles sont déclarés
`"nvidia/nemotron-…"` avec `providerId: "openai"`. OmniRoute résout le provider par le *préfixe du
nom de modèle*, pas par `providerId` : `nvidia/…` part vers un provider `nvidia` sans credentials →
`401 No active credentials for provider: nvidia`, et appelé par le nom du combo → `502` avec un
message imbriqué. Ce n'est **pas** le proxy : les mêmes modèles passent en `200` dès qu'on les
appelle sous leur forme préfixée `openai/nvidia/…` (la forme que le proxy documente dans son
en-tête). Correctif : préfixer les 3 entrées du combo par `openai/`.

**Défaut 2 — le proxy est mono-thread et se bloque.** `nvidia-nim-proxy.py` instancie
`HTTPServer` (mono-thread). Un appel abandonné en cours de route (exactement ce que fait OmniRoute
quand sa deadline locale de 15 s expire) bloque le serveur : il cesse de répondre à **tout** le
monde — `GET /health` reste sans réponse pendant ~30-60 s, la connexion traîne en `CLOSING`. Le
process reste vivant et le port reste `LISTENING`, donc rien ne se voit. Reproduit en session :
appel direct normal → `200`, puis appel client coupé à 1 s → `/health` muet, puis retour à la
normale après la fin de l'appel amont. `resilienceSettings.requestQueue.maxWaitMs=15000` côté
OmniRoute (réglage local, pas un timeout amont) rend ce scénario fréquent : les premiers appels à
un modèle Nemotron durent 9-12 s à froid.

Ces deux défauts sont **hors du périmètre initial des 4 phases** : soumis à décision.

#### 1c — Observabilité : proposition soumise, NON écrite

Le script `nvidia-nim-proxy.py` **n'accepte aucun paramètre de log** : `argparse` n'expose que
`--port` et `--host`. Il écrit sur `stdout` (`[PROXY] …`, `[NIM Proxy] Listening…`) avec
`flush=True`. Fenêtre masquée par le VBS → sortie perdue, d'où 4 jours d'invisibilité.

Proposition : modification minimale du **VBS** (une ligne de redirect, aucune modification du
Python). Nouveau `nvidia-nim-launch.vbs` :

```vbs
' NVIDIA NIM proxy auto-launch for Hermes — hidden window (no console flash)
Option Explicit
Dim sh, rc, py, script, logPath
Set sh = CreateObject("WScript.Shell")
py      = "C:\Users\searc\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
script  = "C:\Users\searc\AppData\Local\hermes\data\nvidia\nvidia-nim-proxy.py"
logPath = "C:\Users\searc\AppData\Local\hermes\data\nvidia\proxy.log"
' Idempotent: if port 20200 is already listening, do nothing.
rc = sh.Run("cmd /c netstat -an | findstr /r "":20200 "" >nul", 0, True)
If rc = 0 Then WScript.Quit 0
' Launch detached, hidden, stdout+stderr appended to proxy.log
sh.Run "cmd /c """"" & py & """ """ & script & """ >> """ & logPath & """ 2>&1""", 0, False
```

La commande générée est exactement :
`cmd /c ""…python.exe" "…nvidia-nim-proxy.py" >> "…proxy.log" 2>&1"` — vérifiable, les variables ne
changent que la lisibilité. Le log s'accumule sans rotation (à borner plus tard si besoin).

### A1 à A4 — exécution (autorisée par l'opérateur)

#### A1 — Redirect du log : FAIT, avec deux défauts révélés par le redirect lui-même

Backups : `backups/nvidia-nim-launch.vbs.20260917_122451` (VBS d'origine),
`backups/nvidia-nim-launch.vbs.20260917_123141` (VBS avec redirect seul).

Quoting vérifié avant bascule en faisant afficher la chaîne réellement construite par le VBS
(`cscript` sur un VBS de contrôle) : identique à l'attendu.

**Défaut A1 bis — le redirect casse le proxy.** Dès que `stdout` n'est plus une console, Python
retombe sur l'encodage de la locale (cp1252) au lieu de l'UTF-8 console (PEP 528). La ligne
`print(f"[PROXY] {original} → {model}")` contient un U+2192 :

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 46
```

→ **chaque requête proxied mourait** dans le handler. Correctif : `PYTHONIOENCODING=utf-8` posé
dans l'environnement de l'enfant par le VBS — c'est le motif déjà utilisé par
`profiles/watch/gateway-service/Hermes_Gateway_watch.vbs`.

**Défaut A1 ter — l'idempotence était trop laxiste.** `netstat -an | findstr /r ":20200 "` matche
**toute** connexion vers/depuis 20200, y compris les sockets clientes laissées en `TIME_WAIT` après
un arrêt. Reproduit de façon déterministe : proxy arrêté → 6 sockets `TIME_WAIT` → l'ancienne
vérification renvoie `rc=0` → **le lanceur refuse de relancer un proxy mort** pendant toute la durée
du TIME_WAIT. Correctif : `... | findstr "LISTENING"`, qui ne matche qu'un vrai socket en écoute
(vérifié : `rc=1` après arrêt, `rc=0` quand le proxy tourne).

Version finale du VBS : redirect + `PYTHONIOENCODING=utf-8` + `python -u` (non bufferisé, pour que
les lignes de démarrage et les tracebacks atterrissent immédiatement) + vérification LISTENING.

Preuve après écriture, relance par la tâche planifiée :

```
[NIM Proxy] Listening on 127.0.0.1:20200
[NIM Proxy] Upstream: https://integrate.api.nvidia.com/v1
[NIM Proxy] API key: nvapi-0IrGa-...
[PROXY] nvidia/nemotron-3.5-lightning-30b-a3b → nvidia/nemotron-3.5-lightning-30b-a3b
```

(Remarque : le proxy journalise ses 12 premiers caractères de clé NVIDIA. C'est un `print` du script
d'origine, désormais écrit sur disque. À masquer si le log doit être partagé.)

#### A2 — Threading : FAIT

`ThreadingHTTPServer` vérifié disponible dans l'interpréteur du proxy (Python 3.11.16,
`daemon_threads=True` par défaut). Backup : `backups/nvidia-nim-proxy.py.20260917_123206`
(md5 avant/après backup identiques : `0e755ac6c53f9af640dc08f41318243c`).

Diff : 2 lignes — `from http.server import HTTPServer…` → `ThreadingHTTPServer…`, et
`server = HTTPServer(…)` → `server = ThreadingHTTPServer(…)`.

Preuve du déblocage, avec une requête longue réellement en vol :

| Mesure | Résultat |
|---|---|
| Requête longue (500 tokens) en arrière-plan | **HTTP 200 en 38,49 s** |
| `GET /health` pendant qu'elle tourne | 4 appels : **14 ms / 22 ms / 14 ms / 1 ms** |
| Requête complète concurrente pendant ce temps | **HTTP 200 en 2,55 s** |
| Connexions simultanées observées | 2 × `ESTABLISHED` sur 20200 |
| Port après tout ça | `LISTENING`, pid unique |
| `ECONNREFUSED 20200` depuis 10:31Z | **0** (`proxy_logs` et `call_logs`) |

Avant le patch, ces trois appels auraient été servis en série : le premier bloquait les deux autres.

#### A3 — Combo `nvidia-stack` : FAIT

Backups : `~/.omniroute/backups/combo_nvidia-stack.20260917_123315.json` (ligne SQLite exportée)
et `~/.omniroute/backups/combo_api_20260917_123329.json` (état via l'API).
Script ré-exécutable et idempotent livré : `data/omniroute/fix_combo_nvidia_prefix.py`.

| Entrée | Avant | Après |
|---|---|---|
| n1 | `nvidia/nemotron-3.5-lightning-30b-a3b` | `openai/nvidia/nemotron-3.5-lightning-30b-a3b` |
| n2 | `nvidia/nemotron-3-super-120b-a12b` | `openai/nvidia/nemotron-3-super-120b-a12b` |
| n3 | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | `openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |

`providerId: "openai"` conservé sur les trois (cohérent avec le préfixe).

| Vérification | Résultat |
|---|---|
| `PUT /api/combos/<id>` | HTTP 200 |
| Relecture API | les 3 entrées préfixées `openai/` |
| `model="nvidia-stack"` (par le NOM DU COMBO) | **HTTP 200 en 5,78 s** (était 502), modèle servi `nvidia/nemotron-3.5-lightning-30b-a3b` |
| `openai/nvidia/nemotron-3-super-120b-a12b` | HTTP 200 en 7,20 s |
| `openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | HTTP 200 en 4,86 s |
| Combo `eco` (défaut Hermes) | **non modifié** — `updatedAt` toujours `2026-09-12T00:15:44Z`, 10 modèles, aucun nvidia |
| Connexion provider `1910f7a8` | `isActive=True`, `testStatus=active`, `baseUrl=http://127.0.0.1:20200/v1` |

Précision de schéma : la table `combos` **n'a pas de colonne `is_active`** — il n'existe donc pas
d'indicateur « combo actif » à vérifier. Les colonnes sont
`id, name, data, sort_order, created_at, updated_at, system_message, tool_filter_regex,
context_cache_protection`.

Note amont : NVIDIA a renvoyé plusieurs `503 Service temporarily overloaded` /
`ResourceExhausted: Worker local total request limit reached (16/16)` pendant les tests. OmniRoute a
réessayé et les appels ont fini en 200. C'est de la capacité côté NVIDIA, pas un défaut local — c'est
justement ce que le log rend maintenant visible.

#### A4 — Second déclencheur : FAIT

Backups XML : `Hermes_NVIDIA_NIM_Proxy.20260917_123432.xml` puis `…123448.xml`.
`creer_tache_nim_proxy.ps1` mis à jour : il produit désormais **deux** déclencheurs et reste la
source de vérité (rejoué deux fois sans dérive).

| | Avant A4 | Après A4 |
|---|---|---|
| Déclencheurs | `LogonTrigger` + répétition PT15M | `LogonTrigger` **sans** répétition (StartBoundary `2026-09-08T19:11:00` inchangé) **+ `TimeTrigger`** avec répétition PT15M |
| `NextRunTime` | **vide** | **17/09/2026 12:48:48** |
| `StartWhenAvailable` | `True` | `True` |
| `MultipleInstances` | `IgnoreNew` | `IgnoreNew` |
| Action | VBS | VBS (inchangée) |

La répétition a été retirée du déclencheur logon : deux répétitions de même période mais
désynchronisées doubleraient la cadence pour rien. Le logon démarre le proxy à l'ouverture de
session, le déclencheur horaire assure la surveillance continue.

Test `Start-ScheduledTask` : `LastTaskResult=0`, `NextRunTime` toujours renseigné, **1 seul listener**
et 1 seule instance serveur (le 2ᵉ pid est le shim `venv\Scripts\python.exe`, paire normale).




## Phase 2 — Gateway default : DIAGNOSTIC (aucune action)

### 2a — Pourquoi le gateway default est muet

**Dernier log (`logs/gateway.log`, fin du fichier, aucune ligne après) :**

```
2026-09-17 00:02:07,144 INFO  gateway.run: Received UNKNOWN as a planned gateway stop — exiting cleanly
2026-09-17 00:02:07,144 WARN  gateway.run: Shutdown context: signal=UNKNOWN under_systemd=no parent_pid=21884 parent_name=? loadavg_1m=? parent_cmdline='(unknown)'
2026-09-17 00:02:07,212 INFO  gateway.run: Sent shutdown notification to active chat telegram:8956868107
2026-09-17 00:02:11,717 INFO  gateway.run: response ready: … time=141.9s api_calls=7 response=1151 chars
```

**Cause racine — la dernière instance n'était pas détachée.** `logs/gateway-exit-diag.log`
enregistre le dernier démarrage :

```json
{"ts":"2026-09-16T17:18:37Z","tag":"gateway.start","pid":21928,
 "console_window_attached":true,"detached":true,"breakaway":null, ...}
```

Tous les démarrages précédents portent `"console_window_attached":false` et `"breakaway":true`.
Cette instance-ci a hérité de la console / du Job Object du shell qui l'a lancée (le `hermes update`
du 16/09 à 19:18). Quand le parent `21884` a disparu, le gateway a reçu un signal inconnu, l'a
interprété comme un arrêt planifié, a drainé le tour en cours (141,9 s) puis est sorti proprement —
il n'y a **aucune entrée `gateway.exit_clean`** pour le pid 21928, donc sortie non gracieuse. La
tâche planifiée ne l'a pas relevé : elle ne tire qu'au logon, et il n'y a pas eu de logon depuis.

**PID du process mort** : `gateway_state.json` déclare `pid: 21928`. Vérifié : 21928 **absent**,
21884 **absent** (seuls 22876/24596, le gateway watch, sont vivants).

**Ce que « draining » implique concrètement** (lu dans `gateway/status.py`) :

| Élément | Valeur constatée | Effet |
|---|---|---|
| `gateway_state` | `draining` | État de fin de vidage, pas un état de marche |
| `pid` | 21928 (mort) | `derive_gateway_drainable` exige un PID **vivant** ⇒ non drainable |
| `updated_at` | `2026-09-16T22:02:37Z` (≈ 10 h) | `_RUNTIME_STATUS_STALE_TTL_S = 120` s ⇒ `runtime_status_is_stale` = vrai |
| `exit_reason` | `null` | Le drain n'a jamais été conclu |
| `restart_requested` | `false` | Aucun redémarrage demandé par l'updater |
| `start_time` | `178957911544` | Identifie l'instance 21928 |

Autrement dit : **ce fichier est inerte**. Il est périmé (10 h > TTL 120 s), donc sa prétention de
vivacité n'est pas crue ; le PID est mort et l'état n'est pas `running`, donc le gateway n'est ni
« drainable » ni « occupé ». Rien à supprimer à la main : un redémarrage réécrit le fichier
(`starting` → `running`). C'est aussi ce qui fait dire à `hermes gateway status` :
`✗ No gateway process detected`.

### Hermes_Gateway vs HermesGateway — lequel est le bon ?

| | **Hermes_Gateway** | **HermesGateway** (sans underscore) |
|---|---|---|
| Description | « Hermes Agent Gateway - Messaging Platform Integration » | **aucune** |
| Action | `wscript.exe //B //Nologo "…\hermes\gateway-service\Hermes_Gateway.vbs"` | `pwsh.exe -NoProfile -Command "hermes gateway start"` |
| Déclencheur | `LogonTrigger` + `Delay PT30S` | `LogonTrigger` (`UserId OMATHS\searc`) |
| LogonType | `InteractiveToken` | `InteractiveToken` |
| Resiliency | `RestartOnFailure` 999 × 1 min, `StartWhenAvailable` | absente |
| Hidden | non | **oui** |
| Dernier run | 16/09 19:18:35 (result 0) | 13/09 16:23:32 (result 0), soit 3 s après le logon de 16:23:29 |
| Reconnue par Hermes | **oui** — `hermes gateway status` affiche `✓ Scheduled Task registered: Hermes_Gateway` | non |

**Verdict : `Hermes_Gateway` est la tâche canonique, `HermesGateway` est un vestige artisanal.**
Preuves : la description officielle, le lanceur VBS généré dans `gateway-service/`, la
reconnaissance par `hermes gateway status`, et l'absence totale des réglages de résilience côté
vestige. Risque concret si on la laisse : **au logon, les deux tâches tirent** et lancent chacune un
démarrage du gateway default — double instance ou conflit de polling Telegram (le vestige masqué
échoue silencieusement, sans trace visible).

### Le gateway watch couvre-t-il le default ?

**Non.** Preuves : le process 22876/24596 tourne `--profile watch gateway run` avec
`HERMES_HOME=C:\…\profiles\watch` (VBS du watch), son log dit `Active profile: watch` et
`Session storage: …\profiles\watch\sessions`, il sert 2 plateformes (telegram + email), et à
19:19:31 il note `kanban dispatcher: another gateway already holds the dispatcher lock` — preuve que
les deux gateways sont des instances distinctes qui se coordonnent par verrou. Aucun recouvrement :
le bot Telegram du profil `default` (`channel_directory.json` → dm `8956868107`, Thomas Leroyer)
n'est servi par personne.

### 2c — Hermes-PurgeReports : DEUX défauts, aucun log d'échec

Tâche : `powershell.exe -NoProfile -WindowStyle Hidden -File "C:\ProgramData\Hermes\purge_reports.ps1"`,
quotidienne à 02:00, **exécutée sous `S-1-5-18` (SYSTEM)**, `RunLevel HighestAvailable`.

**Aucun log d'échec n'existe** — `C:\ProgramData\Hermes\logs\` était **vide**. Ce n'est pas une
absence de preuve, c'est le premier symptôme : le script écrit sa première ligne de log dès la
3ᵉ instruction (`Write-Log "=== Hermes Purge Reports ==="`). Pas de log ⇒ le script **n'a jamais
été chargé**.

**Défaut 1 — politique d'exécution.** La tâche invoque `-File` **sans `-ExecutionPolicy Bypass`**.
`ExecutionPolicy` est `Undefined` en MachinePolicy / UserPolicy / LocalMachine, et `RemoteSigned`
seulement pour `CurrentUser` (= `searc`). Pour le compte SYSTEM, la politique retombe sur le défaut
machine → chargement de fichier `.ps1` refusé → code retour `1`, aucun log. C'est cohérent avec
`LastTaskResult = 1` et un dossier `logs` vide depuis la création de la tâche (19/07).

**Défaut 2 — garde-fou en faux positif permanent.** Exécution directe du script (compte courant,
`DryRun=True` par défaut, donc non destructif) :

```
2026-09-17 12:21:37 | === Hermes Purge Reports - DryRun=True ===
2026-09-17 12:21:37 | BLOCKED: non-zero alerts for host OMATHS - refusing to purge
2026-09-17 12:21:37 | PURGE ABORTED: critical actions or alerts pending
exit=1
```

Le test est une comparaison exacte : `$row.alerts_wazuh_recentes -ne '0 alertes'`. Or la valeur du
CSV est `0 alertes (index neuf)` — donc différente de `'0 alertes'` → blocage à vie. Le script ne
purgera **jamais**, même une fois le défaut 1 corrigé.

**Conséquence à valider avant tout correctif** : si on répare les deux défauts, le script passe à
l'action réelle — les archives de plus de 30 jours partent en quarantaine puis sont **supprimées
après 24 h**. Dans `archives/` se trouve `hermes_evidence_OMATHS_20260719-202157.tar.gz.gpg`
(43 959 octets, créée le 19/07, donc au-delà des 30 jours) : elle serait purgée. C'est une
suppression de preuve d'audit — à confirmer ou à exclure explicitement.

**Divulgation** : mon exécution de diagnostic ci-dessus a créé
`C:\ProgramData\Hermes\logs\purge_20260917-122137.log` (448 octets). Aucun autre effet.

### 2b — Exécution

Backups XML : `backups/taches/Hermes_Gateway.20260917_123532.xml` et
`backups/taches/HermesGateway.20260917_123532.xml`.

| Étape | Résultat |
|---|---|
| `schtasks /Run /TN Hermes_Gateway` | « Opération réussie » |
| `hermes gateway status` | `✓ Gateway process running (PID: 28656)` |
| `gateway_state.json` | `gateway_state = running`, `pid = 28656`, `updated_at = 2026-09-17T10:35:59Z`, `restart_requested = False` |
| PID vivant | vérifié (PowerShell `Get-Process`) — **pas** un pid fantôme |
| `logs/gateway.log` | `✓ telegram connected`, `Telegram polling confirmed healthy: getUpdates progressing (generation 1)`, `set_my_commands OK` ×3, `Gateway running with 2 platform(s)`, `Channel directory built: 1 target(s)` |
| Plateformes | `telegram: connected`, `email: connected`, `whatsapp: retrying`, `whatsapp_cloud: connected` |
| Dispatcher kanban | `holding singleton dispatcher lock` — le verrou est passé du watch au default, preuve de la coordination |
| `hermes gateway list` | `✓ default — PID 28656` / `✗ veille` / `✓ watch — PID 22876` |

L'état `draining` est bien parti tout seul : le nouveau démarrage a réécrit le fichier
(`starting` → `running`), **sans qu'on touche au fichier à la main**, comme annoncé dans le diagnostic.

**Vestige** : `Disable-ScheduledTask -TaskName HermesGateway` → `State=Disabled`, `Enabled=False`.
La tâche **existe toujours** (aucune suppression) : nom, action
(`pwsh.exe -NoProfile -Command "hermes gateway start"`) et déclencheurs conservés pour trace.
Après désactivation, sur les trois tâches `*Gateway*`, **seul `Hermes_Gateway` est `Ready`** —
c'est donc le seul qui tirera au prochain logon.

Le bot Telegram : connexion confirmée côté log (`telegram connected`, polling sain). Le test
bout-en-bout (envoi d'un message) reste à l'opérateur.

### 2c — Exécution

Backups : `backups/scripts/purge_reports.ps1.20260917_123643` (script) et
`backups/taches/Hermes-PurgeReports.20260917_123708.xml` (tâche).

**Défaut 1 — politique d'exécution.** Arguments avant :
`-NoProfile -WindowStyle Hidden -File "C:\ProgramData\Hermes\purge_reports.ps1"`.
Après : `… -ExecutionPolicy Bypass -File …` (Execute, principal, triggers et horaire inchangés).

**Défaut 2 — garde-fou.** Avant / après :

```powershell
# AVANT
if ($row.alerts_wazuh_recentes -and $row.alerts_wazuh_recentes -ne '0 alertes' -and $row.alerts_wazuh_recentes -ne '0') {
# APRES
$alerts = 0
if ("$($row.alerts_wazuh_recentes)" -match '^\s*(\d+)') { $alerts = [int]$Matches[1] }
if ($alerts -gt 0) {
```

**Protection de la preuve d'audit — option retenue : exclusion déclarative dans le script**
(plutôt qu'un déplacement de fichier, qui casserait les références au chemin dans les rapports
d'audit existants). Liste `$ProtectedPatterns = @('*hermes_evidence*', 'archive_sha256*')`, appliquée
aux **deux** étapes destructives (mise en quarantaine **et** suppression depuis la quarantaine), avec
une ligne de log `PROTECTED:` par fichier conservé.

J'ai étendu la protection au-delà de la demande : `archives/` contient aussi
`archive_sha256.txt` (65 o, 19/07), l'empreinte SHA-256 de l'archive de preuve — donc de la matière
d'audit au même titre. Sans cette extension il aurait été purgé, et la preuve devenue invérifiable.

**Preuve après correction, tâche exécutée réellement sous SYSTEM :**

| Mesure | Avant | Après |
|---|---|---|
| `LastTaskResult` | `1` (échec, aucun log) | **`0`** |
| Log écrit dans `C:\ProgramData\Hermes\logs\` | **jamais** (dossier vide) | `purge_20260917-123711.log` |

Contenu du log produit par SYSTEM (DryRun, non destructif) :

```
=== Hermes Purge Reports - DryRun=True ===
Protection preuves d'audit : *hermes_evidence*, archive_sha256*
PROTECTED: archive_sha256.txt - preuve d'audit, ni deplacee ni supprimee
PROTECTED: hermes_evidence_OMATHS_20260719-202157.tar.gz.gpg - preuve d'audit, ni deplacee ni supprimee
SUMMARY: 0 archives to quarantine, 0 to delete, 2 protected
=== Purge complete ===
```

**Liste de ce qui SERAIT purgé : vide.** Rien à valider, rien à supprimer — le garde-fou de la
consigne (« si le DryRun liste autre chose que ce que j'ai validé, STOP ») est satisfait par
l'absence totale de candidat. Les deux fichiers d'`archives/` sont intacts, `quarantine/` est vide.

Deux précisions utiles :

- `[switch]$DryRun = $true` est la **valeur par défaut** et la tâche n'invoque aucun paramètre : le
  passage quotidien de 02:00 est donc **toujours en DryRun**. Il n'a jamais pu supprimer quoi que ce
  soit, même avant correctif. Le risque de destruction était latent, pas actif — mais il l'aurait été
  au premier `-DryRun:$false`.
- Le log écrit par SYSTEM est en **UTF-16LE** (`Out-File` sans `-Encoding` sous PowerShell 5.1) :
  lisible par PowerShell, illisible pour `grep`/`tail`. Correctif d'une ligne
  (`Out-File $logFile -Append -Encoding utf8`) **proposé, non appliqué** — hors du diff autorisé.

### Incident de séance : MEMORY.md consolidé par un job cron

**Non demandé, non attendu : MEMORY.md est passé de 2076 à 1906 chars pendant la Phase 2, à
12:36:37.** Je le signale comme un écart à la consigne « mémoire inchangée (2076/2100) ».

**Cause — le redémarrage du gateway lui-même.** `cron/executions.db` : le pid 28656 (le gateway
redémarré à 12:36:00) a rattrapé 4 jobs en retard (`catch_up_occurrences = 11`), tous `completed` :

| Job | Nom | Cadence | Terminé à |
|---|---|---|---|
| `5712beba047f` | Mémoire auto-consolidation | 720 min | 12:36:39 |
| `a86c7c7f0721` | OmniRoute découverte IA gratuites | quotidien 09:00 | 12:36:02 |
| `493da894d8db` | Monitoring vision gratuite OmniRoute | 60 min | 12:36:25 |
| `5c9dd16aaa37` | omniroute-eco-autorefresh | horaire | 12:36:55 |

`agent.log` confirme l'appel : `12:36:37 [cron_5712beba047f_…] tool memory completed (0.01s, 211 chars)`.

**Ce n'est pas le motif de l'incident du 16/09.** Le job a fait ce pour quoi il est conçu, et son
propre rapport le documente : déclenché parce que le store était à 94 % (> seuil 90 %), consolidation
en **un seul appel batch** (4 `replace`), `USER.md` non touché (sous son seuil). Résultat annoncé :
2075 → 1906/2200 (86 %).

**Intégrité vérifiée** : 7 sections, 6 séparateurs `§`, aucun fait inventé, aucune section perdue.
Diff complet entre l'état d'avant (reconstruit, **2120 octets — exactement la taille mesurée en
Phase 0**) et l'état live :

- Fusions sans perte : GPU bridé intégré à la ligne Environnement ; doublon « RAG 2307 frag. » (il
  apparaissait deux fois) supprimé ; Skills + WP-CLI sur une ligne ; Vidéo condensée (le contenu
  branches A/B, XTTS, outils, projet reste présent).

Quatre détails atténués, listés pour qu'aucun ne disparaisse en silence :

1. `hermes curator archive` (la commande d'archivage des skills) — **supprimée**. C'est la seule
   perte réellement substantielle ; elle n'est pas couverte ailleurs dans MEMORY.md.
2. Compte de fragments RAG : `2284` → `~2300` (information volatile de toute façon).
3. Profil veille : « créé 17/09 » retiré (fait du jour, périme naturellement).
4. Profil veille : « gateway arrêté » retiré — toujours vrai et impliqué par « A2A off ».

**Aucune modification de ma part.** Je n'ai pas appelé l'outil mémoire (consigne) et je n'ai pas
restauré le fichier : la version d'avant est disponible octet pour octet dans
`%TEMP%\MEMORY_avant_consolidation.md` si tu préfères revenir en arrière. Réserve : restaurer
remettrait l'usage à 94 %, donc le job re-consoliderait sous 12 h — la boucle n'a d'intérêt que si
tu veux d'abord déplacer `hermes curator archive` vers un skill.

**Effets de bord des 3 autres jobs rattrapés : aucun.** Vérifié après coup — combo `eco` inchangé
(`updatedAt` toujours `2026-09-12T00:15:44Z`, md5 `659da0519bc4bbe5c50103d43b332dae`, identique à la
mesure d'avant le rattrapage), combo `nvidia-stack` toujours préfixé, connexion provider toujours
`isActive=True`.



## Phase 3 — Configuration du profil veille : PROPOSITIONS (aucune écriture)

### État mesuré du profil

| Élément | Valeur |
|---|---|
| `profile.yaml` | description présente, `description_auto: false` |
| `config.yaml` | `model.default: eco`, `provider: omniroute`, `base_url: http://127.0.0.1:20128/v1`, `plugins.enabled: []`, `agent: {}` |
| `.env` | **168 octets, uniquement l'en-tête de commentaires — aucune clé** |
| `SOUL.md` | 667 octets, texte par défaut générique (« You are Hermes Agent… ») |
| `skills/` | **58 skills bundled** (inventaire `skills/<cat>/<nom>/SKILL.md`), 0 local, 0 hub, 0 désactivé |
| Aucune section `skills:` | le profil n'a pas de clé `skills.disabled` |

Répartition des 58 : productivity 14, software-development 12, creative 10,
autonomous-ai-agents 5, research 4, apple 4, media 3, email 2, puis devops, web,
social-media, note-taking 1 chacun.

### 3a — Modèles candidats

Métadonnées lues dans le catalogue OmniRoute (`GET /v1/models`, 1 634 entrées).
**1 607 des 1 634 modèles ne portent aucun prix** (gratuits ou sans tarification déclarée) ; les seuls
modèles tarifés identifiés sont trois MiniMax.

| Modèle | Provider | Reasoning | Tools | Contexte | Coût | Pourquoi ce candidat |
|---|---|---|---|---|---|---|
| `auto/best-reasoning` | omniroute (combo) | **oui** (`thinking: true`) | oui | 1 048 576 in / 512 000 out | gratuit | Alias explicitement orienté raisonnement, le plus large contexte du catalogue. Dépouiller 20 papiers arXiv dans un seul contexte est le cas d'usage central de la veille |
| `nvidia-stack` | omniroute → proxy NIM 20200 → NVIDIA | oui | oui | 128 000 | gratuit | **Déterministe** : 3 modèles Nemotron nommés, stratégie `priority`, aucune rotation. Réparé et durci aujourd'hui (threading, log, idempotence) — l'agent veille ne dépend pas d'un proxy qui meurt en silence |
| `eco` (actuel) | omniroute (combo) | oui | oui | 200 000 in / 131 072 out | gratuit | Statu quo, identique au bureau, éprouvé. Mais combo orienté coût : rotation sur 10 modèles gratuits → qualité et latence variables d'une exécution à l'autre |
| `auto/best-free` | omniroute (combo) | oui (`thinking: true`) | oui | 1 000 000 in / 384 000 out | gratuit | Traduit littéralement la politique « gratuit d'abord ». Contexte 1 M |
| `auto/zai` | omniroute (combo) | oui (`thinking: true`) | oui | 128 000 / **8 192 out** | gratuit | Z.AI/GLM, dans la chaîne de repli habituelle. **Sortie plafonnée à 8 192 tokens** : gênant pour une synthèse hebdo longue, acceptable pour un digest |
| `minimax/MiniMax-M2.5` | omniroute (payant) | oui | oui | 200 000 | 0,27 $/M in · 0,95 $/M out (cache 0,135) | Secours **payant**, à mettre en `fallback_model` et pas en défaut. Respecte « payant en dernier » |
| DeepSeek (`data/harness:3080`) | local | — | — | — | — | **Indisponible** : le port 3080 n'écoute pas (vérifié). À ne pas proposer comme candidat tant que le harnais n'est pas relancé |

Recommandation : **`auto/best-reasoning` en défaut**, avec `fallback_model` sur **`nvidia-stack`**
(gratuit, déterministe) — les deux sans dépense. Alternative si tu préfères la reproductibilité à la
puissance : `nvidia-stack` en défaut.

Mise en œuvre (scalaires uniquement, donc `hermes config set` sans risque) :

```bash
hermes -p veille config set model.default auto/best-reasoning
hermes -p veille config set fallback_model.provider omniroute
hermes -p veille config set fallback_model.model nvidia-stack
```

`hermes model` est **interactif** (« Select default model and provider ») : je ne l'exécute pas en
tâche de fond, l'équivalent non interactif est `config set`.

### 3b — SOUL.md proposé (texte soumis, NON écrit)

```
Tu es l'agent de veille technologique de Thomas Leroyer (Searching Murphy, Caen).
Tu produis de la veille ; tu n'agis pas sur le système.

Rôle
- Surveiller arXiv, HuggingFace (modèles, datasets, papers), le catalogue et les prix OpenRouter,
  et les flux RSS/Atom des éditeurs et labos suivis.
- Produire une synthèse hebdomadaire datée : un paragraphe par sujet retenu, chaque affirmation
  rattachée à sa source (URL + date). Aucun sujet sans source.
- Émettre une alerte à signal fort dès détection, hors cadence : tout changement qui invalide une
  décision en cours (mise à jour majeure d'un outil du parc, rupture d'API, changement de licence,
  vulnérabilité dans une dépendance).

Règles de travail
- Filtre : ne remonter que ce qui est actionnable pour le parc de l'opérateur (Windows, RTX 3070 Ti
  8 Go, Hermes, SiYuan, WordPress, pipelines vidéo). Une nouveauté qui ne touche ni ses outils ni ses
  projets est du bruit, pas de la veille.
- Distinguer systématiquement le fait (mesuré, sourcé) de l'inférence. Aucun chiffre inventé, aucun
  modèle cité de mémoire : vérifier le catalogue.
- Dater chaque élément. Ne pas présenter comme nouveau un contenu de plus de 8 jours sans le
  signaler.
- Contradiction plutôt que remplacement : si une trouvaille contredit une note existante, signaler
  la contradiction, ne pas écraser.
- Français, concis, sans emphase. Un digest long se termine par la liste des sources.

Périmètre interdit
- Aucune action sur le système du bureau : produire du texte, l'opérateur décide.
- Ne jamais divulguer ni recopier de secrets, ne jamais écrire dans le .env du bureau.
```

### 3c — Skills : proposition de tri (validation ligne par ligne requise)

**À GARDER (6)**

| Skill | Pourquoi |
|---|---|
| `research/arxiv` | source principale, API REST sans clé |
| `web/blocked-page-recovery` | un fetch 403/429/paywall ne doit pas arrêter une veille |
| `research/llm-wiki` | construire/interroger une base markdown interliée — support naturel d'une veille cumulée |
| `autonomous-ai-agents/hermes-agent` | connaître sa propre configuration avant de la modifier |
| `software-development/github` | suivre les releases et les dépôts qui comptent pour le parc |
| `creative/humanizer` | la synthèse hebdo est un livrable rédigé ; ce skill sert la qualité du texte |

**À DÉSACTIVER (45)** — hors rôle : rien de tout cela ne sert la recherche ou la synthèse, et chaque
skill actif est du bruit dans le contexte de sélection.

- `apple/` (4) : `apple-notes`, `apple-reminders`, `findmy`, `imessage`
- `creative/` (9) : `architecture-diagram`, `ascii-video`, `baoyu-infographic`, `claude-design`,
  `design-md`, `manim-video`, `p5js`, `popular-web-designs`, `songwriting-and-ai-music`
- `autonomous-ai-agents/` (4) : `claude-code`, `codex`, `computer-use`, `opencode`
- `software-development/` (11) : `codebase-inspection`, `dogfood`, `hermes-agent-skill-authoring`,
  `inspecting-hermes-desktop-dom`, `node-inspect-debugger`, `python-debugpy`,
  `requesting-code-review`, `simplify-code`, `spike`, `systematic-debugging`,
  `test-driven-development`
- `productivity/` (14) : `airtable`, `box`, `document-to-action-items`, `docx`, `google-workspace`,
  `maps`, `meeting-action-items`, `notion`, `pdf`, `powerpoint`, `product-price-monitor`,
  `teams-meeting-pipeline`, `weekly-review-planning`, `xlsx`
- `email/` (2) : `email-inbox-triage`, `himalaya`
- `media/` (2) : `gif-search`, `songsee`
- `note-taking/obsidian`, `social-media/xurl`, `devops/sdlc-review`

**À EXAMINER (7)** — je ne tranche pas seul :

| Skill | Question |
|---|---|
| `research/competitor-news-monitor` | **désactivé côté bureau** — le rôle veille le réclame explicitement (`veille-2-agent`). Pourquoi est-il désactivé ? Tant que je ne sais pas, je ne l'active pas ici |
| `research/grounded-citations` | également **désactivé côté bureau**, alors qu'il sert exactement l'exigence « chaque affirmation rattachée à sa source » |
| `media/youtube-content` | transcripts YouTube : utile pour les conférences, hors périmètre arXiv/HF |
| `productivity/document-to-action-items` | extraire des actions datées d'un document — utile si la veille doit produire des actions |
| `productivity/weekly-review-planning` | cadre la cadence hebdo, mais c'est un skill de revue personnelle |
| `software-development/spike` | une veille peut ouvrir un spike d'évaluation — mais ce n'est plus de la veille |
| `autonomous-ai-agents/computer-use` | à désactiver par principe : le profil veille ne doit pas piloter le bureau |

**Manques à combler (ajout, pas élagage)** — vérifié : ces skills existent côté bureau mais **pas**
dans le profil veille.

| Skill absent | Pourquoi il manque au rôle |
|---|---|
| `research/rss-feeds` | le protocole `veille-2-agent` cite les flux RSS/Atom comme **source** ; aucun skill RSS n'est présent dans le profil |
| `research/veille-2-agent` | le protocole de rôle lui-même : sans lui, l'agent veille ne connaît pas son périmètre ni le format de sortie attendu |
| `research/research-content` | routeur blog/RSS/registres — doublon partiel de `rss-feeds`, à voir |

**Avertissement de mécanisme — à ne pas rater.** Les skills se désactivent par une clé **liste**
(`skills.disabled` dans `config.yaml`). Or :

- `hermes config set` sur une clé **liste remplace la liste entière par un scalaire** (piège documenté
  dans le skill `hermes-operations`, avec harness de vérification) → **`config set` est interdit ici**,
  alors que ta consigne dit « `hermes config set` uniquement ». Les deux règles se contredisent : sur
  ce point précis, la consigne détruirait la config.
- `hermes skills disable` **n'existe pas** (sous-commandes réelles : `trust, untrust, browse, search,
  install, inspect, list, check, update, audit, uninstall, reset, …, opt-out, opt-in`).
- `hermes skills opt-out` est un interrupteur **global de profil** (marqueur `.no-bundled-skills`, et
  `--remove` supprime les skills bundled non modifiés) : beaucoup trop large pour un tri de 45 skills.

Le seul chemin sûr est donc une **insertion textuelle ciblée** de `skills.disabled` dans
`profiles/veille/config.yaml` (jamais le config du bureau), sur le modèle de
`hermes-operations/references/config-editing-safety.md` : backup préalable, édition, puis
`hermes -p veille config check` et `hermes -p veille skills list` pour vérifier le résultat.

### 3d — Clés strictement nécessaires

| Clé | Nécessaire ? | Pourquoi |
|---|---|---|
| `OMNIROUTE_API_KEY` | **OUI, indispensable** | le profil pointe sur `http://127.0.0.1:20128/v1` et OmniRoute refuse sans clé (`AUTH_001 Authentication required`). Sans elle, **aucune inférence** — le profil est inerte |
| `HF_TOKEN` | Recommandée, non bloquante | HuggingFace répond sans jeton, mais avec des limites de débit basses et sans accès aux dépôts restreints. Utile pour la veille modèles/datasets |
| `OPENROUTER_API_KEY` | **Non** | le catalogue et les prix OpenRouter sont exposés publiquement (`/api/v1/models` sans clé). À n'ajouter que si tu veux des quotas plus élevés |
| Clé de recherche web (exa/brave/…) | **Non** | vérifié : le profil veille a **déjà** `✓ web search (exa)` et `✓ web extract (exa)` actifs, via `auth.json` à la **racine** de `hermes` (partagé entre profils, pas dans le `.env` du profil) |
| `TELEGRAM_BOT_TOKEN`, SMTP, WhatsApp, `DEEPSEEK_API_KEY` | **Non** | aucun besoin pour le rôle ; à ne surtout pas recopier |

**Recommandation sur la clé OmniRoute** : ne pas recopier celle du bureau. OmniRoute sait émettre des
clés dédiées (`GET /api/keys` → HTTP 200 ; table `api_keys` avec les colonnes `name`, `key`,
`allowed_models`, `machine_id`, `no_log`, `expires_at` — 6 clés existent déjà, dont `Hermes_agent`).
Une clé nommée `hermes_veille` avec `allowed_models` restreint aux modèles retenus donnerait
l'isolation réelle que le reste du dispositif cherche à obtenir. La création est une écriture :
je ne la fais pas sans ton accord.

**Entorse à l'isolation, à connaître** : `auth.json` (2 428 octets) vit à la racine de `hermes` et
n'est pas dupliqué dans le profil. Le profil veille en hérite — c'est ce qui lui donne la recherche
web. L'isolation par `.env` est donc réelle mais **partielle** ; si tu veux du strict, il faudra
traiter `auth.json` aussi.


## Phase 4 — Checklist d'activation A2A (aucune action)

Correction de cadrage d'abord : la question « 2ᵉ machine/VM joignable ? » est **sans objet par
décision d'architecture**, pas par manque. `architecture_2_agents.md` ligne 178 :
« **Ne pas créer le second agent sur une autre machine : profil local uniquement.** » Le pair est donc
le profil `veille`, sur la **même** machine. Le prérequis réseau réel n'est pas « une machine
distante », c'est « deux profils qui ne se marchent pas dessus sur le même port ».

| # | Prérequis | État mesuré | Preuve | Ce qui manque |
|---|---|---|---|---|
| 1 | Pair Hermes joignable | **Local par décision** | `architecture_2_agents.md` l.178 | Rien côté réseau. En revanche la topologie locale impose **deux ports distincts** (voir #5) |
| 2 | Profil `veille` opérationnel | Existe, isolé, `.env` vide | 58 skills, 0 clé, gateway arrêté | Le configurer : c'est la Phase 3 |
| 3 | Gateway `veille` up | ✗ `not running` | `hermes gateway list` | Le démarrer côté `veille`. Non fait — A2A reste off |
| 4 | Token A2A partagé | **0 clé** | `grep -c '^A2A_'` = 0 dans `hermes/.env` **et** `profiles/veille/.env` | Générer et poser dans **les deux** `.env`. Préférer `A2A_PEER_TOKENS="veille:tok1,bureau:tok2"` (identité = nom authentifié) au `A2A_BEARER_TOKEN` partagé (identité retombant sur l'IP) |
| 5 | Port côté `veille` ouvert | **9900 muet** (`netstat`, aucun listener) | `curl 127.0.0.1:9900/.well-known/agent-card.json` → HTTP 000 | Deux profils sur une même machine ⇒ **il faut deux ports** : 9900 pour le bureau, un autre (ex. 9901 via `A2A_PORT`) pour la veille. Aujourd'hui **aucun** port n'est posé des deux côtés |
| 6 | Agent Card accessible depuis le bureau | HTTP 000 | même curl | La card n'est servie que si `platforms.a2a.enabled: true`. Rien à tester avant l'activation : l'inaccessibilité actuelle est l'état attendu |
| 7 | Plugin `a2a-platform` | `not enabled` | `hermes plugins list` ; `plugins.enabled: []` dans le profil veille | `hermes plugins enable a2a-platform` — au minimum côté appelant, en pratique **des deux côtés** |
| 8 | `platforms.a2a.enabled` | **non posée** | `hermes -p veille config get platforms.a2a.enabled` → « Config key not set » | Poser la clé **racine** (c'est elle que lit le gate des outils), **pas** `gateway.platforms.a2a.enabled` |
| 9 | `a2a_agents` déclaré des deux côtés | **rien** | config des deux profils | bureau → veille (`url`, `auth: {type: bearer, token}`, `capabilities: [research, veille]`) ; veille → bureau. Sans paire déclarée, les outils A2A ne se chargent pas |
| 10 | **Script d'activation adapté à la topologie** | **incomplet** | `activer_a2a.ps1` : paramètres `-Force -SelfTest -SkipGateway -ConfigPath` seulement ; `$profile2 = "watch"` **codé en dur** ; vérifie 9900 uniquement | **C'est le vrai manque.** Le script ne connaît ni le profil `veille` ni un port paramétrable. Tel quel, il activerait le bureau sur 9900 et redémarrerait `watch` — pas `veille`. Il faut soit ajouter `-Port` / `-Profile`, soit écrire un script dédié côté veille |
| 11 | Mode sans risque disponible | `-SelfTest` | rejoue insertion/retrait sur **copie** du config, vérifie l'idempotence et l'égalité md5, sans toucher au plugin ni aux gateways | Non rejoué dans cette session. Reste le seul mode exécutable sans conséquence |

**Piège de lecture à ne pas rejouer** : `grep -n a2a config.yaml` remonte `- a2a` ligne 717 — c'est
`known_plugin_toolsets.cli`, la liste des toolsets **connus**, pas la liste **active**. Le gate réel
est `platform_toolsets.cli` + `platforms.a2a.enabled`.

**Réponse courte à « qu'est-ce qui manque pour lancer `activer_a2a.ps1` »** : le pair n'est pas le
problème (il est local par décision), et l'Agent Card inaccessible est l'état normal. Ce qui manque
réellement, dans l'ordre : (1) configurer le profil veille (Phase 3) ; (2) générer un jeton par pair
et le poser des deux côtés ; (3) choisir un second port pour la veille et l'assumer ; (4) activer le
plugin des deux côtés puis poser `platforms.a2a.enabled` **à la racine** ; (5) déclarer `a2a_agents`
des deux côtés ; (6) **adapter le script d'activation**, qui aujourd'hui ne sait faire que le profil
`default` sur 9900.

