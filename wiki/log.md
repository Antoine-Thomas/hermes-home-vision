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

## [2026-09-27] create | page concepts/laya-onnx-windows.md

- Ajout manuel (sans appel LLM) du concept Laya ONNX Windows CPU : installation sans PyTorch,
  contrat du graphe, latences mesurees (190 ms par decision), comparaison avec Jev.
- `index.md` mis a jour a la main (section Concepts, ordre alphabetique) : 18 pages.
- Aucune page existante modifiee.

## [2026-09-29] create | page concept ANIMA

- Page `concepts/anima.md` creee : ANIMA 0.1 (supervision 15 composants + memoire hierarchique RAG/JEV).
- Sources : chantier_ANIMA_0.1.log (etapes 1-10), health_anima.json, docs/ANIMA_*.md.
- Tags : hermes, omniroute, rag, jev, cron, provider, model.
## [2026-10-06] lint | contradictions

- 5 contradictions trouvees : 1 ouverte (`jev` vs `laya-onnx-windows`, latence
  0,316 s contre 0,50 s) et 4 tranchees par la source du 22/09 15:27
  (`free-openrouter` contre `fallback-chain`, `nvidia-stack` et `primary-model` :
  ordre des etages 2 et 3 ; `eco` contre `free-openrouter` : adhesion au combo).
- Pages touchees : concepts/fallback-chain.md, concepts/nvidia-stack.md,
  concepts/primary-model.md, concepts/free-openrouter.md, entities/openrouter.md,
  concepts/eco.md, concepts/jev.md, concepts/laya-onnx-windows.md.
- `contested: true` + `contradictions: [...]` poses sur ces 8 pages, `updated`
  incremente, les deux positions sont conservees dans chaque page (aucune
  affirmation ecrasee). `contradictions.md` mis a jour. Aucune ecriture dans
  `raw/` ni `scripts/`.

## [2026-10-06] lint | contradictions

- Second passage du 2026-10-06 (le premier portait sur l'ordre des etages 2/3 de la
  chaine). 2 contradictions nouvelles, toutes deux tranchees par la source la plus
  recente : `auto-best-reasoning` vs `primary-model` (identite du modele primaire)
  et `fallback-providers` vs `fallback-chain` (composition de `fallback_providers`).
  1 contradiction reste ouverte : `jev` vs `laya-onnx-windows` (latence 0,316 s
  contre 0,50 s).
- Elements nouveaux verses a l'analyse : releve direct de `config.yaml` le 2026-10-06
  (`model.default: deepseek-flash`, `model.provider: deepseek`, `fallback_providers`
  = `omniroute/free-openrouter` -> `omniroute/nvidia-stack` -> `deepseek/deepseek-flash`,
  `agent.api_max_retries: 3`) et relecture de la note
  `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`
  (22/09 15:27 : `Primary: auto/best-reasoning (via omniroute)`, chaine de 4 entrees).
- Pages touchees : concepts/primary-model.md, concepts/auto-best-reasoning.md,
  concepts/auto-best-free.md, concepts/hermes-config.md, concepts/fallback-chain.md,
  concepts/fallback-providers.md, concepts/eco.md, concepts/free-openrouter.md.
- `contested: true` + `contradictions: [...]` poses ou completes, `updated` incremente,
  les deux positions sont conservees dans chaque page (aucune affirmation ecrasee).
  `contradictions.md` mis a jour. Aucune ecriture dans `raw/` ni `scripts/`.
