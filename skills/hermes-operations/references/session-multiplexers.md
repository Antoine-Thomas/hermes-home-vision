# Multiplexeurs de sessions d'agents (tmux, Herdr) et adaptateur Hermes

Bilan vérifié sur ce parc : Hermes n'a **aucun** backend de multiplexeur ; tmux n'est utilisé que par la
doc du skill `autonomous-ai-agents` (3 copies) et par un seul chemin de code (nettoyage des workers
kanban) ; Herdr (`herdrdev/herdr`) est une alternative autonome à tmux, pas un wrapper. **Tout ce qui est
marqué « conçu » plus bas n'a PAS été exécuté** — ne pas le présenter comme validé.

## 1. Herdr : ce que c'est, ce que ce n'est pas

- `herdrdev/herdr` — Rust, Apache-2.0, binaire unique, home `herdr.dev`, doc `herdr.dev/docs`.
- Multiplexeur **autonome** avec serveur d'arrière-plan (comme tmux) : préfixe `ctrl+b`, souris native,
  workspaces / tabs / panes, plugins et marketplace. **Il ne s'appuie pas sur tmux et ne le wrappe pas**
  (aucune dépendance tmux) : c'est un remplaçant. Son apport réel = il connaît les agents — chaque pane
  est marqué `working` / `blocked` / `idle` / `done`, remonté au tab et au workspace.
- CLI : `herdr` (attache ou relance la session par défaut), `herdr session list|attach|stop|delete`,
  `herdr workspace|tab|pane|agent|integration …`, et `--json` sur les commandes destinées aux scripts.
- Surface d'automation : CLI + **socket API** + `herdr api schema --json` (schéma complet du protocole —
  c'est la base propre pour générer un adaptateur). Pages utiles : `socket-api`, `integrations`,
  `session-state`, `persistence-remote`.
- Installation : `curl -fsSL https://herdr.dev/install.sh | sh`, `brew install herdr`,
  `mise use -g herdr`, et Windows `powershell -ExecutionPolicy Bypass -c "irm https://herdr.dev/install.ps1 | iex"`
  (support Windows encore en beta).

## 2. Persistance — la distinction qui décide de l'architecture

| Événement | Processus | Layout | Conversation agent |
|---|---|---|---|
| Détachement du client (fermer le terminal, perdre le SSH) | conservés | conservé | conservée (le process n'a pas bougé) |
| Redémarrage du serveur ou de la machine hôte | **perdus** | restauré | seulement si l'agent a une reprise native (intégration Claude Code / Codex) |

Règle : « je ferme mon Mac » est un détachement client → sans risque ; « la machine hôte redémarre » tue
les agents. L'hôte du serveur Herdr — et le gateway Hermes qui doit répondre sur Telegram — doit donc
être une machine qui reste allumée, pas le poste portable.

## 3. Mapping tmux → Herdr (les verbes que la doc Hermes emploie)

| tmux | Herdr |
|---|---|
| `tmux new-session -d -s X` | `herdr workspace create --cwd <projet> --label X` (session nommée : `herdr session attach X`) |
| `tmux send-keys -t X 'cmd' Enter` | `herdr pane send_text <w1:p1> "cmd"` (bas niveau : `pane.send_keys`, `pane.send_input`) |
| `tmux capture-pane -p -S -50` | `herdr pane read <w1:p1> --source recent --lines 50` |
| `tmux ls` / `list-panes` | `herdr pane list` · `herdr agent list` · `herdr session list --json` |
| `tmux kill-session -t X` | `herdr pane close <w1:p1>` · `herdr session stop X` · `herdr server stop` |
| `tmux attach -t X` | `herdr` · `herdr session attach X` · `herdr --remote <machine>` |
| (aucun équivalent) | `herdr agent wait <w1:p1> --until done` — état d'agent plutôt que scraping d'écran |

La cible d'un pane s'écrit `<workspace>:p<index>` (ex. `w1:p1`), pas un nom de session.

## 4. Intégrations agents

`herdr integration install hermes|claude|codex|…` installe l'autorité de statut et la reprise de session
native. **Hermes Agent figure dans le tableau officiel des agents supportés** (autorité de statut : screen
manifest ; rôle : session) : Herdr sait héberger et suivre Hermes, alors que Hermes ne sait pas piloter
Herdr. Côté Hermes, l'unique artefact Herdr est le plugin communautaire `herdr-auto-reconcile`
(tier community) : il surveille des panes allowlistés et injecte un tour `AUTO_RECONCILE` — **détecter et
réveiller, jamais piloter** (aucun prompt, aucune approbation, aucune commande). Il exige
`allow_gateway_injection`, `owned_panes`, une `gateway_session_key` pointant une route gateway existante,
et un gateway (les hôtes CLI/TUI/Desktop sont explicitement non supportés).

## 5. Adaptateur Hermes → multiplexeur (conception, non construite)

- **Option recommandée** : serveur MCP local `herdr` wrappant la CLI en `--json`, exposant
  `session_list`, `workspace_create`, `agent_start`, `pane_read`, `pane_send`, `agent_wait`, `pane_close` ;
  déclaré sous `mcp_servers:` puis `hermes gateway restart`. Découplé des internes Hermes, utilisable
  depuis le CLI **et** depuis Telegram.
- **Option plugin Hermes** : plus intégré (hooks + tools), mais couplé à la version — les plugins récents
  exigent `ctx.state` et l'API d'injection du gateway, absentes des versions publiées anciennes.
- **Option zéro code** : garder tmux comme backend bas niveau du parc (kanban swarm) et n'utiliser Herdr
  que comme cockpit humain — mais alors Hermes ne sait pas envoyer de touches dans les panes Herdr.
- **Prévoir la cohabitation** : le nettoyage kanban s'appuie sur les sessions `swarm-<assignee>` ; changer
  de multiplexeur impose soit de conserver ce chemin, soit de patcher `_cleanup_worker_tmux` — sinon les
  workers morts s'accumulent sans bruit.

## 6. Checklist d'audit avant migration (read-only)

1. **Réalité de l'hôte d'abord** : OS, shell de l'outil terminal, et existence des chemins cités par le
   demandeur. Ces chemins peuvent être faux (`~/.config/hermes`, `/opt/hermes`, `/srv` n'existent pas ici ;
   le vrai config est `%LOCALAPPDATA%/hermes/config.yaml`) et un « VPS » supposé peut n'avoir aucune trace
   (`~/.ssh` absent = aucun accès distant configuré).
2. **Présence du multiplexeur** : `command -v tmux|herdr` **dans le shell de l'outil terminal**, puis
   `tmux ls` — un socket absent signifie « zéro session à migrer », pas « erreur ».
3. **Usages réels** : `grep -RIl 'tmux'` scopé (un grep récursif large EXPIRE, cf. SKILL.md), plus
   `search_files` en `--include='*.py'` sur `hermes-agent/` pour séparer doc et code.
4. **Sessions vivantes** : lister les sessions/panes réellement actives avant d'annoncer un inventaire.
5. **Sauvegardes avant écriture** : `config.yaml` (+ `backups/`), `skills/`, `profiles/<profil>/skills/`.
   `~/.tmux.conf` peut ne pas exister : ne pas annoncer une sauvegarde qui n'a rien copié.
6. **Rollback** = restaurer ces copies + retirer l'entrée d'adaptateur. Aucune étape n'exige de
   désinstaller tmux ni de tuer une session en activité.

## 7. Pièges

- **Le dialogue de confiance de Claude Code reste à traiter quel que soit le multiplexeur** : injecter
  `Enter` (premier dialogue), puis `Down` + `Enter` pour `--dangerously-skip-permissions` (défaut = « No »).
  En Herdr ce sont des `pane send_keys`, la séquence ne change pas.
- **Un agent supporté dans le sens Herdr→Hermes ne prouve pas le sens inverse.** Les deux intégrations
  sont indépendantes.
- **Pas de téléchargement ni d'installation sans accord explicite** (règle du parc) : la phase
  d'installation se demande, elle ne se suppose pas.
