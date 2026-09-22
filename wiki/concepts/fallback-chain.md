---
title: "Chaine de repli"
created: 2026-09-22
updated: 2026-09-22
type: concept
tags: [hermes]
sources: [raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
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