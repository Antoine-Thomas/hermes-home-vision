<!-- Mesures de reference, machine : Intel i7-8700 (6 cœurs, 12 threads logiques),
     Windows 11, onnxruntime 1.30.0, CPUExecutionProvider. Releve le 27-09-2026. -->

# Mesures Laya ONNX — 27-09-2026

## Environnement

- Graph : `mariojcr/laya-onnx`, `english/laya.onnx`, 1 688 711 336 o (1,69 Go), F32, opset 18
- Repo sha `aeebb05497cc473360caf4de1653107cf08d6b10`
- venv Python 3.11.9 : onnxruntime 1.30.0, tokenizers 0.23.2, huggingface_hub 1.33.0, numpy 2.4.6
- Chargement de la session ONNX Runtime : 2,6 s
- Tokens speciaux : cls=50281, sep=50282, pad=50283, mask=50284

## Latence

| Cas | n | L | mediane | min |
| --- | --- | --- | --- | --- |
| 1 question noul | 1 | 83 | 190 ms | 178 ms |
| 2 questions noul | 2 | 85 | 380 ms | 377 ms |
| 2 noul + 1 choice + 1 score | 4 | 96 | 793 ms | 765 ms |

Tokenisation + construction du prompt : 2 ms pour les 4 questions.

Effet de `intra_op_num_threads` sur le lot de 4 (L=96) :

| Threads | 0 (defaut) | 8 | 12 | 16 | 20 | 24 |
| --- | --- | --- | --- | --- | --- | --- |
| Lot de 4 | 843 ms | 865 ms | 793 ms | 1798 ms | 1853 ms | 2120 ms |
| 1 noul | 190 ms | 192 ms | 211 ms | 458 ms | 618 ms | 625 ms |

=> optimal 6-10 threads ; au-dela de 12 (threads logiques) effondrement par surabonnement.

## Sorties sur le cas du README Laya

Etat : double facturation + demande de remboursement + menace de resiliation.

| Question | Primitive | Brut (T=1) | Calibre | Attendu README |
| --- | --- | --- | --- | --- |
| refund_requested | noul | 0,9885 | 0,9041 | — |
| churn_risk | noul | 0,9536 | 0,8211 | oui, eleve |
| department | choice k=4 | billing 0,9987 | billing 0,9653 | billing (0,94) |
| urgency | score k=3 | — | 1,44 | — |

Logits bruts du noul : `[-3.0566, 1.3944]` (refund), `[-1.9539, 1.0691]` (churn).
Temperatures appliquees : `noul:2` = 1,9834 ; `choice:3-5` = 1,7602 ; `score:3-5` = 1,2514.

## Comparaison JEV (typesafe/jev-1.13 via OpenRouter)

Meme etat, meme question noul « Does the customer request a refund? » :

| | JEV | Laya ONNX local |
| --- | --- | --- |
| noul | 0,99 | 0,9041 (0,9885 sans calibration) |
| latence | 0,502 s (reseau) | 190 ms |
| cout | 1,38e-05 $ (328 tokens in) | 0 |
| modele servi | `typesafe/jev-1.13-20260917` | graph local |

Ne pas comparer frontalement les latences : JEV est un service distant.

## Parite

Non verifiee contre le SDK PyTorch : l'export ne publie pas de fixture (`--fixture` n'est
produit qu'a la demande) et torch n'etait pas installe. Les sorties ci-dessus collent a celles
annoncees par le README Laya et par la carte du modele (parite annoncee : max |delta logits| 1,8e-6).
