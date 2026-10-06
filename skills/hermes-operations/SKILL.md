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

## Référence rapide (commandes)

| Besoin | Commande |
|---|---|
| **Archiver un skill** (récupérable, jamais supprimé) | `hermes curator archive <skill>` |
| Lister les skills archivés / en restaurer un | `hermes curator list-archived` · `hermes curator restore <skill>` |
| État du curateur / déclencher une revue / geler un skill | `hermes curator status` · `hermes curator run` · `hermes curator pin <skill>` |
| Récupérer gateway bloqué après mise à jour | `hermes update` puis `hermes gateway restart` |
| **Gateway mort / ticker cron figé** (plus aucun job ne tourne, jobs « en retard ») | `hermes gateway status` ; procédure complète : `references/cron-heartbeat-diagnosis.md` |
| Historique des décisions du curateur | `hermes curator ledger` |
| Budget mémoire (lecteur autoritaire) | `hermes memory status` + `scripts/check_memory.ps1` |
| Inventaire réel des skills d'un profil (sans troncature) | `find <profil>/skills -mindepth 3 -maxdepth 3 -name SKILL.md` |
| Lire / écrire une valeur de config | `hermes config get <clé>` · `hermes config set <clé> <val>` — **jamais `set` sur une clé LISTE** |
| Agir sur un autre profil | `hermes -p <profil> <sous-commande>` |
| Créer / tester / lister les jobs d'un profil | `hermes -p <profil> cron create …` · `cron status` · `cron run <id>` · `cron list` |
| **Diagnostiquer un job qui semble bloqué** (lecture seule : état réel, PID du worker, motifs de log, verrous) | `references/cron-job-diagnostic.md` |

**Diagnostic = lecture seule jusqu'au GO.** Un état anormal se rapporte d'abord (état, durée, cause `établie` / `hypothèse` / `inconnue`, recommandation) ; ne jamais tuer un process, relancer un job ou lancer un reindex sans GO explicite. Ne pas présenter une hypothèse comme établie, et signaler tout écart avec la mesure plutôt que de le corriger en silence.

`hermes curator` est le cycle de vie des skills **créés par l'agent** : la revue est une tâche
d'arrière-plan qui élague, consolide et archive. Les skills bundled et hub-installed ne sont jamais
touchés, **les archives sont récupérables et la suppression automatique n'existe pas** — d'où
`archive` plutôt qu'un `rm`. C'est aussi la commande à retrouver quand on cherche « où ai-je rangé ce
skill » : `list-archived`, puis `restore`.

### La revue d'arrière-plan écrit dans tes fichiers pendant ta session

Voir [references/background-review.md](references/background-review.md).

## ESTOP — what it does

- Sentinel file: `%LOCALAPPDATA%/hermes/ESTOP` (written by `agent/estop.py`). Checked via `check_paused(component, logger)`.
- Gated: cron dispatch (`cron/scheduler.py`), kanban dispatch (`gateway/kanban_watchers_common.py`), new gateway turns. In-flight work is never killed; it finishes normally.
- NOT gated: outbound webhooks (`agent/outbound_webhooks.py`) and inbound webhook platforms (`gateway/platforms/webhook.py`) — they keep firing while paused. To stop webhooks, disable the platform or filter at the receiver.
- Resume is tick-based: no restart needed, next scheduler/gateway tick picks up.

## Inspection et config : méthodes non-interactives

Voir [references/inspection-config-noninteractive.md](references/inspection-config-noninteractive.md).

### Multiplexeur de sessions d'agents (tmux / Herdr) — Hermes n'a pas de backend natif

Voir [references/agent-session-multiplexers.md](references/agent-session-multiplexers.md).

### Créer une tâche planifiée Hermes (Windows)

Voir [references/scheduled-tasks-windows.md](references/scheduled-tasks-windows.md).

### Snapshot git de la config (`docs/`)

Voir [references/config-git-snapshot.md](references/config-git-snapshot.md).

## Multi-bot Telegram (deux bots = deux profils)

Voir `references/multi-telegram-bots.md` : 1 `TELEGRAM_BOT_TOKEN` = 1 bot ; plusieurs bots simultanés exigent plusieurs profils (`hermes profile create watch --clone`, `hermes -p <profil> gateway start` + `hermes gateway start`). Parc actuel : `default`=@Hermes_assistante_2026_bot (chat principal), `veille`=@Hermesveille1_veille_bot (**bot de veille de l'utilisateur**), `watch`=@Omaths2_watch_bot (bot distinct — PAS le bot de veille, ne pas confondre). Ne pas injecter `channel_directory.json` à la main — l'appairage se fait au premier `/ping` Telegram.

## Envoyer un message ponctuel (récap de fin de chantier) par l'API Bot

Voir [references/bot-api-message.md](references/bot-api-message.md).

## Update procedure

Voir [references/update-procedure.md](references/update-procedure.md).

## Limites inter-agents (delegate_task et A2A)

Voir [references/inter-agent-limits.md](references/inter-agent-limits.md).

## Masque récursif — état

Voir [references/masque-recursif.md](references/masque-recursif.md).

## A2A — procédure d'activation (préparée, non activée)

Voir [references/a2a-activation.md](references/a2a-activation.md).

## Supervision du gateway sur Windows (le trou de surveillance)

Voir [references/gateway-supervision-windows.md](references/gateway-supervision-windows.md).

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

Voir [references/pitfalls.md](references/pitfalls.md).

## Cron d'un profil : créer, tester, vérifier

Voir [references/cron-profil.md](references/cron-profil.md).

## Jetons et secrets : mesurer sans divulguer

Voir [references/tokens-secrets-measurement.md](references/tokens-secrets-measurement.md).

## Verification

Voir [references/verification.md](references/verification.md).

## Memory & runbook bookkeeping

Voir [references/memory-bookkeeping.md](references/memory-bookkeeping.md).

## References

- `references/estop-matrix.md` — command matrix (Telegram vs CLI, aliases, what is/is-not gated).
- `references/config-editing-safety.md` — modifier `config.yaml` sans le casser : clés liste vs scalaires,
  harness de vérification sur copie (`-SelfTest`, md5), test d'isolation `HERMES_HOME`, test du chemin
  d'écriture d'un script destructeur, versionnement des scripts livrés.
- `references/profile-provisioning.md` — provisionner un 2ᵉ profil isolé : section `providers:`
  obligatoire (sinon `Unknown provider`), clé dédiée posée par script, chaîne `fallback_model`,
  **ordre réel du repli (fusion `fallback_providers` + `fallback_model`, gratuit avant payant) et sa
  preuve par défaillance forcée**, `skills.disabled`, SOUL qui nomme les interdits, preuve d'inférence
  `hermes -p <profil> -z`, et **isolation d'une passe documentaire** (§6 bis) : worktree git dédié
  (`-b <branche>` quand `main` est déjà cochée) + `terminal.cwd` du profil, profil de travail non
  versionné par une seule ligne dans `.git/info/exclude`, `setup --non-interactive` sans effet.
- `references/local-service-triage.md` — un port local ne répond plus : trancher « encore utile ou
  vestige » en lisant la base du routeur (`~/.omniroute/storage.sqlite` : `provider_connections`,
  `combos`, `call_logs`/`proxy_logs`), dater la panne, et retirer des deux côtés ou pas du tout.
- `references/session-multiplexers.md` — héberger les panes d'agents : tmux vs Herdr (Herdr ne s'appuie
  pas sur tmux), mapping des verbes, ce qui survit à un détachement vs un redémarrage d'hôte,
  intégrations `herdr integration install …`, conception d'un adaptateur (MCP/plugin/rien) et checklist
  d'audit read-only avant migration.
- `references/windows-task-failure-triage.md` — tâche planifiée Windows en échec : séparer « jamais
  chargé » (politique d'exécution d'un compte système), « abort volontaire » et « crash », puis
  chiffrer la conséquence destructrice d'un correctif avant de l'appliquer.
- `references/token-leak-audit.md` — un secret a fuité : carte des fuites dans une install Hermes
  (`.hermes_history`, `pastes/`, `sessions/`, `cache/terminal/`, chaque `.env`), empreinte + `getMe`
  pour trier les jetons encore vivants, nettoyage par correspondance de contenu ou à longueur constante,
  vérification par empreinte quand l'ancienne valeur est détruite, et séquence de rotation sans que le
  secret passe par le chat.
- `references/hermes-home-git-baseline.md` — versionner le home (`skills/`, `profiles/`, `config.yaml`)
  sans y laisser de secret : motifs d'exclusion par catégorie (jetons tiers, sessions WhatsApp/MCP,
  binaires, tickers cron), le fichier `nul` qui fait échouer `git add -A`, le scan par empreinte (yc le
  piège de la clé réelle cachée dans un exemple `curl` d'une doc de skill), **l'audit de TOUT
  l'historique et la purge en une passe**, les **contrôles bloquants avant un push** (fichiers
  sensibles, contenu, > 50 Mo, `.gitattributes`), le piège `.env.*` qui avale `.env.example`, la
  **restauration sur une autre machine** (installeur Hermes d'abord, puis `git init`/`fetch`/`checkout`
  par-dessus — jamais `git clone` dans un dossier non vide) et la **fusion de deux dépôts en un seul**
  (clone de travail puis `--ff-only`, collisions précalculées, rangement sous `docs/`).
- `references/jev-primitives.md` — JEV (TypeSafe System One) : ou il vit, signatures et pieges
  (`choice` prend un dict d'options, `score` plafonne a 10 niveaux), latence/cout mesures, cout reel
  via `/api/v1/auth/key`, pourquoi il n'est PAS cable dans le backend par defaut, et le verdict des
  candidats de fallback local (Laya Core ML ecarte : Apple Silicon only).
- `scripts/scan_history_secrets.py` — scanner rejouable de **tout l'historique** d'un dépôt
  (`rev-list --objects --all` + `cat-file --batch`), qui rend blob / chemin / taille / occurrences /
  `sha256[:16]`, propose la liste `--purge-cmds` et sort en 1 si un motif matche (gate utilisable).

Extraits créés par la compression A.3 (2026-10-06) — un fichier par domaine, contenu verbatim :

- `references/background-review.md` — la revue d'arrière-plan du curateur écrit dans tes fichiers pendant ta session (détection, conduite à tenir).
- `references/inspection-config-noninteractive.md` — inspecter et configurer Hermes sans interaction (état, clés, profils, lecteurs autoritaires).
- `references/agent-session-multiplexers.md` — héberger plusieurs sessions d'agents : tmux / Herdr, et ce qu'Hermes n'a PAS en natif.
- `references/scheduled-tasks-windows.md` — créer une tâche planifiée Hermes sous Windows (schtasks, compte, déclencheur, échecs).
- `references/config-git-snapshot.md` — versionner la config dans `docs/` : snapshot git, exclusions, contrôles avant push.
- `references/bot-api-message.md` — envoyer un message ponctuel (récap de fin de chantier) par l'API Bot Telegram.
- `references/update-procedure.md` — procédure de mise à jour Hermes : ordre des étapes, préflight, restart du gateway.
- `references/inter-agent-limits.md` — limites inter-agents : ce que `delegate_task` et A2A ne savent pas faire.
- `references/masque-recursif.md` — état du masque récursif (profils/ACL) : ce qui est masqué et ce qui ne l'est pas.
- `references/a2a-activation.md` — A2A : procédure d'activation (préparée, non activée), cas d'usage stratégiques et pièges.
- `references/gateway-supervision-windows.md` — supervision du gateway sur Windows (le trou de surveillance), double process, restart et vérification.
- `references/pitfalls.md` — pièges Hermes : ESTOP vs `/resume`, commandes gateway-only, webhooks non gelés, etc.
- `references/cron-profil.md` — cron d'un profil : créer, tester, vérifier, diagnostiquer un run en échec, relire `state.db`.
- `references/tokens-secrets-measurement.md` — jetons et secrets : mesurer sans divulguer (empreintes, `getMe`, rotation hors chat).
- `references/verification.md` — vérification post-opération : ce qui prouve que l'état est bien celui annoncé.
- `references/memory-bookkeeping.md` — tenue de `memories/MEMORY.md` et du runbook : budget en caractères, lecteurs autoritaires.