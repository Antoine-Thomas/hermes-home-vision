<!-- Extrait de hermes-operations/SKILL.md, lignes 88-176 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Inspection et config : méthodes non-interactives

`hermes tools` **sans sous-commande** est l'interface interactive : lancée hors TTY elle bloque la
session. Ses **sous-commandes** sont non-interactives et sûres (`tools list`, `tools --summary`,
`tools disable|enable <nom>`) — et c'est la seule surface qui dit l'état **réel** d'un toolset : une
intention écrite dans `config.yaml` sous une clé que rien ne lit n'y change rien
(`references/profile-provisioning.md` §9). Les équivalents non-interactifs :

| Besoin | Commande |
|---|---|
| État des plugins (activé / `not enabled`) | `hermes plugins list` |
| État RÉEL des toolsets d'un profil | `hermes -p <profil> tools list` · `hermes -p <profil> tools --summary` |
| Activer / désactiver un toolset (écrit `platform_toolsets.<plateforme>`) | `hermes -p <profil> tools disable <nom>…` · `tools enable <nom>…` |
| Lire une valeur de config | `hermes config get <clé.pointée>` |
| Écrire une valeur de config | `hermes config set <clé.pointée> <valeur>` |
| Intégrité / migration de la config | `hermes config check` |
| Inventaire skills (N enabled, M disabled) | `hermes skills list` |
| Budget mémoire | `hermes memory status` + `scripts/check_memory.ps1` |
| Santé install / version | `hermes doctor`, `hermes --version` |
| Chercher / détailler un plugin du catalogue | `hermes plugins search <motif>` · `hermes plugins info <nom>` |

**Le nom d'un plugin ne prouve pas ce qu'il branche — lire `hermes plugins info <nom>` avant de
l'installer.** La fiche donne les lignes `Tools` / `Hooks` / `Middleware` : `(none)` partout signifie
que le plugin n'expose rien au runtime (typiquement un serveur MCP stdio lancé par `uv run`), donc il
ne rend PAS une primitive automatiquement disponible dans le backend, quel que soit son nom. Un
`hermes plugins list` ne dit que l'état activé/désactivé, jamais la surface d'intégration : chercher
(`search`) → lire (`info`) → présenter la fiche, puis attendre l'accord avant d'installer.

**Installer n'active pas.** `hermes plugins install <nom>` sort « Plugin installed but not enabled »
et le plugin reste inerte : c'est **`hermes plugins enable <nom>`** qui branche reellement les hooks —
il resout et installe les dependances Python, puis recharge le gateway a chaud (« Gateway reloaded
plugins — active in the running gateway now: hooks »). Preuve a rapporter, dans cet ordre : la ligne
`enabled` de `hermes plugins list`, puis le hook lu dans la SOURCE installee (`grep -n 'HOOK'
plugins/<nom>/*.py`, `plugin.yaml: provides_hooks`) — ni la sortie d'`install` ni `plugins list` ne
disent quel hook est branche. Le plugin reste modifiable dans l'arbre git du home
(`plugins/<nom>/`) : c'est cette copie qu'on committe.

**`hermes config set` n'écrit que des scalaires.** Sur une clé *liste* il **remplace la liste entière
par la valeur scalaire** — `hermes config set platform_toolsets.cli a2a` transforme les 17 toolsets
en la chaîne `a2a`, et l'avertissement n'arrive qu'*après* l'écriture. Pour toute clé liste : édition
textuelle ciblée du YAML, jamais `config set`. Supprimer une clé : `hermes config unset`. Procédure
complète, harness de vérification sur copie et test d'isolation `HERMES_HOME` :
`references/config-editing-safety.md`.

**`hermes config validate` n'existe pas** (sous-commandes réelles : `show, edit, get, set, unset,
path, env-path, check, migrate`) — `check` est le validateur : il affiche `Config version: N ✓` et
sort 0. De même `hermes plugins status <nom>` n'existe pas : seulement `list`, `enable`, `disable`. Et
`hermes tools --list` n'existe pas (la forme est `hermes tools list`) : l'argument rejeté remonte en
`unrecognized arguments` par le parseur **principal**, ce qui ressemble faussement à un problème de
`-p <profil>`.
Si l'utilisateur demande une commande absente, dire laquelle est fausse et basculer sur
l'équivalent — ne pas improviser un flag.

**`hermes skills disable <nom>` n'existe pas non plus** (sous-commandes réelles : `trust, untrust,
browse, search, install, inspect, list, check, update, audit, uninstall, reset, list-modified, diff,
opt-out, opt-in, repair-official, publish, snapshot, tap, config`). Désactiver des skills pour un
profil passe par la clé **liste** `skills.disabled` de son `config.yaml` — donc édition textuelle
ciblée, jamais `config set` — et `hermes skills opt-out` est un interrupteur **global de profil**
(marqueur `.no-bundled-skills`, `--remove` supprime les skills bundled non modifiés), trop large pour
désactiver quelques skills. Les skills bundled d'un profil vivent sous
`profiles/<nom>/skills/<categorie>/<skill>/SKILL.md` : compter par `find`, pas par la sortie de
`skills list` qui tronque les noms longs (si on relit quand même cette sortie, apparier par
**préfixe** — un nom affiché `foo-bar…` correspond à `foo-bar-entier`).

**Un compte de skills se donne sur trois niveaux, sinon il ne retombe jamais juste.** Le CLI **filtre
par plateforme** : des noms écrits dans `skills.disabled` ne correspondent à aucun skill reconnu
(typiquement `apple/*` hors macOS, ou un skill dont une dépendance manque) et restent **inertes, sans
erreur**. Les trois niveaux sont : fichiers `SKILL.md` **sur disque**, skills **reconnus par le CLI**,
et **noms écrits** dans `skills.disabled`. Additionner « désactivés + non reconnus + activés » compte
les non reconnus **deux fois** (ils sont déjà inclus dans les noms écrits) et le total dépasse le
nombre de fichiers : ce n'est pas un drift de contenu, c'est l'addition qui est fausse. La
réconciliation qui tient : `disque = reconnus + non reconnus` et `reconnus = activés + désactivés
appliqués`.

**Authenticité d'une fonctionnalité** : ne pas conclure d'un grep, lire le `plugin.yaml`. Et grepper
scopé — un `grep -rn` lancé depuis `$LOCALAPPDATA/hermes` se noie dans `data/*/venv`,
`site-packages`, `node_modules`, `.hermes-runtime` (une recherche a rendu 81 Ko de bruit
`pygments`/`chardet`). Chercher dans `hermes-agent/` en excluant ces quatre-là. Les plugins bundled
sont sous `hermes-agent/plugins/<kind>/<name>/` ; `plugin.yaml` fait foi pour `requires_env` et
`provides_tools`.

**Les hooks de routage nommés dans un brief (`pre_model_routing`, `pre_skill_selection`, `pre_rag_filter`) n'existent pas.** Vérifier la surface réelle avant de planifier un branchement : (a) **shell hooks** — config.yaml sous `hooks:`, événements dans `VALID_HOOKS` (`hermes_cli/plugins.py`) : `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`, `pre_verify`, `pre_api_request`, `post_api_request`, `on_session_start/end/finalize/reset`, etc. ; (b) **event hooks** — `~/.hermes/hooks/<nom>/{HOOK.yaml, handler.py}` avec `handle(event_type, context)`, événements `gateway:startup`, `session:start/end/reset`, `agent:start`, `agent:step`, `agent:end`, `command:*` (`gateway/hooks.py`). Un routage modèle s'accroche sur `pre_llm_call` (injecte du contexte avant l'appel), pas sur un hook `pre_model_routing` inventé.

**JEV (TypeSafe System One)** : primitive de decision appelee par script, pas un outil Hermes natif
et pas d'integration backend par defaut. Signatures et pieges (`choice` prend un DICT d'options,
`score` plafonne a 10 niveaux), latence/cout mesures, lecture du cout reel via
`/api/v1/auth/key`, et la liste des plugins d'integration disponibles mais non installes :
`references/jev-primitives.md`.

