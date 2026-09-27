---
name: laya-onnx-windows
description: Use when running Laya ONNX decisions on CPU without torch.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [laya, onnx, onnxruntime, decisions, noul, choice, score, cpu, no-torch]
    related_skills: [typesafe-ai, llm-ops]
---

# Laya en ONNX sur CPU, sans PyTorch

Laya = modele de decision typee non autoregressif (ModernBERT-large + tete typee, 421M,
Apache-2.0). L'export `mariojcr/laya-onnx` met encodeur + tete dans un seul graphe ONNX :
onnxruntime + tokenizers suffisent, aucun torch a installer. Mesure : **~190-200 ms par
decision** sur un i7-8700, 1,69 Go de RAM pour le graphe (details :
`references/mesures-2026-09.md`).

## When to use

- Executer Laya en local (hors ligne, cout zero) sans installer PyTorch ni le SDK `laya`.
- Donner a du code une primitive de decision typee : `noul` (oui/non), `choice` (une option
  parmi N), `score` (position sur une echelle ordonnee).
- Remplacer/comparer avec JEV (voir la skill `typesafe-ai`) sur le meme cas.
- Charger un des trois checkpoints exportes : `english` (512 ctx), `multilingual` (mmBERT,
  1024 ctx, ~2x plus rapide), `typed-decisions` (1024 ctx, meilleur sur 4 workflows types).

## Installation (recette verifiee Windows, 27-09-2026)

```bash
# 1. venv isole — ne jamais installer dans le venv d'Hermes
python -m venv laya-win-venv                  # Python 3.11
./laya-win-venv/Scripts/python.exe -m pip install onnxruntime huggingface_hub tokenizers numpy

# 2. telecharger UNIQUEMENT le checkpoint voulu (~1,7 Go anglais, ~3 Go de plus sinon)
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("mariojcr/laya-onnx", allow_patterns=["english/*"], local_dir="laya-onnx")
PY
```

Versions mesurees : onnxruntime 1.30.0, tokenizers 0.23.2, huggingface_hub 1.33.0, numpy 2.4.6.
Chargement de la session : ~2,6 s, une seule fois au demarrage.

## Contrat du graphe

| Entree | Type | Shape |
| --- | --- | --- |
| `input_ids` | int64 | [n, L] |
| `attention_mask` | int64 | [n, L] |
| `marker_pos` | int64 | [n, k] — position du `[MASK]` de chaque option |
| `marker_mask` | bool | [n, k] — quels marqueurs sont reels |
| `qtype` | int64 | [n] — 0=choice, 1=score, 2=noul |

Sorties : `logits` float32 [n, k] (options masquees a -1e4), `act_logits` float32 [n, 2].
`rl_agent_config.json` porte `max_len`, `head_max_len`, `temperature` (par type) et
`temperature_by_options` (par bucket).

## Construire la sequence — le point critique

Format : `[CLS] <type> question: <instructions> [SEP] [MASK] opt0 [MASK] opt1 ... [SEP] <state> [SEP]`

Le prompt doit etre **recopie a l'identique** de `laya/common.py::build_sequence` :

- tokeniser avec `add_special_tokens=False` et poser `[CLS]`/`[SEP]` a la main — sinon le
  post-processeur du `tokenizer.json` en ajoute une seconde fois ;
- en-tete `"%s question: %s" % (type, instructions)`, tronque a `head_max_len` ;
- chaque option = `" " + texte`, tronquee a **48 tokens**, prefixee du `[MASK]` ;
- si le budget d'options tombe sous 16 tokens, re-tronquer chaque option a
  `max(4, (head_max_len - 16) // k)` ;
- `room = max_len - len(ids) - 1`, etat tronque **a droite** sauf pour un state de type liste
  (conversation : troncature a gauche, sinon on perd le dernier tour) ;
- remplacer le texte du token `[MASK]` par un espace dans l'etat, les instructions et l'option.

Rendu des options par primitive (`render_options`) : `choice` -> `"label: description"` (ou juste
le label si description vide) ; `score` -> `"level %d: desc"` ; `noul` -> les deux options sont
`"false: no, the statement does not hold"` et `"true: yes, the statement holds"`.

`scripts/laya_onnx.py` implemente tout ca et se teste seul (`--self-test`).

## Post-traitement

```
t_scale = temperature_by_options.get("%s:%s" % (nom_du_type, bucket(k)), temperature[qtype])
t_scale = clamp(t_scale, 0.5, 5.0)            # un T < 1 durcit au lieu d'adoucir
z = logits[q, :k] / t_scale ; p = softmax(z)
noul   -> reponse = p[1]                       # P(true), l'ordre est toujours [false, true]
choice -> cle = argmax(p)
score  -> valeur = somme(i * p[i])
```

Bucket : `k <= 2` -> `"2"`, `<= 5` -> `"3-5"`, `<= 10` -> `"6-10"`, sinon `"11+"`.
La calibration compte : sur le cas mesure, `noul` brut 0,9885 -> 0,9041 apres T=1,9834.

## Latence attendue (i7-8700, 12 threads logiques)

| Cas | tokens | mediane |
| --- | --- | --- |
| 1 question noul | 83 | 190 ms |
| 2 questions | 85 | 380 ms |
| 4 questions (lot) | 96 | 793 ms (~200 ms/decision) |

Tokenisation : 2 ms. Repartir les questions d'un meme etat en **un seul appel** (batch sur la
dimension `n`) : on partage le forward au lieu de le payer par question.

## Pitfalls

- **Ne pas surabonner les threads.** `intra_op_num_threads` optimal = 6-10 ; au-dela du nombre
  de threads logiques (12 ici) la latence s'effondre : 1798 ms a 16, 2120 ms a 24 (vs 190 ms).
  Le defaut convient, ne pas « accelerer » en montant les threads.
- **`add_special_tokens=False` obligatoire** : le `tokenizer.json` de ModernBERT porte un
  post-processeur ; sans ce flag les tokens speciaux sont comptes deux fois.
- **L'export ne publie aucune fixture** de parite (`--fixture` n'est ecrit qu'a la demande par
  `export_onnx.py`). Sans torch installe, la parite logits ne peut pas etre verifiee : valider
  sur les sorties annoncees au README Laya (department -> billing) avant de faire confiance.
- **`act_logits` / `act_probability` ne portent pas de signal utilisable** (la carte Laya le
  documente) : ne pas les utiliser comme garde-fou, gater sur `answer_confidence` = `max(p)`.
- **`noul` sur le checkpoint anglais peut suivre ses labels** au lieu de l'etat et repondre
  « non » a une entree clairement positive : verifier sur ses propres donnees ; au besoin poser
  la meme question en `choice` a 2 options neutres.
- **Echelle a 512 tokens** sur le checkpoint anglais : l'etat est tronque a droite.
- Le venv Hermes et `config.yaml` ne doivent jamais etre touches : tout vit dans un venv dedie.

## Files

- `scripts/laya_onnx.py` — runtime complet (construction du prompt, inference, post-traitement) :
  `python laya_onnx.py --onnx-dir <dir> --self-test` rejoue l'exemple du README Laya.
- `references/mesures-2026-09.md` — mesures de reference : latence, sorties du cas README,
  comparaison JEV.
