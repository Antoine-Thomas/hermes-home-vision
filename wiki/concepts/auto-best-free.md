---
title: Auto-Best-Free
created: 2026-09-22
updated: 2026-10-06
type: concept
tags: [hermes, llm]
sources: [raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md]
confidence: high
contested: true
contradictions: [auto-best-reasoning, primary-model, hermes-config, fallback-chain]
---

# Auto-Best-Free

Le modèle `auto/best-free` était configuré comme primary, mais il ne répond jamais (400/502). La chaîne de repli passe donc directement à `eco` (premier étage gratuit) puis aux niveaux restants. Voir [[auto-best-reasoning]] pour le modèle principal fonctionnel et [[fallback-chain]] pour la structure complète.

## Contradiction notee le 2026-10-06 (modele principal fonctionnel)

Cette page designe [[auto-best-reasoning]] comme « le modele principal fonctionnel ».
Or [[auto-best-reasoning]] affirme avoir ete ecarte de la chaine le 22/09/2026 et
n'etre pas le modele principal, tandis que [[primary-model]], [[hermes-config]] et
[[fallback-chain]] donnent [[eco]] en primaire. La note source
`raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`
(22/09 15:27) donne raison a cette page (`Primary: auto/best-reasoning (via
omniroute)`) ; le releve direct de `config.yaml` le 2026-10-06 donne depuis
`model.default: deepseek-flash`.

Arbitrage : tranche le 2026-10-06 par la source — primaire `auto/best-reasoning`
au 22/09 15:27, `deepseek-flash` au 2026-10-06. Les affirmations « primaire = `eco` »
de [[primary-model]] et [[hermes-config]] sont perimees. Les deux positions restent
conservees ici, sans reecriture. Registre : `contradictions.md`.
