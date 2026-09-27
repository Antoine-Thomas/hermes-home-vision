---
title: Laya ONNX Windows CPU
created: 2026-09-27
updated: 2026-09-27
type: concept
tags: [jev, model, windows, decision, cout]
sources: []
confidence: high
---

# Laya ONNX Windows CPU

Laya est un modèle de décision typée non autorégressif (ModernBERT-large + tête typée, 421 M
paramètres, Apache-2.0, Convai Innovations). L'export `mariojcr/laya-onnx` place encodeur et tête
dans **un seul graphe ONNX** : onnxruntime + tokenizers suffisent, **aucun PyTorch**. Installé et
mesuré le 27/09/2026 sur la machine de Thomas : c'est le **fallback local gratuit de [[jev]]**.
Voir [[hermes-agent]].

## Ce que ça remplace

| | Jev ([[omniroute]]) | Laya ONNX local |
| --- | --- | --- |
| Type | service distant (OpenRouter) | graphe local, hors ligne |
| Latence | 0,50 s (aller-retour réseau) | **190 ms** par décision |
| Coût | ~1,4 × 10⁻⁵ $ / appel | **0 $** |
| Primitives | `noul`, `choice`, `score` | `noul`, `choice`, `score` |
| Contexte | 512 tokens (checkpoint anglais) | 512 tokens (anglais) |

Même état, même question `noul` « Does the customer request a refund? » : Jev répond 0,99,
Laya 0,9041 calibré (0,9885 brut). Les deux tranchent pareil. Ne pas comparer frontalement les
latences : Jev est un service distant, Laya un forward local.

## Installation et mesure

- venv isolé Python 3.11, `onnxruntime` 1.30.0 + `huggingface_hub` + `tokenizers` + `numpy`
- graphe `english/laya.onnx` : 1,69 Go (F32, opset 18) ; chargement 2,6 s une fois au démarrage
- seuls les fichiers `english/*` sont téléchargés : `multilingual` (mmBERT, 1024 tokens, ~2× plus
  rapide) et `typed-decisions` pèsent ~3 Go de plus

| Cas | tokens | latence médiane |
| --- | --- | --- |
| 1 question `noul` | 83 | 190 ms |
| 2 questions | 85 | 380 ms |
| 4 questions (lot) | 96 | 793 ms (~200 ms/décision) |

Cible tenue : moins de 500 ms par décision, sans GPU. Points qui coûtent du temps :
le prompt doit être **recopié à l'identique** de `laya/common.py::build_sequence` (tokenisation
`add_special_tokens=False`, options tronquées à 48 tokens, état tronqué à droite), la température
`temperature_by_options` s'applique **avant** le softmax (clamp [0,5 ; 5]), et `intra_op_num_threads`
doit rester à 6-10 : au-delà des 12 threads logiques la latence s'effondre (2 120 ms à 24 threads).

## Livrables

- Skill `laya-onnx-windows` (catégorie `mlops`) : `scripts/laya_onnx.py` = runtime complet
  (construction du prompt, inférence, post-traitement), auto-testé en `--self-test`.
- Documentation détaillée : doc SiYuan « Laya ONNX Windows CPU - 27-09-2026 »
  (notebook *Infrastructure — Providers LLM*).

## Questions ouvertes

- Parité exacte avec le SDK PyTorch **non vérifiée** : l'export ne publie aucune fixture de parité
  et torch n'était pas installé. Les sorties collent aux valeurs annoncées par le README Laya.
- Faut-il charger `laya-multilingual` (100+ langues, ~2× plus rapide) pour les états non anglais ?
- Le checkpoint anglais peut suivre ses propres labels sur `noul` et répondre « non » à une entrée
  clairement positive : à vérifier sur les données propres avant de router une décision dessus.

## Concepts liés

Voir [[jev]] (la primitive payante dont Laya est le repli gratuit), [[hermes-agent]] et
[[omniroute]].
