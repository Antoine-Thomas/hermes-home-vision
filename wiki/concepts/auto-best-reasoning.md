---
title: Auto/best-reasoning
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [jev, hermes]
sources: [raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md, raw/notes/siyuan-20260922-openrouter-dans-omniroute-combo-free-openrouter.md, raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md, raw/notes/siyuan-20260922-reparation-omniroute-maj-hermes-fde4997f-22-09-2.md, raw/notes/siyuan-20260922-restauration-providers-depuis-repo-22-09-2026.md]
confidence: high
contested: true
contradictions: [primary-model, hermes-config, fallback-chain, auto-best-free]
---

# Auto/best-reasoning

`auto/best-reasoning` est un alias de raisonnement d'[[omniroute]], résolu vers des modèles Anthropic **payants** : `claude-opus-5`, puis `claude-sonnet-5`, via OpenRouter. Il a été écarté de la chaîne de repli le 22/09/2026 : il n'est pas le modèle principal, voir [[primary-model]] et [[fallback-chain]].

## Mesure du 22 septembre 2026

- Résolution vers `openrouter/anthropic/claude-opus-5`, puis
  `anthropic/claude-sonnet-5` : modèles **payants** servis par OpenRouter,
  environ 274 jetons d'entrée par tour.
- Une seule requête déclenche plus de trente tentatives journalisées
  `virtual-auto-smart-<n>-<provider>`.
- Un tir sur trois part en timeout après 120 secondes.
- L'alias ne figure plus dans la chaîne : le modèle principal gratuit est
  [[eco]].

## Contradiction notee le 2026-10-06 (role du primaire)

Cette page affirme que l'alias a ete « ecarte de la chaine de repli le 22/09/2026 »
et qu'« il n'est pas le modele principal ». [[primary-model]] et [[hermes-config]]
donnent [[eco]] en primaire ; [[auto-best-free]] designe au contraire
`auto/best-reasoning` comme « le modele principal fonctionnel ». La note source que
cette page cite (`raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`,
22/09 15:27) affiche elle-meme `Primary: auto/best-reasoning (via omniroute)` :
cette page contredit donc une de ses propres sources. Releve direct de `config.yaml`
le 2026-10-06 : `model.default: deepseek-flash`, `model.provider: deepseek`.

Arbitrage : tranche le 2026-10-06 par la source — au 22/09 15:27 le primaire etait
`auto/best-reasoning` (l'alias n'etait donc pas « ecarte » ce jour-la) ; depuis, le
primaire est `deepseek-flash`. Les deux positions restent conservees ici, sans
reecriture. Registre : `contradictions.md`.
