# ANIMA 0.2 — Architecture

ANIMA est la couche de supervision et de mémoire hiérarchique d'Hermes : elle
surveille les composants, route les questions vers la bonne source de mémoire
(SiYuan / RAG / mémoire native) et documente les coûts et la chaîne de repli.

## Les 4 couches de mémoire

```
┌─────────────────────────────────────────────────────────────┐
│ Niveau 4 : Skills Hub (en ligne)           domaine non couvert │
├─────────────────────────────────────────────────────────────┤
│ Niveau 3 : RAG local  (127.0.0.1:8200)     questions techniques│
├─────────────────────────────────────────────────────────────┤
│ Niveau 2 : SiYuan     (127.0.0.1:6806)     projets, décisions  │
├─────────────────────────────────────────────────────────────┤
│ Niveau 1 : MEMORY.md + USER.md (natif)     toujours chargé     │
└─────────────────────────────────────────────────────────────┘
```

Règle : on consulte le premier niveau qui peut répondre, pas le meilleur score
vectoriel. Le RAG (niveau 3) n'est consulté que si les niveaux 1-2 sont
insuffisants.

## Flux de données (E2E, câblé à l'étape 10)

```mermaid
flowchart LR
  U[Message utilisateur] --> G[Gateway Hermes]
  G --> P[Profil (default)]
  P --> H[Hook pre_llm_call<br/>anima-memoire-router]
  H --> J[JEV : choix de la couche<br/>repli regex]
  J -->|rag_L2| R[RAG /search :8200]
  J -->|wiki_L1| S[SiYuan :6806]
  J -->|memoire_native| N[Mémoire native]
  R --> I[Injection <rag_context>]
  S --> I
  I --> L[LLM (combo OmniRoute)]
  N --> L
  L --> A[Réponse]
```

Chemin nominal observé (T1, étape 10) : message → hook → JEV (`rag_L2`) → RAG
`/search` → injection `<rag_context>` → LLM (combo) → réponse citant le document.

## Composants et ports

| Composant | Rôle | Port/URL |
|---|---|---|
| gateway | Réception des messages, dispatch | processus local |
| profils | Profils actifs (default, veille, watch, docs-writer) | — |
| omniroute | Routeur de modèles (combos) | 127.0.0.1:20128 |
| nim_proxy | Proxy NVIDIA NIM | local |
| ollama / ollama-local | Modèles locaux (llama3.2:3b) | 127.0.0.1:11434 |
| rag | Index + recherche vectorielle (e5-base) | 127.0.0.1:8200 |
| siyuan | Base de connaissance (notes structurées) | 127.0.0.1:6806 |
| wazuh | SIEM (cluster/dashboard) | 9200 / 8443 |
| jev | Décideur mémoire (TypeSafe/OpenRouter/gateway) | plugin jev-skill-router |
| laya | Décision locale ONNX (CPU) | module data/rag |
| cron | Jobs planifiés | — |
| reindex | Reconstruction de l'index RAG (03:00) | — |
| memoire | Budget mémoire USER.md / MEMORY.md | fichiers |
| couts | Suivi des coûts (state.db) | — |
| fallback | Chaîne de repli | config.yaml |

## Dépendances

- `router_memoire.py` (data/rag) : route les questions, appelle JEV (repli regex),
  journalise dans `jev_routing.jsonl`.
- `health_anima.py` / `health_architecture.py` (data/route_ia_fix) : supervision
  (sondes, états, seuils), produisent `health.json` / `health_anima.json` toutes
  les 15 min.
- `anima-memoire-router` (plugin) : hook `pre_llm_call` qui câble router_memoire +
  RAG dans le flux du bot (étape 10).

## États de supervision

`READY` (sonde fonctionnelle concluante) · `DEGRADED` (mesure dégradée) ·
`FAILED` (panne dure) · `BLOCKED` (non évaluable, ex. JEV sans usage).
Agrégation : un critique `FAILED` → global `FAILED` ; sinon un composant
secondaire en `DEGRADED`/`FAILED`/`BLOCKED` → global `DEGRADED` ; sinon `READY`.
