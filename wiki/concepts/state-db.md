---
title: "Base d'etat"
created: 2026-09-22
updated: 2026-09-22
type: concept
tags: [hermes]
sources: [raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
---

# Base d'etat

La base d'etat (`state.db`) conserve l'historique d'usage des modeles par
session : quel modele a servi chaque requete, a quel moment, et les details de
facturation associes. Ces donnees servent a auditer le comportement de la
chaine de repli et a diagnostiquer les problemes de latence. Voir
[[hermes-agent]] et [[fallback-chain]].