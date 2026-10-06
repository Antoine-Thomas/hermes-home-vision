---
title: "NVIDIA Stack"
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [hermes, llm, gpu]
sources: [raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md]
confidence: high
contested: true
contradictions: [free-openrouter, openrouter]
---

# NVIDIA Stack

Le `nvidia-stack` constitue un étage de repli gratuit basé sur les modèles NVIDIA (ex. `nvidia/nemotron-3-super-120b-a12b`). Il est invoqué après `eco` dans la chaîne de repli. Voir [[fallback-chain]], [[hermes-agent]], [[omniroute]] et [[deepseek-flash]].

## Contradiction notee le 2026-10-06

Cette page place `nvidia-stack` juste apres `eco` (« invoque apres eco »), d'apres
`raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md`
(etat du 22/09/2026 avant 15:27) et l'ordre du repo (`aac90d5`). [[free-openrouter]]
et [[openrouter]] affirment au contraire que `free-openrouter` est le deuxieme
etage. La note source `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`
(22/09 15:27) tranche : `eco` -> `free-openrouter` (2e) -> `nvidia-stack` (3e) ->
`deepseek-flash`. Les deux positions sont conservees, sans reecriture. Voir
[[fallback-chain]] et `contradictions.md`.
