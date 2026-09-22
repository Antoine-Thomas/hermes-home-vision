---
title: Free-openrouter
created: 2026-09-22
updated: 2026-09-22
type: concept
tags: [omniroute, provider]
sources: [raw/notes/siyuan-20260922-openrouter-dans-omniroute-combo-free-openrouter.md, raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
---

# Free-openrouter

Le combo free-openrouter a été ajouté à OmniRoute le 22‑09‑2026. Il contient, en ordre de priorité, les modèles suivants :
1. `openrouter/nvidia/nemotron-3-super-120b-a12b:free`
2. `openrouter/cohere/north-mini-code:free`
3. `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free`
Lorsqu'il est appelé, le combo retourne le premier modèle disponible, généralement le modèle Cohere puis le modèle NVIDIA. Il constitue le deuxième étage de la chaîne de repli après eco. Voir [[openrouter]] et [[omniroute]].
