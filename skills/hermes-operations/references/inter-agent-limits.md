<!-- Extrait de hermes-operations/SKILL.md, lignes 431-456 (compression A.3 du 2026-10-06) — contenu verbatim. -->

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

