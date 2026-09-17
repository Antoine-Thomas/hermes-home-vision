---
name: omniroute-suite
description: "OmniRoute compression, cost tracking, and auto-update — requetes compressees, monitoring budget, mises a jour auto."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, windows, macos]
metadata:
  hermes:
    tags: [omniroute, compression, cost-tracking, auto-update]
    category: devops
    created: "2026-09-10"
    umbrella_of: [compression-tokens, omniroute-cost-tracker, omniroute-auto-update]
---

# OmniRoute Suite — Compression, Cost Tracking & Auto-Update

Pipeline de compression OmniRoute, suivi des couts et mises a jour automatiques. Les skills proteges `fallback-intelligent` et `omniroute-gateway` restent independants.

## When to Use

- Reduire les tokens LLM via OmniRoute (`compression-tokens`)
- Suivre / auditer les couts par combo et par modele (`omniroute-cost-tracker`)
- Mettre a jour OmniRoute automatiquement (`omniroute-auto-update`)
- Ne pas utiliser pour `fallback-intelligent` ou `omniroute-gateway` (proteges)

## Compression — points cles

- Auth d'abord : le CLI ment sur les echecs — verifier le header echo.
- Endpoint de compression empilee (stacked) : seul vrai endpoint.
- RTK ne touche que `role="tool"` messages.
- Verifier avec le header de reponse echoe.
- Preview endpoint : sur, sans burn de rate-limit.
- Combos : adresser par BARE NAME, prober les membres (modeles morts = 1er hop perdu).
- Binding OmniRoute en loopback seul, wiring dans Hermes.

Voir `references/compression-tokens.md` pour la procedure complete (241l, decoupee en refs par H2).

## Cost Tracker

Contexte, etapes et pieges du suivi des couts OmniRoute.

Voir `references/omniroute-cost-tracker.md` (32l).

## Auto-Update

Mises a jour automatiques d'OmniRoute via GitHub releases. Cron job de veille + script de mise a jour automatique.

Voir `references/omniroute-auto-update.md` (72l).

## Proteges — non inclus

- `fallback-intelligent` (protege, 130l, 2026-09-08) — chaine de repli gratuit->payant
- `omniroute-gateway` (protege, 107l, 2026-09-08) — reordonnancement des combos

## References

- `references/compression-tokens.md` — verbatim from `devops/compression-tokens/` (archived 2026-09-10)
- `references/omniroute-cost-tracker.md` — verbatim from `devops/omniroute-cost-tracker/` (archived 2026-09-10)
- `references/omniroute-auto-update.md` — verbatim from `omniroute-auto-update/` (archived 2026-09-10)
