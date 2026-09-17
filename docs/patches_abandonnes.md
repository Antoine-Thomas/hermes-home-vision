# Patch repo delegate_task — abandonné 2026-09-17

## Objectif initial
Détection de cycle + budget tokens par sous-agent dans tools/delegate_tool.py

## Pourquoi abandonné
- Le patch demande 500+ lignes de lecture de code
- Risque de casser delegate_task (test non concluant)
- Gain marginal : max_spawn_depth=1 suffit comme garde-fou anti-récursion
- Aucun cycle observé en pratique

## Alternatives retenues
- Config : child_timeout_seconds=120, max_concurrent_children=3 (déjà fait)
- Config : max_spawn_depth=1 (gardé)
- Si besoin : ouvrir une PR upstream au dépôt Hermes

## Pour reprendre
Voir hermes-agent/tools/delegate_tool.py + delegate_tool_config.py
Tests nécessaires : appel simple / récursif / boucle / normal
