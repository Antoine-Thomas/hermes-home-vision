---
name: second-cerveau-complet
description: "Orchestrer SiYuan, RAG et memoire persistante."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [siyuan, rag, memory, knowledge]
---

# Second cerveau complet

## When to Use

Quand il faut maintenir ou interroger le second cerveau : retrouver une procedure passee,
documenter une decision, ou reindexer la base. Un seul point d'entree pour SiYuan + RAG
+ memoire native, dans la hierarchie 1 -> 4.

## Quick Reference

```
Hierarchie : 1. MEMORY.md/USER.md (toujours charge)
             2. SiYuan API 6806 (documents cures)
             3. RAG port 8200 (fragments filtres)
             4. Skills Hub en ligne (hors local)
Orchestre  : siyuan-second-brain, rag-second-cerveau, hermes-memory
Scripts    : data\rag\{chercher,indexer,router_memoire,serveur_rag}.py
```

## Procedure

1. **Avant de dire "je ne sais pas"** : interroger SiYuan (niveau 2) puis le RAG (niveau 3).
2. **Recherche RAG** : `chercher.py "question"` ou POST `/search` sur 8200.
3. **Router** : `router_memoire.py` applique la hierarchie + budget tokens + fraicheur.
4. **Documenter** : nouvelle info -> SiYuan d'abord ; MEMORY.md seulement si durable (1 ligne).
5. **Reindexer** apres modification des sources : `indexer.py` (~5 min).

## Pitfalls

- Le RAG n'est PAS consulte automatiquement : il faut l'appeler explicitement.
- Si le noyau SiYuan est arrete, la source `siyuan` revient vide en silence — verifier le manifeste.
- Ne jamais dupliquer dans MEMORY.md ce qui vit dans SiYuan (budget 2100 chars).
- Ne pas ecrire dans MEMORY.md/USER.md sans validation (regle utilisateur).

## Verification

- SiYuan 6806 et RAG 8200 repondent.
- Une question test remonte le bon document en tete (score > 0,8).
- `manifeste.json` coherent avec le nombre de fragments attendu.
