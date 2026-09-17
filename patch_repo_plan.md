# Plan — patch repo : détection de cycle + budget tokens (chantier 3)

> **Statut** : plan, aucune action effectuée
> **Écrit le** : 2026-09-17
> **À exécuter** : session DÉDIÉE, contexte frais (< 30 %), aucun autre chantier en cours

## Objectif

Détection de cycle + budget tokens par sous-agent dans `tools/delegate_tool.py` (patch upstream).

## Pourquoi reporté

- Patch sur du code upstream écrasé à chaque `hermes update`.
- Tentative précédente a bricolé le repo (annulée ; sauvegardes déplacées dans
  `snapshot/pre_patch_abandonne_20260917/`).
- `max_spawn_depth=1` est déjà un garde-fou anti-récursion fonctionnel.

## Voie recommandée (session FUTURE, contexte frais)

1. Vérifier si une PR upstream existe sur `NousResearch/hermes-agent` — chercher
   `cycle detection delegate_task`, `max_tokens_per_child`. Si oui : utiliser la PR au lieu de
   patcher.
2. Sinon : ouvrir une PR upstream — c'est la voie propre (survit à `hermes update`, maintenue par
   la communauté). Le patch sera similaire à celui tenté, mais dans une branche git dédiée avec
   commits atomiques + tests A/B.
3. Si PR impossible : patcher localement avec `git checkout -b patch-delegate-cycle`, documenter la
   procédure de rejeu après chaque `hermes update` dans un fichier `patches_locaux.md` à la racine
   de `hermes_install`.

## Prérequis

- Session fraîche (contexte < 30 %).
- Pas d'autre chantier en cours.
- Lire d'abord `patches_abandonnes.md` et `patch_repo_plan.md` (ce fichier).

## Contraintes

- Ne pas relancer ce chantier dans une session où d'autres choses sont en cours.

## Références

- `patches_abandonnes.md` — objectif initial, raison de l'abandon, alternatives retenues.
- `snapshot/pre_patch_abandonne_20260917/` — sauvegardes pré-patch de
  `delegate_tool.py` et `delegate_tool_config.py` (41 710 o et 30 800 o).
- Skill `hermes-operations`, section « Masque récursif — état » — bornes effectives actuelles et ce
  qui manque (budget tokens par sous-agent, détection de cycle, aucun hook d'interception A2A).
