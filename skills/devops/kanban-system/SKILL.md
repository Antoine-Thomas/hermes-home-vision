---
name: kanban-system
description: "Kanban multi-agent: orchestration, worker lifecycle et revue des handoffs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration]
    category: devops
    created: "2026-09-10"
    umbrella_of: [kanban-orchestrator, kanban-worker, sdlc-review]
---

# Kanban System

Orchestration, execution et revue dans Hermes Kanban. Le lifecycle de base est auto-injecte via `KANBAN_GUIDANCE` — ce skill est le playbook approfondi.

## Profiles — decouverte obligatoire

Pas de roster par defaut. Avant fan-out, decouvrir les profils existants :

```bash
hermes profile list
cat ~/.config/hermes/profiles.json  # ou AppData/Local/hermes
```

Un assignee inconnu reste bloque en `ready` sans erreur.

## When to Use

- **Orchestrator** : repartir le travail sans l'executer soi-meme
- **Worker** : traiter une carte kanban, tenant isole, workspace ephemere
- **SDLC Review** : verifier un handoff et router le resultat (merge/reject/rework)

## Orchestrator — anti-tentation et decomposition

- **Decomposer, ne pas executer** — creer des cartes via `kanban_create`, ne pas faire le travail.
- Fan-out : 1 carte = 1 livrable verifiable, assignee existant, deps explicites.
- Goal-mode cards : workers persistants, heartbeat, stuck detection.

Voir `references/kanban-orchestrator.md` pour le playbook complet, les patterns et la reprise des workers bloques.

## Worker — isolation et execution

- Workspace ephemere par carte, tenant isole.
- Claimer uniquement ses cartes, bloquer avec une raison repondable.
- Heartbeats utiles, retry scenarios, notification routing.
- CLI fallback pour scripting : `hermes kanban claim/list/complete`.

Voir `references/kanban-worker.md` pour les good shapes de summary/metadata et les pitfalls.

## SDLC Review — verification des handoffs

Lenses : tests, securite, dette, specs. Procedure `sdlc-review` pour valider les criteres d'acceptation avant merge.

Voir `references/sdlc-review.md`.

## Pitfalls communs

- Assignee inexistant -> carte bloquee silencieusement.
- Ne pas contourner le board pour "aller plus vite".
- Toujours verifier l'etat du worker avant de re-assigner.

## References

- `references/kanban-orchestrator.md` — decomposition playbook (214l)
- `references/kanban-worker.md` — worker pitfalls et edge cases (193l)
- `references/sdlc-review.md` — review des handoffs (181l)
