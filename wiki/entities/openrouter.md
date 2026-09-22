---
title: OpenRouter
created: 2026-09-22
updated: 2026-09-22
type: entity
tags: [omniroute, provider]
sources: [raw/notes/siyuan-20260922-openrouter-dans-omniroute-combo-free-openrouter.md, raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
---

# OpenRouter

OpenRouter est un provider de modèles accessible via une clé API stockée dans `.env`. Dans la configuration locale, une connexion OpenRouter a été créée dans OmniRoute permettant d'accéder à des modèles gratuits tels que `nvidia/nemotron-3-super-120b-a12b:free`, `cohere/north-mini-code:free` et `nvidia/nemotron-3-ultra-550b-a55b:free`. Ces modèles sont regroupés dans le combo **free-openrouter** qui occupe le deuxième étage de la chaîne de repli Hermes. Voir [[fallback-chain]] et [[omniroute]].
