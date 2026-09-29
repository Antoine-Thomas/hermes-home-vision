# RAG Hybride v1.5 — copie versionnée

Ce dossier est la **copie versionnée de référence** du code du RAG Hybride v1.5
(recherche dense + BM25, fusion RRF, routeur de complexité).

## Source d'exécution (runtime)

Le code réellement exécuté par le serveur RAG reste dans :

```
%LOCALAPPDATA%\hermes\data\rag\
```

Ce chemin est **non versionné** : `data/` est ignoré par le `.gitignore` du dépôt
(ligne `data/`), tout comme les journaux (`*.log`). Les fichiers n'ont pas été
déplacés pour ne pas perturber le serveur RAG en marche (127.0.0.1:8200).

## Fichiers couverts (11)

Coeur :

- `chercher.py` — recherche hybride dense + BM25, fusion RRF, reranking cross-encoder optionnel (désactivé par défaut)
- `routeur_complexite.py` — routeur de complexité (simple → sans RAG, modérée → top-5, complexe → top-20 puis sélection locale de 5)
- `serveur_rag.py` — serveur FastAPI local (importe `chercher.py`, aucune logique de recherche dupliquée)
- `indexer.py` — indexation e5 + manifeste
- `test_phase_b.py` — tests du routeur de complexité

Outillage :

- `bench_rag_v2.py`, `compare_phaseC.py`, `ragas_baseline_run.py`, `reindex_auto.py`, `audit_rag.py`

Lancement :

- `start_rag.cmd` — lancement du serveur RAG local (127.0.0.1:8200)

## Règle de synchronisation

Tant qu'il n'existe pas de dépôt dédié au RAG, **toute modification de code doit
être appliquée aux deux endroits** :

1. `%LOCALAPPDATA%\hermes\data\rag\` (source exécutée par le serveur)
2. ce dossier (copie versionnée)

Sinon la copie versionnée dérive silencieusement du code réellement utilisé.

## Non versionné ici (volontairement)

`manifeste.json` (artefact généré), `venv/`, `ragas_env/`, `models_flashrank/`,
`index.faiss`, `chunks.jsonl`, `cache.db`, `*.log`.
