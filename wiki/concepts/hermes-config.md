---
title: "Configuration Hermes"
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [hermes, llm]
sources: [raw/notes/siyuan-20260922-reparation-omniroute-maj-hermes-fde4997f-22-09-2.md]
confidence: high
contested: true
contradictions: [auto-best-reasoning, auto-best-free]
---

# Configuration Hermes

La configuration d'Hermes définit le modèle par défaut (`eco`), le provider (`omniroute`), la chaîne de repli via `fallback_providers`, et le nombre maximal de tentatives (`agent.api_max_retries`). Voir [[hermes-agent]], [[omniroute]], [[fallback-chain]], [[auto-best-reasoning]] et [[deepseek-flash]].

## Contradiction notee le 2026-10-06 (modele par defaut)

Cette page donne `eco` comme modele par defaut. [[auto-best-free]] designe
`auto/best-reasoning` comme le primaire fonctionnel, [[auto-best-reasoning]] se dit
ecarte, et le relevé direct de `config.yaml` le 2026-10-06 donne
`model.default: deepseek-flash` avec `model.provider: deepseek`. La note source
`raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`
(22/09 15:27) affichait `Primary: auto/best-reasoning (via omniroute)` et une chaine
de repli de 4 entrees (`eco`, `free-openrouter`, `nvidia-stack`, `deepseek-flash`).
Seul `agent.api_max_retries: 3` est confirme par le relevé du 2026-10-06.

Arbitrage : tranche le 2026-10-06 par la source la plus recente — `eco` n'est pas le
modele par defaut a cette date. Les deux positions restent conservees, sans
reecriture. Registre : `contradictions.md`.
