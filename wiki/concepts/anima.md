---
title: ANIMA
created: 2026-09-29
updated: 2026-10-07
type: concept
tags: [hermes, omniroute, rag, jev, cron, provider, model]
sources: [raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md]
confidence: high
---

# ANIMA 0.2 — supervision et mémoire hiérarchique

ANIMA est la couche qui enveloppe Hermes : **Hermes est le moteur, ANIMA est le
système intégré**. Elle surveille 15 composants ([[omniroute]], RAG, SiYuan,
Ollama, jobs, coûts, repli) et route chaque question vers la bonne source de
mémoire.

## Les 4 couches de mémoire

1. `MEMORY.md` + `USER.md` (natif, toujours chargé)
2. SiYuan (127.0.0.1:6806) — projets, décisions
3. RAG local (127.0.0.1:8200) — questions techniques (index e5-base)
4. Skills Hub (en ligne) — domaine non couvert

Le routeur (`router_memoire.py`) choisit la couche via [[jev]] (repli regex), et
le plugin `anima-memoire-router` (hook `pre_llm_call`) injecte les extraits RAG
dans le contexte du LLM.

## Câblage E2E (étape 10)

Flux : message → profil → routeur (JEV/regex) → LLM (combo) → RAG → JEV → réponse.
Vérifié : T1 (réponse cite le RAG), T2 (JEV échec → regex), T3 (RAG échec →
fail-open). Tests 15/15 health + 9/9 plugin.

## Supervision

`health_anima.py` sonde les composants toutes les 15 min (états READY / DEGRADED
/ FAILED / BLOCKED) et produit `health_anima.json`. Seuils documentés
([[fallback-chain]] : `cout_24h` 5 $, `repli_payant` 0,50 $). État global
**DEGRADED** (causé par OmniRoute 56,5 % succès, pas par ANIMA).

Voir [[state-db]] pour l'attribution des coûts, [[eco]] et [[nvidia-stack]] pour
les cibles gratuites du combo.
