# Wiki Log

> Journal chronologique de toutes les actions du wiki. Append-only.
> Format : `## [YYYY-MM-DD] action | sujet`
> Actions : ingest, update, query, lint, create, archive, delete
> Au-delà de 500 entrées : renommer en `log-YYYY.md` et repartir à zéro.

## [2026-09-22] create | Wiki initialisé

- Domaine : infrastructure et stack IA locale (Hermes, OmniRoute, SiYuan, RAG, Jev, GPU, vidéo, skills, crons).
- Structure canonique du skill `llm-wiki` créée dans `%LOCALAPPDATA%\hermes\wiki`.
- `WIKI_PATH` ajouté à `.env`.
- Extensions locales : `raw/notes/` (notes SiYuan), `syntheses/`, `contradictions.md`, `scripts/jev_router.py`.
- Décision de seuil : canonique du skill (2+ sources OU 1 source centrale).
- Architecture cible : L1 = ce wiki, L2 = RAG sur `data/`, routeur = Jev.

## [2026-09-22] ingest | compilation one-shot (8 pages)

- Serveur : NIM direct nano-omni [nvidia/nemotron-3-nano-omni-30b-a3b-reasoning]
- entities/hermes-agent.md
- entities/omniroute.md
- concepts/fallback-chain.md
- concepts/primary-model.md
- concepts/eco.md
- entities/openrouter.md
- concepts/provider-connection.md
- concepts/state-db.md

## [2026-09-22] ingest | compilation one-shot (1 pages)

- Serveur : NIM direct lightning [nvidia/nemotron-3.5-lightning-30b-a3b]
- concepts/nom-en-kebab-case.md

## [2026-09-22] ingest | compilation one-shot (9 pages)

- Serveur : NIM direct nano-omni [nvidia/nemotron-3-nano-omni-30b-a3b-reasoning]
- entities/hermes-agent.md
- entities/omniroute.md
- concepts/fallback-chain.md
- concepts/eco.md
- concepts/deepseek-flash.md
- concepts/nvidia-stack.md
- entities/openrouter.md
- concepts/provider-connection.md
- comparisons/eco-vs-deepseek.md

## [2026-09-22] ingest | compilation one-shot (7 pages)

- Serveur : NIM direct nano-omni [nvidia/nemotron-3-nano-omni-30b-a3b-reasoning]
- entities/hermes-agent.md
- entities/omniroute.md
- concepts/fallback-chain.md
- concepts/eco.md
- concepts/deepseek-flash.md
- concepts/nvidia-stack.md
- concepts/provider-connection.md

## [2026-09-22] ingest | compilation one-shot (3 pages)

- Serveur : NIM direct super-120b [nvidia/nemotron-3-super-120b-a12b]
- concepts/free-openrouter.md
- concepts/auto-best-reasoning.md
- entities/openrouter.md

## [2026-09-22] ingest | compilation one-shot (6 pages)

- Serveur : NIM direct super-120b [nvidia/nemotron-3-super-120b-a12b]
- entities/openrouter.md
- concepts/auto-best-reasoning.md
- concepts/free-openrouter.md
- concepts/fallback-chain.md
- entities/hermes-agent.md
- entities/omniroute.md

## [2026-09-22] ingest | compilation one-shot (1 pages)

- Serveur : NIM direct super-120b [nvidia/nemotron-3-super-120b-a12b]
- entities/hermes-agent.md

## [2026-09-22] ingest | compilation one-shot (6 pages)

- Serveur : NIM direct nano-omni [nvidia/nemotron-3-nano-omni-30b-a3b-reasoning]
- concepts/auto-best-free.md
- concepts/deepseek-flash.md
- concepts/nvidia-stack.md
- entities/nvidia-nim-proxy.md
- concepts/hermes-config.md
- concepts/fallback-providers.md

## [2026-09-22] create | page concepts/jev.md

- Ajout manuel (sans appel LLM) du concept Jev : 3 primitives (`noul`, `choice`, `score`),
  perimetre d'usage, exemple d'appel.
- `index.md` regenere par `update_index([], dry=False)` : 17 pages.
- Aucune page existante modifiee.
