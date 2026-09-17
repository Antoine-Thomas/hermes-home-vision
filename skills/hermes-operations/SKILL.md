---
name: hermes-operations
description: "Use when controlling Hermes ESTOP, gateway, A2A, or Telegram ops."
version: 1.0.0
author: searching-murphy
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, gateway, estop, telegram, cron, kanban, runbook]
    related_skills: [omniroute-gateway, fallback-intelligent, veille-2-agent]
---

# Hermes Operations

Control Hermes at runtime without restart: ESTOP (pause/resume), gateway status, Telegram dispatch, and runbook/memory bookkeeping.

## ESTOP — what it does

- Sentinel file: `%LOCALAPPDATA%/hermes/ESTOP` (written by `agent/estop.py`). Checked via `check_paused(component, logger)`.
- Gated: cron dispatch (`cron/scheduler.py`), kanban dispatch (`gateway/kanban_watchers_common.py`), new gateway turns. In-flight work is never killed; it finishes normally.
- NOT gated: outbound webhooks (`agent/outbound_webhooks.py`) and inbound webhook platforms (`gateway/platforms/webhook.py`) — they keep firing while paused. To stop webhooks, disable the platform or filter at the receiver.
- Resume is tick-based: no restart needed, next scheduler/gateway tick picks up.

## Inspection et config : méthodes non-interactives

`hermes tools` est **interactif** : lancé hors TTY il bloque la session. Ne jamais l'appeler pour
inspecter toolsets, plugins ou clés. Les équivalents non-interactifs :

| Besoin | Commande |
|---|---|
| État des plugins (activé / `not enabled`) | `hermes plugins list` |
| Lire une valeur de config | `hermes config get <clé.pointée>` |
| Écrire une valeur de config | `hermes config set <clé.pointée> <valeur>` |
| Intégrité / migration de la config | `hermes config check` |
| Inventaire skills (N enabled, M disabled) | `hermes skills list` |
| Budget mémoire | `hermes memory status` + `scripts/check_memory.ps1` |
| Santé install / version | `hermes doctor`, `hermes --version` |

**`hermes config set` n'écrit que des scalaires.** Sur une clé *liste* il **remplace la liste entière
par la valeur scalaire** — `hermes config set platform_toolsets.cli a2a` transforme les 17 toolsets
en la chaîne `a2a`, et l'avertissement n'arrive qu'*après* l'écriture. Pour toute clé liste : édition
textuelle ciblée du YAML, jamais `config set`. Supprimer une clé : `hermes config unset`. Procédure
complète, harness de vérification sur copie et test d'isolation `HERMES_HOME` :
`references/config-editing-safety.md`.

**`hermes config validate` n'existe pas** (sous-commandes réelles : `show, edit, get, set, unset,
path, env-path, check, migrate`) — `check` est le validateur : il affiche `Config version: N ✓` et
sort 0. De même `hermes plugins status <nom>` n'existe pas : seulement `list`, `enable`, `disable`.
Si l'utilisateur demande une commande absente, dire laquelle est fausse et basculer sur
l'équivalent — ne pas improviser un flag.

**Authenticité d'une fonctionnalité** : ne pas conclure d'un grep, lire le `plugin.yaml`. Et grepper
scopé — un `grep -rn` lancé depuis `$LOCALAPPDATA/hermes` se noie dans `data/*/venv`,
`site-packages`, `node_modules`, `.hermes-runtime` (une recherche a rendu 81 Ko de bruit
`pygments`/`chardet`). Chercher dans `hermes-agent/` en excluant ces quatre-là. Les plugins bundled
sont sous `hermes-agent/plugins/<kind>/<name>/` ; `plugin.yaml` fait foi pour `requires_env` et
`provides_tools`.

**Lire les tâches planifiées depuis git-bash** : `schtasks /Query` sort en UTF-16, donc `grep`
répond `Binary file (standard input) matches` sans rien afficher. Passer par `tr -d '\0'` et
utiliser `grep -ia`. Garder `MSYS_NO_PATHCONV=1` pour les commutateurs `/TN`, `/FO`, `/NH`. Plus
lisible et hors du problème d'encodage : `Get-ScheduledTask | Where-Object { $_.TaskName -like '*Hermes*' } | Select-Object TaskName, State | Format-Table -AutoSize`.

### Créer une tâche planifiée Hermes (Windows)

Reprendre le principal d'une tâche existante au lieu d'en inventer un :
`Export-ScheduledTask -TaskName 'Hermes - check memory'` montre la convention du parc (SID de
l'utilisateur courant + `<LogonType>InteractiveToken</LogonType>`).

```powershell
$action   = New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '" --auto') -WorkingDirectory (Split-Path $script)
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 4:00am
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName '<nom>' -Action $action -Trigger $trigger -Settings $settings -Force
```

- Pointer l'action sur le python du venv Hermes en **chemin absolu**, jamais un `python` nu : le
  contexte de la tâche n'a pas le PATH de la session interactive.
- `-StartWhenAvailable` : un déclenchement manqué (PC éteint la nuit) se rattrape au démarrage suivant.
- Garder la création dans un script ré-exécutable à côté du script cible
  (`scripts/creer_tache_<nom>.ps1`) — c'est ce qui rend la tâche reproductible après un incident.
- Tester avec `Start-ScheduledTask -TaskName '<nom>'`, puis lire `Get-ScheduledTaskInfo`
  (`LastRunTime`, `LastTaskResult`) **et** le log propre du script : un code retour suffit à déclarer
  victoire alors que le script n'a rien écrit.
- Une tâche `Disabled` alors que `hermes doctor` voit le service tourner (cas du profil watch) ne
  remontera pas seule après un redémarrage : le signaler plutôt que le corriger sans demande.

### Snapshot git de la config (`Desktop/hermes_install`)

La copie versionnée du config live est `Desktop\hermes_install\snapshot\config.yaml` — il n'y a
**pas** de `hermes_install\config.yaml` à la racine du dépôt. « Resynchroniser
hermes_install/config.yaml » désigne donc ce fichier-là : le dire avant d'agir, plutôt que de
supposer que la racine contient la copie.

Procédure : `cp` live → snapshot, confirmer les deux `md5sum` identiques, `diff` vide, puis commit.
**S'attendre à un drift plus large que la dernière modification** : la copie versionnée retarde de
toute la migration de config, donc lire le `diff` en entier et rapporter chaque hunk au lieu de
supposer que seule l'édition du jour manque.

`config.yaml` ne contient aucun secret en clair (`api_key: ''` partout, les clés vivent dans
`.env`) : la copie brute est sûre. Mais le `.gitignore` déclare la politique « REDACTED uniquement »
et `snapshot/config.yaml.redacted` n'a **aucun régénérateur** (le scanner de secrets est un scanner
seul, sans mode export) — le rafraîchir signifierait inventer un format : le laisser tel quel et le
signaler.

## Multi-bot Telegram (deux bots = deux profils)

Voir `references/multi-telegram-bots.md` : 1 `TELEGRAM_BOT_TOKEN` = 1 bot ; deux bots simultanés exigent deux profils (`hermes profile create watch --clone`, token `8967...` en watch / `8802...` en default, `hermes -p watch gateway start` + `hermes gateway start`). Ne pas injecter `channel_directory.json` à la main — l'appairage se fait au premier `/ping` Telegram.

## Update procedure

Voir `references/update-preflight.md` pour la séquence complète : précaution (multiplex_profiles, snapshot frais, arrêt des writers), contrôles post-update, et récupération des pièges d'exécution Windows (gateway tué par Job Object → `schtasks /Run /TN Hermes_Gateway` ; serveur long-running → `cmd //c "start /b …"` car `setsid` absent de git-bash et background terminal timeout). frais, arrêt des writers).

`hermes update` has NO `--restart` flag — this fails silently and confusingly. The correct sequence:

**Editing config.yaml: use `hermes config set KEY value`, never patch/write_file.** `patch` and `write_file` refuse `config.yaml` as security-sensitive ("Agent cannot modify security-sensitive configuration"). `hermes config set gateway.multiplex_profiles false` is the sanctioned path; verify placement with `hermes config get KEY` and by grepping the section (a dotted key can land under a sibling heading — confirm it is under the right section, not just that it resolves).

**Post-update gateway dies on Windows (Job Object #91675): recover with `schtasks /Run /TN Hermes_Gateway`, not `hermes gateway start`.** The cold-start gateway spawned inside `hermes update`'s shell is killed when that shell exits because it sits in a Windows Job Object. `schtasks /Run /TN <task>` starts the task-scheduler task OUTSIDE any Job Object, so it survives. The task name is `Hermes_Gateway` for default, `Hermes_Gateway_watch` for the watch profile (check `schtasks /Query /FO CSV /TN <task>` if a run says the task is missing or disabled). Verify with `hermes gateway status` → look for `✓ Gateway process running (PID: …)`.

The correct sequence:

1. **Pre-check (read-only)**: `hermes update --plan` — shows what will be updated, which services will restart, and the install method. Safe on live fleet.
2. **Run update**: `hermes update -y` (auto-accepts config migration prompts).
3. **Verify**: `hermes doctor` — check for "mixed sys.modules" warning.
4. **Fix if needed**: `hermes gateway restart` if doctor warns about modules.
5. **Confirm**: `hermes gateway status` + `hermes doctor` clean output.

**state.db cleanup after repair**: if state.db was repaired (`.pre_repair`, `.corrupted` files exist), purge them ONLY after `PRAGMA integrity_check` returns `ok` on the current `.db`. These backups can be 400+ MB each.

## Limites inter-agents (delegate_task et A2A)

**`delegate_task` a des bornes natives dans `delegation.*` — les utiliser plutôt que d'écrire un
wrapper** : `max_spawn_depth`, `max_concurrent_children`, `child_timeout_seconds`. La garde de
profondeur est réelle et refuse avec un message explicite (`Delegation depth limit reached
(depth=N, max_spawn_depth=M)`).

**`max_spawn_depth` compte les ARÊTES, pas les agents.** La garde est `if depth >= max_spawn` où
`depth` est la profondeur du *parent* : `2` donne la chaîne A→B→C (3 agents), `1` = parent→enfant
seulement (défaut). Régler `3` pour « 3 niveaux » autorise en réalité 4 agents — piège vérifié
dans `tools/delegate_tool.py`.

**Aucun knob natif** pour : plafond de tokens par sous-agent (l'enfant hérite du `max_tokens` du
parent), détection de cycles, log par appel. Ces trois points exigent un guard externe.

**A2A n'est pas une dépendance manquante.** C'est un plugin platform livré avec Hermes
(`hermes-agent/plugins/platforms/a2a/`), transport stdlib pur : `requires_env: []`, aucun package
à installer, aucune clé requise. Le `⚠ a2a (system dependency not met)` du doctor est un **gate de
configuration** — le toolset est dans `_DEFAULT_OFF_TOOLSETS` et `_a2a_tools_available()` ne renvoie
vrai que si `a2a_agents` est renseigné, ou `A2A_PORT` posé, ou `platforms.a2a.enabled: true`.
Activer A2A ouvre un port d'écoute (défaut 9900 ; bind 127.0.0.1 tant qu'aucun token n'est
configuré) : ne pas l'activer sans demande explicite.

**Le plugin A2A n'expose aucune hook d'interception** (ni middleware, ni call-site) : un guard ne
peut pas s'y brancher, l'intégration passe par un wrapper documenté.

## Masque récursif — état

Bornes effectives du masque appliqué à `delegate_task` (vérifiées dans `config.yaml` section `delegation`,
valeurs *runtime*, pas souhaitées) :

| Règle | Valeur | Implémentation |
|---|---|---|
| Profondeur max | 1 (garde-fou natif) | `delegation.max_spawn_depth` |
| Timeout par appel | 120 s | `delegation.child_timeout_seconds` |
| Sous-agents simultanés | 3 | `delegation.max_concurrent_children` |
| Budget tokens par sous-agent | — | ⚠ À implémenter par patch du repo |
| Détection de cycle | — | ⚠ À implémenter par patch du repo |
| A2A (inter-agents) | désactivé | Plugin bundled, fail-closed par défaut |

Changer `delegation.*` : `hermes config set delegation.<clé> <valeur>`, puis vérifier le placement
réel sous `delegation:` (`grep -n "^delegation:" -A 14 config.yaml`) — une clé pointée peut atterrir
sous une section voisine. `hermes config validate` n'existe pas dans 0.21.3 : la validation se fait
avec `hermes config check` (exit 0, « Config version: 45 ✓ », section Required vide).

**Pourquoi depth reste à 1** : `max_spawn_depth` est le seul garde-fou anti-récursion du code
(`tools/delegate_tool.py` : `effective_role = "orchestrator" si child_depth < max_spawn_depth sinon
"leaf"`). Il n'existe aucune détection de cycle (pas de suivi d'ancêtres ni de graphe). Passer à 3
lèverait le seul garde-fou existant — à ne faire qu'après avoir écrit la détection de cycle.

**Pourquoi A2A reste désactivé** : aucun pair Hermes à interconnecter, et l'activer ouvre un port
d'écoute (défaut 9900, bind 127.0.0.1 tant qu'aucun token). Procédure d'activation complète et
vérifiée : section « A2A — procédure d'activation » ci-dessous (scripts prêts, jamais exécutés).

## A2A — procédure d'activation (préparée, non activée)

**Prérequis : un 2ᵉ agent Hermes opérationnel et joignable.** Sans pair, ne pas activer : un port
d'écoute de plus à surveiller, zéro bénéfice.

**Scripts prêts** (jamais exécutés en mode activation) :

| Script | Rôle | Options |
|---|---|---|
| `%LOCALAPPDATA%\hermes\scripts\activer_a2a.ps1` | activation en 8 étapes | `-Force`, `-SkipGateway`, `-ConfigPath`, `-SelfTest` |
| `%LOCALAPPDATA%\hermes\scripts\desactiver_a2a.ps1` | retour au défaut fail-closed | idem |

`activer_a2a.ps1` enchaîne : sauvegarde `config.yaml.a2a-backup-<horodatage>` →
`hermes plugins enable a2a-platform` → ajout de `- a2a` dans `platform_toolsets.cli` →
`hermes config set platforms.a2a.enabled true` → `hermes config check` → redémarrage des gateways
(profil watch inclus s'il existe) → vérification du port 9900 → rappel des 5 outils A2A.
`desactiver_a2a.ps1` fait l'inverse, plus `hermes config unset platforms.a2a.enabled`.

**`-SelfTest` est le seul mode exécutable sans risque** : il rejoue insertion/retrait sur une COPIE
de `config.yaml`, vérifie l'idempotence des deux sens et l'égalité md5 après add+remove, sans toucher
ni au plugin ni aux gateways. Validé : add 17→18 éléments, add x2 sans effet, remove 18→17, md5
identique à l'original.

**Config minimale — les 3 clés :**

| Élément | Où | Rôle |
|---|---|---|
| `platforms.a2a.enabled: true` | `config.yaml`, **clé racine** | gate des outils A2A (`tools.py:_a2a_tools_available`) et démarrage de la plateforme entrante |
| `a2a_agents:` | `config.yaml`, racine | pairs sortants : `url`, `auth: {type: bearer, token}`, `timeout`, `capabilities` |
| `A2A_BEARER_TOKEN` (partagé) ou `A2A_PEER_TOKENS="alice:tok1,bob:tok2"` (par pair) | `.env` | authentification entrante |

`gateway.platforms.a2a.enabled` **n'est pas** la clé lue par le gate des outils — `gateway/config_loader.py`
fusionne les deux emplacements côté gateway, `tools.py` lit le niveau racine. Rencontrer un cas où les
outils n'apparaissent pas malgré la plateforme active : vérifier d'abord l'emplacement de la clé.

**Sécurité** : bind `127.0.0.1` tant qu'aucun jeton n'est posé (il faut un jeton **et**
`A2A_HOST=0.0.0.0` pour élargir — l'activation ne le fait jamais d'elle-même) ; audit
`a2a_audit.jsonl` ; conversations dans `a2a_conversations/` (survivent à la compaction) ; texte
entrant filtré (prompt-injection) et slash-commands non invocables par un pair ; texte sortant
nettoyé des chaînes ressemblant à des credentials.

**Port** : 9900 (`A2A_PORT`). Agent Card servie sur `/.well-known/agent-card.json`.

**Pièges vérifiés (reproduits en isolation) :**
- `platform_toolsets.cli` est une clé **liste** : c'est `references/config-editing-safety.md` qui
  s'applique ici (jamais `config set`, insertion textuelle ciblée).
- Un aller-retour YAML complet (`ruamel.yaml` load/dump) **reformate tout `config.yaml`** :
  réindentation des séquences, rewrapping des blocs de prompts. Diff inacceptable sur le fichier live.
- Une regex qui matche `^platform_toolsets:` doit **restituer la ligne d'en-tête** : la première
  version du script la consommait et supprimait le bloc entier. C'est le `-SelfTest` (comparaison
  md5) qui l'a attrapé.
- `is_connected()` lit `extra.enabled`, pas le champ typé `enabled` : l'état « connecté » affiché
  peut être faux alors que la plateforme tourne. Se fier à `netstat` sur 9900.

**Vérification après activation** : `hermes config check`, `netstat -ano | findstr :9900` (attendu :
`127.0.0.1:9900` en LISTENING), `hermes plugins list` (`a2a-platform` enabled).

**Désactivation** : `scripts\desactiver_a2a.ps1`, puis vérifier que 9900 n'écoute plus. Les jetons
`A2A_*` restent dans `.env` (inertes plugin désactivé) : les retirer à la main si besoin.

## A2A — cas d'usage stratégiques (lus dans le code, non activés ici)

| Cas | Ce que ça donne | Exemple concret | État vérifié |
|---|---|---|---|
| Fédération multi-machines | un agent Hermes par machine, chacun sa mémoire, ses clés, son modèle ; découverte par Agent Card | le bureau (PC) appelle l'agent veille (serveur / VM) pour une synthèse ; le distant garde ses propres credentials | Supporté (`#25176`, `#689` : agent↔agent inter-machines). Distant ⇒ `A2A_HOST` **et** jeton. Aucun pair configuré ici |
| Délégation cross-framework | appeler un agent non-Hermes | un agent LangChain / CrewAI / Google ADK / OpenClaw qui annonce une capacité devient un pair comme un autre | Interopérabilité **annoncée** dans `plugin.yaml` (JSON-RPC v1.0). Jamais testée localement : aucun pair non-Hermes dans le parc — ne pas la présenter comme acquise |
| Orchestration de capacités | `a2a_orchestrate(capability, message, mode)` diffuse à tous les pairs annonçant la capacité (`*` = tous) | « Cherchez les 5 dernières publications arXiv et croisez les résultats » avec 3 agents de recherche | Outil présent, modes `all` / `first` / `best` réels |
| Service callable (inbound) | Hermes devient un pair découvrable | un workflow n8n / Make découvre `/.well-known/agent-card.json` et envoie un `message/send` | Actif seulement avec `platforms.a2a.enabled: true`. La tâche entre dans la **session live** : elle occupe un tour réel de l'agent |
| Paiement à la requête (x402) | facturer un appel | — | **Hors périmètre** : `DESIGN.md` liste DID/Ed25519, scopes OAuth2 et x402 (`#14559` bindu) comme non-objectifs assumés. Ne pas planifier dessus |

### Pièges propres à A2A

- **Piège de lecture de config** : `grep -n a2a config.yaml` remonte `- a2a` (ligne ~717) sous
  `known_plugin_toolsets.cli` — la liste des toolsets *connus*, pas la liste *active*. Le gate réel
  est `platform_toolsets.cli` + `platforms.a2a.enabled`. Un grep naïf conclut « A2A activé » à tort.
- `hermes a2a` **n'existe pas** : activation par le plugin et les clés de config uniquement.
- **Aucune hook d'interception** dans le plugin (ni middleware ni call-site) : un guard de sécurité
  passe par un wrapper documenté, jamais par un branchement interne.
- `tasks/cancel` marque la tâche annulée et abandonne la réponse mais **ne coupe pas** le tour en
  cours de la session live : ce n'est pas un vrai abort.
- Une tâche entrante consomme un tour de l'agent destinataire — cadence lente, une alerte = un appel.
- `a2a_orchestrate(mode="best")` = **la réponse la plus longue**, pas un score de qualité ni de
  latence (le code se qualifie lui-même de « coarse »). Pour arbitrer, utiliser `all`. Les résultats
  sont triés par nom de pair, donc déterministes.
- Distant = `A2A_HOST` **et** un jeton ; sans jeton le bind reste `127.0.0.1` même si `A2A_HOST`
  est posé.
- L'interopérabilité cross-framework et les micropaiements x402 ne sont pas des fonctionnalités
  livrées : un brief qui les présente comme « working in production » mélange une issue-source
  d'exigences (`#11025` : injection session live, filtres, persistance, auth) et un non-objectif.

## Gateway restart after update

After `hermes doctor` shows "A previous update pulled new code but did not restart running gateways" → run `hermes gateway restart`. This fixes mixed `sys.modules` (code and binary out of sync). The gateways keep serving stale modules until explicitly restarted.

## Gateway double-process is normal

`hermes gateway status` reports one PID but `Get-CimInstance Win32_Process` where CommandLine like '*gateway*' routinely shows 2: parent `...\.venv\Scripts\python.exe -m hermes_cli.main gateway run` (PPID = Task Scheduler) and child `...\.hermes-runtime\python\generation-...\python.exe -m hermes_cli.main gateway run` (PPID = parent). Do not treat as zombie — killing the child alone drops gateway (`No gateway process detected`). Only kill stale generations: CreationDate older than last `schtasks /Run /TN Hermes_Gateway` or PID not matching `hermes gateway status`. Verify with `ProcessId, ParentProcessId, CreationDate` table before any taskkill.

## Restart verification

After `hermes gateway restart` or `schtasks /Run /TN Hermes_Gateway`, wait 7-9s then check `hermes gateway status` and `Get-Content "$env:LOCALAPPDATA/hermes/logs/gateway.log" -Tail 25` for `telegram connected` / `polling healthy` / `set_my_commands OK`. Log tail is authoritative — status alone can show `No gateway process detected` while child is still warming (2s turn machinery). ESTOP check is `Test-Path "$env:LOCALAPPDATA/hermes/ESTOP"` — must be False for normal ops.

## Commands

### Telegram (any chat authorized in `hermes-telegram` / `channel_directory.json`)

```
/pause              # pause, no reason
/pause <raison>     # pause with reason stored in sentinel and echoed back
/pause off          # resume (also accepts: resume, stop, disengage)
```

Handler: `gateway/run_busy.py:_handle_pause_command` — `busy_policy=dispatch`, so it runs even while agent is busy. Slash dispatch bypasses the ESTOP gate (`run_inbound.py:estop_turn_allowed`), so `/pause off` is always reachable.

### Telegram — listing commands

```
/com [page]        # alias de /commands, liste dynamique paginee (182 cmds)
/commands [page]   # idem, page 1 par defaut, page_size 15 sur Telegram
/help [filter]     # aide filtree, /help skills liste les skills
```
Impl: `hermes_cli/commands.py:CommandDef("commands", aliases=("com",), execute="gateway_commands", busy_policy="dispatch", gateway_only=True)` + `hermes_cli/slash_exec.py:EXECUTORS["gateway_commands"]` (dynamique via `COMMAND_REGISTRY` + `get_skill_commands()`). Ajouter un alias = patch `commands.py` puis `hermes gateway restart` — verifier PID stale (double process apres restart, tuer l'ancien generation-*).

Pitfalls:
- Refuse toute commande `/camera`/`/stream` infinie avec micro continu declenchable a distance et ignore ESTOP — surveillance covert illegale sans consentement en France, contourne l'arret d'urgence et laisse un processus detache sans voyant; proposer `/snapshot` (photo unique) ou `/record 30s` borne avec voyant visible et respect ESTOP, ou solution dediee type Frigate/motionEye.

### CLI (PC)

```bash
hermes pause [--reason "..."]   # engage ESTOP
hermes resume                    # disengage ESTOP
hermes status                    # check model/provider + ESTOP hint
ls "$LOCALAPPDATA/hermes/ESTOP" # sentinel presence = paused
```

## Pitfalls

- `/resume` in gateway is NOT ESTOP resume — it resumes a named session (`CommandDef resume [name]`, `argument_mode mixed`). Always use `/pause off` to lift ESTOP from Telegram; `hermes resume` only exists as CLI.
- `CommandDef pause` is `gateway_only` — it does not exist as CLI slash, and `hermes pause` does not exist as gateway slash. Use the right channel for each form.
- Assuming webhooks stop on pause — they do not; ESTOP has no hook into webhook dispatch. Verify with `grep -rn check_paused` if unsure whether a component respects ESTOP before claiming it is frozen.
- One Telegram channel (`channel_directory.json: platforms.telegram`) can back multiple bot usernames only if they share the same token. Two distinct bot tokens require two entries via `hermes gateway setup`; otherwise only one bot actually receives dispatch.
- `patch` tool refuses to write `config.yaml` (security guard) — edit Hermes config via `terminal` (Python read/write or `hermes config set`), never `patch` or `sed` range substitution which silently truncates on fragile boundaries.
- GPU-bound inference (LivePortrait/SadTalker at 100% GPU / ~95% VRAM) starves the gateway event loop and triggers `CRITICAL gateway.shutdown_watchdog: missed 3 liveness probes -> exit 75` — this is an intentional self-kill for the Task Scheduler to restart, not a code bug; recover with `hermes gateway restart` + verify `telegram connected` in `gateway.log`, never treat as auth/network failure.
- A gateway that died on its own with `gateway.log` ending in "Received UNKNOWN as a planned gateway stop — exiting cleanly" and "Shutdown context: signal=UNKNOWN parent_pid=... parent_cmdline='(unknown)'" orphaned because its parent (Task Scheduler spawn) died — not a code bug. Confirm with `gateway_state.json` showing `"gateway_state":"draining"` and `hermes gateway list` showing `✗ not running`, then restart with `hermes -p <profile> gateway start` (profile flag, not `gateway restart`). Distinct from the `exit 75` watchdog self-kill above.
- `cron.scheduler: Job '...' failed: lost its durable fire claim ownership / _abort_if_fire_claim_lost` after a gateway restart is a benign abort of the in-flight fire, not a gateway crash — clean the orphaned job with `hermes cron remove <id>` and do not alert on it.
- `deliver=telegram` on heavy/background cron jobs blocks the gateway loop and amplifies spam via `security-monitoring/monitors/log_monitor.py` (each ERROR forwarded as lvl8 `Erreur API` per bot) — use `deliver=local` for GPU/monitoring jobs; extend `EXCLUDE` in `log_monitor.py` with `lost its durable fire claim|fire claim ownership lost|cron\.scheduler.*failed|_abort_if_fire_claim_lost` to suppress internal scheduler noise.

## Verification

```bash
hermes gateway status   # expect PID + Scheduled Task Hermes_Gateway
hermes gateway list     # all profiles at once (default + watch) -> ✓/✗ per profile
 hermes status          # model/provider sanity
cat "$LOCALAPPDATA/hermes/channel_directory.json"  # which telegram chats are authorized
```

**Rapport de vérification (passe en lecture seule)** : quand la demande est « colle-moi les sorties
de <commandes> », livrer les sorties brutes dans l'ordre demandé — pas de résumé, pas d'artefact de
contrôle, pas de commit pour cette partie. Commenter uniquement les écarts par rapport à l'attendu,
et requalifier ce qui est **préexistant** (vulnérabilités npm du doctor, tâche planifiée désactivée)
au lieu de le présenter comme une régression de la session.

**Chantier explicitement reporté à une session dédiée** : ne pas le relancer depuis une session
multi-chantiers, ne pas en rejouer les tests. Relever seulement son état — `git status` sur
`hermes-agent` (propre, aucun diff = patch annulé, pas de patch à moitié appliqué), emplacement des
sauvegardes pré-patch — et l'écrire dans le plan du dépôt. Le contexte frais fait partie de la
procédure : une tentative de patch upstream échouée sur du code frais se rejoue à l'identique.

## Memory & runbook bookkeeping

- `memories/MEMORY.md` has a hard ~2200 char budget (injected every turn). When near limit, compress existing entries in place before appending — shorten verbose lines, merge related bullets, keep `§` separators. Target ≤2170 to leave headroom.
- **Verify memory usage in CHARACTERS, never with `wc -c`.** `wc -c` counts bytes and accented characters cost 2 bytes in UTF-8, so it overstates usage (2071 "chars" measured for 2036 real). The budget is characters. Authoritative reader: `scripts/check_memory.ps1`, which uses `(Get-Content -Raw).Length`; Python equivalent `len(open(f, encoding='utf-8').read())`.
- `check_memory.ps1` alert thresholds (MEMORY 2100 / USER 1300) differ from the `config.yaml` limits (2200 / 1375). Name the reader you are quoting — otherwise "under the threshold" and "above the target" coexist and nobody can tell which applies.
- `check_memory.ps1` is **read-only**: it writes no file and creates no `.bak`. Do not attribute sanitising backups to it.
- `memories/USER.md` (~1000 chars) holds stable preferences; `MEMORY.md` holds environment facts and standing ops rules.
- `recovery_runbook.md` is the durable ops reference — record ESTOP semantics, channel/bot mapping, and verification commands there with tags `[telegram pause resume bots surveillance assistance]` so future sessions can `search_files` it.
- Tag new ops facts with all relevant keywords in the same line so keyword search finds them without scanning full history.

## References

- `references/estop-matrix.md` — command matrix (Telegram vs CLI, aliases, what is/is-not gated).
- `references/config-editing-safety.md` — modifier `config.yaml` sans le casser : clés liste vs scalaires,
  harness de vérification sur copie (`-SelfTest`, md5), test d'isolation `HERMES_HOME`, test du chemin
  d'écriture d'un script destructeur, versionnement des scripts livrés.
