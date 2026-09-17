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


## Phase 3 — Configuration du profil veille

*(en attente)*

## Phase 4 — Décision A2A

*(en attente)*
