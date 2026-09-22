---
title: "Hermes Agent"
created: 2026-09-22
updated: 2026-09-22
type: entity
tags: [hermes]
sources: [raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
---

# Hermes Agent

Hermes Agent (v0.21.4) est l'agent IA local central : il achemine les requetes
via une chaine de repli configurable, s'integre a OmniRoute et a SiYuan, et
tourne sur un GPU local RTX 3070 Ti. Il assure la continuite de service en
basant automatiquement d'un modele a l'autre lorsque le principal devient
indisponible. Voir [[fallback-chain]] et [[omniroute]].