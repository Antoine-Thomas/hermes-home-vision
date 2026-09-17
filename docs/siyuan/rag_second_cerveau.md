# rag-second-cerveau

> **Statut** : actif — opérationnel depuis le 15/09/2026
> **Dernière mise à jour** : 15/09/2026

## Fait

Le second cerveau est interrogeable : les documents SiYuan, les skills, les scripts du volet 4 et le
dépôt WordPress local sont indexés, et une question posée en langage naturel retrouve la décision,
le seuil ou la commande correspondante.

- Index : `%LOCALAPPDATA%\hermes\data\rag\` — `chercher.py`, `indexer.py`, `index.faiss`,
  `chunks.jsonl`, `manifeste.json`, venv dédié.
- Modèle d'embedding : `intfloat/multilingual-e5-base` (multilingue FR/EN, CPU), fragments de
  900 caractères, préfixes `passage:` / `query:` obligatoires.
- Recherche **hybride** : vectoriel + lexical (BM25), fusion RRF, plus une expansion de requête par
  synonymes du métier. Le vectoriel seul ratait le jargon (« lèvres », « connector-11 », « 45 s »).
- État : **2047 fragments** — SiYuan 169 · skills 1146 · scripts v4 643 · WordPress 89.
- Réindexation **automatique** chaque nuit à 03h00 (tâche `Hermes - Reindex RAG`, journal
  `reindex.log`) ; elle ne fait rien si le noyau SiYuan est arrêté.

Test réel du 15/09/2026, quatre requêtes passées par le seul index :

| Question | Source de tête | Score |
|---|---|---|
| Comment relancer LatentSync si la cadence tombe à 45 s/lot ? | SiYuan `video-ia / Branche A — Pièges` | cos 0,873 |
| Seuil d'alerte sur les fantômes des lèvres ? | SiYuan `video-ia / Contrôle qualité vidéo` | cos 0,867 |
| Où est le lexique de diction et comment l'utiliser ? | SiYuan `hermes-skills / Lexique de diction` | cos 0,846 |
| Comment créer un skill Hermes ? | skill `productivity/recherche-skills-officiels` | cos 0,911 |

## Reste à faire

- Enrichir l'index au fil des volets : chaque nouveau document SiYuan ou skill est pris en compte à
  la réindexation suivante, sans autre action.
- Le catalogue du Skills Hub en ligne n'est **pas** dans l'index (il change trop souvent) : il se
  consulte avec `hermes skills search`.

## Pièges

- **L'index ne se met pas à jour tout seul** dans la journée : la tâche planifiée passe à 03h00.
  Pour un document écrit dans la soirée, lancer `indexer.py` à la main si besoin.
- Sans le noyau SiYuan, la source `siyuan` revient vide **en silence** : le manifeste est le
  contrôle (comparer le nombre de fragments par source).
- Les préfixes e5 (`passage:` à l'indexation, `query:` à la recherche) sont obligatoires : sans eux
  la pertinence s'effondre, sans qu'aucune erreur ne soit levée.
- Une réindexation complète prend environ 5 minutes (CPU) : ce n'est pas un test à lancer en boucle.
- Gradation de lecture : au-dessus de 0,85 la source est fiable ; entre 0,75 et 0,85, lire le
  fragment avant de s'en servir.

## Commandes

```
cd "%LOCALAPPDATA%\hermes\data\rag"

# chercher (3 resultats)
venv\Scripts\python.exe chercher.py "<question>" -k 3

# chercher avec les scores
venv\Scripts\python.exe chercher.py "<question>" -k 3 -v

# reindexer a la main
venv\Scripts\python.exe indexer.py

# journal de la reindexation automatique
type reindex.log
```
