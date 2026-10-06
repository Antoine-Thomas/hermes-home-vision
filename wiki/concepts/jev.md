---
title: Jev
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [hermes]
sources: []
confidence: high
contested: true
contradictions: [laya-onnx-windows]
---

# Jev

Jev est le skill TypeSafe intégré à Hermes pour trancher les choix rapides. Trois
primitives : `noul` (poser un jugement), `choice` (trancher entre N options),
`score` (noter une option). Latence 0,316 s (mesuré le 26/09/2026), coût ~0,0000146 $ par appel (soit 1,46e-5 $). Limite : score sur 10 niveaux maximum. Statut intégration backend (au 26/09/2026) : NON intégré au backend 9119 — JEV n'est appelé que par des scripts explicites (aucun hook/middleware automatique). Correctifs skills associés : commit `5fa0234`. Voir
[[hermes-agent]] et [[omniroute]].

## Où Jev tranche dans l'écosystème

| Service | Port | Type de choix | Exemples |
|---|---|---|---|
| Backend Hermes | 9119 | Opérationnel (modèle, route, run) | eco vs nvidia-stack, retenter un run |
| RAG index 2ᵉ cerveau | 8200 | Classification, rattachement | quel notebook SiYuan, créer ou réutiliser une page |
| Wiki (hébergé dans SiYuan) | 6806 | Routage documentaire | archiver, dédupliquer |

Règle : 2 à 5 options, critères objectifs, choix récurrent.

## Où Jev ne tranche PAS

## Fallback local (exploré)
Exploré le 27/09, éliminé car Core ML/ANE Apple uniquement, incompatible Windows.

- Questions ouvertes (recherche, diagnostic, création)
- Plus de 5 options
- Choix sans critères clairs
- Décisions à impact global (config.yaml, changement de provider)

## Exemple d'appel

```python
from jev_helper import choice
decision = choice(
    question="Quel modèle en primaire ?",
    options=["eco", "nvidia-stack", "free-openrouter"],
    criteria=["gratuit", "stable sur gros prompt", "latence < 30 s"],
)
# → {"choice": "eco", "reason": "...", "confidence": "high"}
```

Voir [[fallback-chain]], [[primary-model]], [[hermes-agent]].

## Contradiction notee le 2026-10-06 (latence)

Cette page releve **0,316 s** par appel (mesure du 26/09/2026). [[laya-onnx-windows]]
retient **0,50 s** (« aller-retour reseau », 27/09/2026). Deux valeurs differentes
pour le meme objet ; l'ecart tient vraisemblablement au protocole (mesure locale vs
aller-retour incluant le reseau) et reste a arbitrer. Les deux positions sont
conservees. Registre : `contradictions.md`.
