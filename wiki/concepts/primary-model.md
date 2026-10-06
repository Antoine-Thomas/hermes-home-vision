---
title: "Modele principal"
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [model, hermes]
sources: [raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md]
confidence: high
contested: true
contradictions: [free-openrouter, openrouter, auto-best-reasoning, auto-best-free]
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

## Contradiction notee le 2026-10-06

La phrase « bascule alors sur [[nvidia-stack]], puis [[free-openrouter]] » reprend
l'ordre du 22/09/2026 avant 15:27 (repo `aac90d5`, restauration de 13:58). La note
source `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`
(22/09 15:27) place au contraire [[free-openrouter]] en 2e etage et `nvidia-stack`
en 3e. Les deux positions sont conservees. Voir [[fallback-chain]] et
`contradictions.md`.

## Contradiction notee le 2026-10-06 (identite du primaire)

Cette page affirme que le primaire est [[eco]] depuis la decision du 22/09/2026.
La note qu'elle cite
(`raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md`)
ne dit pas cela : au 22/09 14:24, `model.default` valait `auto/best-free`.
[[auto-best-reasoning]] se dit « ecarte de la chaine » et [[auto-best-free]]
designe `auto/best-reasoning` comme « le modele principal fonctionnel ».

- Position A (cette page, [[hermes-config]], [[fallback-chain]]) : primaire = `eco`.
- Position B ([[auto-best-free]]) : primaire = `auto/best-reasoning`.
- Position C ([[auto-best-reasoning]]) : alias payant, ecarte, pas le primaire.
- Position D (note `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`,
  22/09 15:27 : `Primary: auto/best-reasoning (via omniroute)` relu sur
  `hermes fallback list`, `state.db` rowid 1001).
- Position E (releve direct de `config.yaml` le 2026-10-06) : `model.default:
  deepseek-flash`, `model.provider: deepseek`.

Arbitrage : tranche le 2026-10-06 par la source — les deux references les plus
recentes donnent `auto/best-reasoning` (22/09 15:27) puis `deepseek-flash`
(2026-10-06) en primaire. L'affirmation « primaire = `eco` » ne tient donc pas a
ces dates. Les deux positions restent ecrites ici, sans reecriture.
Registre : `contradictions.md`.
