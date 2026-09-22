---
title: "Connexion fournisseur"
created: 2026-09-22
updated: 2026-09-22
type: concept
tags: [provider, omniroute]
sources: [raw/notes/siyuan-20260922-openrouter-dans-omniroute-combo-free-openrouter.md]
confidence: high
---

# Connexion fournisseur

Dans OmniRoute, une connexion fournisseur definit la facon dont un service d'IA
externe est atteint. Elle requiert un nom de fournisseur, une URL, une cle
d'API et un indicateur d'activation. Le systeme de combos s'appuie sur cette
connexion pour selectionner les modeles ; une defaillance (cle absente, erreur
403) peut faire planter le demon. Voir [[omniroute]] et [[openrouter]].