---
title: Eco
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [model, hermes]
sources: [raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
contested: true
contradictions: [free-openrouter, fallback-providers]
---

# Eco

Eco est un modele de palier gratuit servi via OmniRoute, utilise comme premier
etage de la chaine de repli. Il offre une latence raisonnable (environ 7 a 10 s)
et ne coute rien a l'usage. Il figure comme membre du combo `free-openrouter`.
Voir [[fallback-chain]] et [[omniroute]].

## Contradiction notee le 2026-10-06

Cette page affirme que `eco` « figure comme membre du combo `free-openrouter` ».
[[free-openrouter]] liste les 3 membres de ce combo (`nvidia/nemotron-3-super-120b-a12b:free`,
`cohere/north-mini-code:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`) et la note
source `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`
recense « `eco` 3, `free-openrouter` 3 membres » : `eco` est un combo distinct, pas
un membre de `free-openrouter`. Les deux positions sont conservees, sans reecriture.
Registre : `contradictions.md`.

## Contradiction notee le 2026-10-06 (presence dans `fallback_providers`)

Cette page presente `eco` comme « premier etage de la chaine de repli », ce que
confirment [[fallback-chain]] et [[free-openrouter]] pour la periode du 22/09.
Mais le relevé direct de `config.yaml` le 2026-10-06 ne trouve pas `eco` dans
`fallback_providers` (`omniroute/free-openrouter`, `omniroute/nvidia-stack`,
`deepseek/deepseek-flash`) et donne `model.default: deepseek-flash`.

Arbitrage : tranche le 2026-10-06 par la source la plus recente — `eco` n'est plus un
etage de `fallback_providers` a cette date. Les deux positions restent conservees,
sans reecriture. Registre : `contradictions.md`.
