---
title: Free-openrouter
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [omniroute, provider]
sources: [raw/notes/siyuan-20260922-openrouter-dans-omniroute-combo-free-openrouter.md, raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
contested: true
contradictions: [fallback-chain, nvidia-stack, primary-model, eco, fallback-providers]
---

# Free-openrouter

Le combo free-openrouter a été ajouté à OmniRoute le 22‑09‑2026. Il contient, en ordre de priorité, les modèles suivants :
1. `openrouter/nvidia/nemotron-3-super-120b-a12b:free`
2. `openrouter/cohere/north-mini-code:free`
3. `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`
Lorsqu'il est appelé, le combo retourne le premier modèle disponible, généralement le modèle Cohere puis le modèle NVIDIA. Il constitue le deuxième étage de la chaîne de repli après eco. Voir [[openrouter]] et [[omniroute]].

## Contradictions notees le 2026-10-06

- **Ordre des etages** : cette page donne `free-openrouter` en 2e etage (conforme a
  `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`,
  22/09 15:27 : « 2. free-openrouter <- NOUVEAU », latence mesuree 9,8 s, ligne
  `state.db` rowid 1003). [[fallback-chain]], [[nvidia-stack]] et [[primary-model]]
  donnent l'ordre inverse (`eco` -> `nvidia-stack` -> `free-openrouter`), herite du
  repo avant le 22/09 (`aac90d5`) et de la restauration de 13:58. Les deux positions
  sont conservees ; arbitrage : la source la plus recente.
- **Composition du combo** : cette page liste 3 membres (nemotron-3-super-120b:free,
  north-mini-code:free, nemotron-3-ultra-550b-a55b:free) ; [[eco]] affirme en etre un
  membre, alors que la meme note source recense `eco` comme un combo distinct de
  3 membres. Les deux positions sont conservees.
- **Composition de `fallback_providers`** : [[fallback-providers]] ne liste pas
  `free-openrouter` (deux couples seulement, d'apres la note de restauration du
  22/09 13:58). Relevé direct de `config.yaml` le 2026-10-06 : `fallback_providers`
  = `omniroute/free-openrouter` -> `omniroute/nvidia-stack` ->
  `deepseek/deepseek-flash` ; le combo est donc bien present, en 1er etage de repli
  (il n'y a plus de `eco` devant lui a cette date). Arbitrage : la source la plus
  recente donne raison a cette page.
