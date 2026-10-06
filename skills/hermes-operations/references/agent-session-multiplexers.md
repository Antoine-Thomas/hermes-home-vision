<!-- Extrait de hermes-operations/SKILL.md, lignes 177-218 (compression A.3 du 2026-10-06) — contenu verbatim. -->

### Multiplexeur de sessions d'agents (tmux / Herdr) — Hermes n'a pas de backend natif

**`terminal.backend` (`local|docker|singularity|modal|daytona`) est un choix d'ISOLATION d'exécution,
pas de gestion de sessions** : il n'existe ni pilote tmux ni pilote Herdr, et aucune clé
`tmux`/`herdr`/`multiplexer` dans `config.yaml`. Donc « migrer Hermes vers Herdr » n'est jamais un
changement de config : c'est un ADAPTATEUR (le plus propre : serveur MCP local qui wrappe la CLI en
`--json`, déclaré sous `mcp_servers:`), ou rien. Le dire avant de planifier quoi que ce soit.

- **Avant de promettre un workflow de panes, vérifier que le multiplexeur est joignable DANS le shell
de l'outil terminal** (`command -v tmux` depuis ce shell-là, pas depuis un autre) : tmux peut vivre dans
WSL pendant que le terminal Hermes tourne en git-bash Windows, et la recette tmux du skill
`autonomous-ai-agents` ne s'exécute alors pas telle quelle.
- **Où tmux est réellement utilisé** : (a) la doc du skill `autonomous-ai-agents` — 3 copies
(`skills/autonomous-ai-agents/`, `profiles/watch/skills/…`, `profiles/veille/skills/…`) — c'est elle qui
porte `send-keys`/`capture-pane` ; (b) **un seul** chemin de code :
`hermes_cli/kanban_db_workspace.py::_cleanup_worker_tmux` (sessions `swarm-<assignee>`,
`tmux list-panes -F #{pane_dead}` puis `kill-session`). Tout le reste des mentions tmux dans le code
est de la compatibilité terminal (OSC 52, mouse tracking, redraw), pas de la gestion de sessions.
- **Intégration Herdr côté Hermes : une seule**, et elle n'agit pas — plugin communautaire
`herdr-auto-reconcile` (tier community, `hermes-agent/plugin-catalog/herdr-auto-reconcile.yaml`) : il
détecte et réveille des panes allowlistés, il ne les pilote jamais.
- **Découverte express « Hermes connaît-il l'outil X ? »** : `cache/plugin-catalog.json` (clé `entries`,
champs `name`/`repo`/`tier`/`description`/`capabilities`) + `hermes-agent/plugin-catalog/*.yaml`, puis
`hermes plugins list`. Beaucoup moins cher que grepper l'install — et `provides_tools`/`provides_hooks`
disent si le plugin agit ou seulement observe.
- **Un `grep -R` lancé depuis `%LOCALAPPDATA%/hermes` n'échoue pas : il EXPIRE** (mesuré : 240 s puis
300 s sans une seule ligne) — et un timeout n'est pas une absence de résultat. Cibler les fichiers
(`config.yaml`, `*.yaml`, `--include='*.py'` sous `hermes-agent/`) ou passer par `search_files`.
- Mapping complet tmux→Herdr, modèle de persistance, intégrations agents, schéma d'adaptateur et
pièges : `references/session-multiplexers.md`.

**Lire les tâches planifiées depuis git-bash** : `schtasks /Query` sort en UTF-16, donc `grep`
répond `Binary file (standard input) matches` sans rien afficher. Passer par `tr -d '\0'` et garder
`MSYS_NO_PATHCONV=1` pour les commutateurs `/TN`, `/FO`, `/NH` — ou, plus simple et hors du problème
d'encodage, utiliser l'applet PowerShell :
`Get-ScheduledTask | Where-Object { $_.TaskName -like '*Hermes*' } | Select-Object TaskName, State | Format-Table -AutoSize`.

Deux pièges MSYS en pilotant des processus : `taskkill //PID <n> //F` échoue (`Argument ou option non
valide`) — utiliser `Stop-Process -Id <n> -Force` en PowerShell ; et `cmd //c "…"` accompagné de
`MSYS_NO_PATHCONV=1` ouvre un shell **interactif** au lieu d'exécuter la commande — exporter la
variable d'abord (`export MSYS_NO_PATHCONV=1`), puis appeler `cmd /c "…"`.

