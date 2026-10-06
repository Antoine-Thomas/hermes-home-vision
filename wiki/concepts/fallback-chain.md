---
title: "Chaine de repli"
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [hermes]
sources: [raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
contested: true
contradictions: [free-openrouter, openrouter, auto-best-reasoning, auto-best-free, fallback-providers]
---

# Chaine de repli

La chaîne de repli est la liste ordonnée des modèles que Hermes sollicite
lorsque le modèle principal devient indisponible. Depuis la décision du
22/09/2026, elle compte quatre niveaux, du primaire à l'ultime recours :
[[eco]] (primaire, gratuit) -> [[nvidia-stack]] -> [[free-openrouter]] ->
[[deepseek-flash]] (dernier recours payant). `auto/best-reasoning` n'y figure
plus : l'alias est payant et a été écarté, voir [[auto-best-reasoning]]. La
bascule est automatique et transparente, sans intervention manuelle. Voir aussi
[[hermes-agent]] et [[primary-model]].

## Contradiction notee le 2026-10-06 (ordre des etages 2 et 3)

Cette page place `nvidia-stack` en 2e et `free-openrouter` en 3e. [[free-openrouter]]
et [[openrouter]] donnent l'ordre inverse (`free-openrouter` juste apres `eco`).

- Position A (cette page, plus [[primary-model]] et [[nvidia-stack]]) : `eco` ->
  `nvidia-stack` -> `free-openrouter` -> `deepseek-flash`. C'est l'ordre du repo
  avant le 22/09/2026 (commit `aac90d5` « repli gratuit nvidia-stack avant
  deepseek-flash ») et de la note de restauration du 22/09 13:58.
- Position B ([[free-openrouter]], [[openrouter]], note source
  `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`,
  22/09 15:27) : `eco` -> `free-openrouter` (2e) -> `nvidia-stack` (3e) ->
  `deepseek-flash`, ordre confirme par les latences mesurees (7,3 / 9,8 / 23,2 /
  6,5 s) et les lignes `state.db`.

Arbitrage : la source la plus recente (22/09 15:27) donne Position B. Les deux
positions sont conservees ici, sans reecriture. Registre : `contradictions.md`.

## Contradictions notees le 2026-10-06 (niveaux, primaire, composition)

- **Niveau du primaire** : cette page compte « quatre niveaux » et place [[eco]] en
  primaire. La note `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`
  (titre « 5 niveaux ») distingue un primaire (`auto/best-reasoning`, relu sur
  `hermes fallback list` le 22/09 15:27) et quatre entrees de repli (`eco`,
  `free-openrouter`, `nvidia-stack`, `deepseek-flash`). [[auto-best-free]] place aussi
  le primaire sur `auto/best-reasoning` ; [[primary-model]] et [[hermes-config]] le
  placent sur `eco`. Relevé direct de `config.yaml` le 2026-10-06 : `model.default:
  deepseek-flash`, `model.provider: deepseek`.
- **Composition de `fallback_providers`** : [[fallback-providers]] ne liste que
  `omniroute/nvidia-stack` et `deepseek/deepseek-flash`. Le relevé du 2026-10-06 donne
  trois couples : `omniroute/free-openrouter` -> `omniroute/nvidia-stack` ->
  `deepseek/deepseek-flash` (pas de `eco`).

Arbitrage : tranche le 2026-10-06 par la source la plus recente — l'ordre
`free-openrouter` avant `nvidia-stack` est confirme (note du 22/09 15:27 et relevé
direct concordent), `eco` ne figure plus dans `fallback_providers` a cette date, et
le primaire n'est plus `eco` (`auto/best-reasoning` au 22/09 15:27, `deepseek-flash`
au 2026-10-06). Les positions de cette page restent ecrites telles quelles.
Registre : `contradictions.md`.
