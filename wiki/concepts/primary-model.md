---
title: "Modele principal"
created: 2026-09-22
updated: 2026-09-22
type: concept
tags: [model, hermes]
sources: [raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md]
confidence: high
---

# Modele principal

Le modèle principal est le premier à répondre à une requête. Depuis la décision
du 22/09/2026, c'est [[eco]] : `model.default: eco` avec
`model.provider: omniroute`, une route gratuite mesurée saine, y compris sur un
prompt de grande taille. `auto/best-reasoning` n'est **pas** le modèle principal :
l'alias est payant et a été écarté de la chaîne, voir [[auto-best-reasoning]]. Le
principal peut être indisponible (par exemple `auto/best-free`, actuellement hors
service) et bascule alors sur [[nvidia-stack]], puis [[free-openrouter]], et
[[deepseek-flash]] en dernier recours payant. Voir aussi [[fallback-chain]] et
[[hermes-agent]].