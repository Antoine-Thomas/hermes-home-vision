---
title: "Fallback Providers"
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [hermes, llm]
sources: [raw/notes/siyuan-20260922-reparation-omniroute-maj-hermes-fde4997f-22-09-2.md, raw/notes/siyuan-20260922-restauration-providers-depuis-repo-22-09-2026.md]
confidence: high
contested: true
contradictions: [fallback-chain, free-openrouter, eco]
---

# Fallback Providers

La configuration `fallback_providers` spécifie les couples provider/modèle utilisés en cas d'échec du primaire. Elle inclut `omniroute/nvidia-stack` et `deepseek/deepseek-flash`. Voir [[fallback-chain]], [[hermes-agent]], [[omniroute]], [[nvidia-stack]] et [[deepseek-flash]].

## Contradiction notee le 2026-10-06 (composition de `fallback_providers`)

Cette page ne cite que deux couples (`omniroute/nvidia-stack`,
`deepseek/deepseek-flash`), d'apres la note de restauration du 22/09 13:58.
[[fallback-chain]] et [[free-openrouter]] decrivent au moins quatre etages dont
[[eco]] et `free-openrouter`. Relevé direct de `config.yaml` le 2026-10-06 :
`fallback_providers` = `omniroute/free-openrouter` -> `omniroute/nvidia-stack` ->
`deepseek/deepseek-flash` (trois couples, pas de `eco`).

Arbitrage : tranche le 2026-10-06 par la source la plus recente — la liste de cette
page est perimee ; `free-openrouter` precede `nvidia-stack`. Les deux positions
restent conservees, sans reecriture. Registre : `contradictions.md`.
