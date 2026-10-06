<!-- Extrait de hermes-operations/SKILL.md, lignes 457-491 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Masque récursif — état

Bornes effectives du masque appliqué à `delegate_task` — colonne *runtime* relue dans `config.yaml`
section `delegation`, colonne *défaut code* lue dans `hermes_cli/config_defaults.py` (le défaut
s'applique dès que la clé est absente : retirer une clé **relâche** la borne, ça ne la fige pas) :

| Règle | Runtime | Défaut code | Sémantique exacte |
|---|---|---|---|
| Profondeur max | 1 | 1 (`MAX_DEPTH`, plancher `_MIN_SPAWN_DEPTH`) | seuls les agents de profondeur 0..N-1 peuvent spawner ; aucune détection de cycle |
| Timeout par enfant | 120 s | 0 = **aucun plafond** | cap d'**inactivité** (secondes sans progrès, pas de durée totale), plancher 30 s ; tout signe de progrès (appel terminé, changement d'outil) relance la fenêtre |
| Sous-agents simultanés | 3 | 10 | cap des délégations async : à saturation la demande est **rejetée**, pas mise en file (l'appelant repart en synchrone) |
| Budget d'itérations | 250 | 250 | `delegation.max_iterations` — le vrai garde-fou de coût d'un enfant |
| Budget tokens par enfant | — | — | ⚠ aucune clé dédiée (à implémenter par patch) ; à défaut : `max_iterations`, `compression_threshold_tokens` (cap du déclencheur de compaction, 0 = hérité du parent) et `max_tokens` de l'enfant **hérité du parent** (`delegate_tool.py` : `child_max_tokens = getattr(parent_agent, "max_tokens")`) |
| Détection de cycle | — | — | ⚠ toujours absente du code (seuls des compteurs de heartbeat nommés `_HEARTBEAT_STALE_CYCLES_*` existent) : passer `max_spawn_depth` > 1 lève le seul garde-fou anti-récursion |
| A2A (inter-agents) | désactivé | fail-closed | plugin bundled `a2a-platform`, `a2a` dans `_DEFAULT_OFF_TOOLSETS` (`hermes_cli/tools_config.py`) |

Clés natives **non renseignées** ici (défauts en vigueur, à connaître avant de croire à une borne) :
`oneshot_max_children` (2 ; 0 = illimité, cap des sous-agents d'un run `-q`/`--oneshot`),
`max_summary_chars` (24000), `independent_completions` (false = « one message per call »),
`subagent_auto_approve` (false → auto-refus des approvals côté enfant, jamais d'`input()` en worker),
`surface_child_process_notifications` (false).

Changer `delegation.*` : `hermes config set delegation.<clé> <valeur>`, puis vérifier le placement
réel sous `delegation:` (`grep -n "^delegation:" -A 14 config.yaml`) — une clé pointée peut atterrir
sous une section voisine. Nota : `hermes config validate` n'existe plus dans 0.21.5 : la vérification se fait via `hermes config check` (exit 0, « Config version: 46 ✓ », section Required vide). Pour appliquer les migrations automatiques, utilisez `hermes config migrate`.

**Pourquoi depth reste à 1** : `max_spawn_depth` est le seul garde-fou anti-récursion du code
(`tools/delegate_tool.py` : `effective_role = "orchestrator" si child_depth < max_spawn_depth sinon
"leaf"`). Il n'existe aucune détection de cycle (pas de suivi d'ancêtres ni de graphe). Passer à 3
lèverait le seul garde-fou existant — à ne faire qu'après avoir écrit la détection de cycle.

**Pourquoi A2A reste désactivé** : aucun pair Hermes à interconnecter, et l'activer ouvre un port
d'écoute (défaut 9900, bind 127.0.0.1 tant qu'aucun token). Procédure d'activation complète et
vérifiée : section « A2A — procédure d'activation » ci-dessous (scripts prêts, jamais exécutés).

