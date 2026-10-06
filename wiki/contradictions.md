# Contradictions

> Registre lisible des contradictions detectees entre pages du wiki.
> **Complement, jamais remplacement** : la source de verite machine reste le
> frontmatter `contested: true` + `contradictions: [slug]` de chaque page.
> Alimente par le cron « LLM Wiki contradictions » et par tout lint.
> Format : `## [YYYY-MM-DD] slug-a vs slug-b` + positions datees + arbitrage.

## Format

```
## [YYYY-MM-DD] page-a vs page-b

- Sujet : ce qui se contredit
- Position A (page-a, source, date) : ...
- Position B (page-b, source, date) : ...
- Arbitrage : en attente | tranche le YYYY-MM-DD (raison)
```

## Contradictions ouvertes

## [2026-10-06] jev vs laya-onnx-windows

- Sujet : latence de Jev (deux valeurs pour le meme objet)
- Position A (concepts/jev.md, mesure du 26/09/2026) : 0,316 s par appel
- Position B (concepts/laya-onnx-windows.md, doc SiYuan « Laya ONNX Windows CPU - 27-09-2026 », 27/09/2026) : 0,50 s (« aller-retour reseau »)
- Arbitrage : **en attente** — l'ecart tient vraisemblablement au protocole de mesure (mesure locale contre aller-retour incluant le reseau) ; une mesure de reference unique est necessaire.

## Contradictions tranchees

## [2026-10-06] free-openrouter vs fallback-chain

- Sujet : place de `free-openrouter` dans la chaine de repli (2e ou 3e etage)
- Position A (concepts/fallback-chain.md, source raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md, 22/09/2026) : `eco` -> `nvidia-stack` -> `free-openrouter` -> `deepseek-flash`
- Position B (concepts/free-openrouter.md, memes sources, 22/09/2026) : `free-openrouter` = 2e etage, juste apres `eco`
- Arbitrage : **tranche le 2026-10-06 par la source** — la note du 22/09 15:27 (« chaine finalisee ») donne la liste ordonnee `1. eco / 2. free-openrouter <- NOUVEAU / 3. nvidia-stack / 4. deepseek-flash`, confirmee par les latences mesurees (7,3 / 9,8 / 23,2 / 6,5 s) et les lignes `state.db` (rowid 1002-1005). Position B exacte.

## [2026-10-06] nvidia-stack vs free-openrouter

- Sujet : quel etage suit immediatement `eco`
- Position A (concepts/nvidia-stack.md, source raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md, etat du 22/09 avant 15:27 ; ordre du repo, commit `aac90d5`) : `nvidia-stack` « invoque apres eco »
- Position B (concepts/free-openrouter.md, 22/09/2026) : `free-openrouter` suit `eco`
- Arbitrage : **tranche le 2026-10-06 par la source** — note du 22/09 15:27 : `free-openrouter` insere en position 2, `nvidia-stack` passe en 3. Position B exacte.

## [2026-10-06] primary-model vs free-openrouter

- Sujet : ordre des etages 2 et 3 cite en passant
- Position A (concepts/primary-model.md, source raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md) : « bascule sur nvidia-stack, puis free-openrouter »
- Position B (concepts/free-openrouter.md, entities/openrouter.md) : `free-openrouter` puis `nvidia-stack`
- Arbitrage : **tranche le 2026-10-06 par la source** — meme preuve que ci-dessus (note du 22/09 15:27 + latences + `state.db`). Position B exacte.

## [2026-10-06] eco vs free-openrouter

- Sujet : `eco` est-il membre du combo `free-openrouter` ?
- Position A (concepts/eco.md, source raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md) : « Il figure comme membre du combo `free-openrouter` »
- Position B (concepts/free-openrouter.md, memes notes) : le combo compte 3 membres (`nvidia/nemotron-3-super-120b-a12b:free`, `cohere/north-mini-code:free`, `nvidia/nemotron-3-ultra-550b-a55b:free`) ; `eco` est lui-meme un combo distinct de 3 membres
- Arbitrage : **tranche le 2026-10-06 par la source** — la note recense « 5 combos : `eco` 3, `eco-fast` 8, `free-openrouter` 3, `nvidia-stack` 3, `vision` 1 membres » : `eco` et `free-openrouter` sont deux combos distincts. Position B exacte.

## [2026-10-06] auto-best-reasoning vs primary-model

- Sujet : identite du modele primaire depuis le 22/09/2026 (et statut de `auto/best-reasoning`)
- Position A (concepts/primary-model.md, concepts/hermes-config.md, concepts/fallback-chain.md ; source `raw/notes/siyuan-20260922-primary-auto-best-free-mesure-et-derive-22-09-20.md`, 22/09 14:24) : primaire = `eco` (`model.default: eco`) ; `auto/best-reasoning` « ecarte de la chaine », « n'est pas le modele principal »
- Position B (concepts/auto-best-free.md, 22/09, meme note source) : `auto/best-free` etait primaire mais ne repond jamais (400/502) ; `auto/best-reasoning` est « le modele principal fonctionnel »
- Position C (concepts/auto-best-reasoning.md, 22/09, 5 sources) : alias payant Anthropic, ecarte de la chaine le 22/09/2026, pas le primaire
- Position D (source `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`, 22/09 15:27) : `hermes fallback list` relu -> `Primary: auto/best-reasoning (via omniroute)` + chaine de 4 entrees (1. `eco`, 2. `free-openrouter`, 3. `nvidia-stack`, 4. `deepseek-flash`) ; `state.db` rowid 1001 = `auto/best-reasoning` ; `hermes doctor` lit `model.default 'auto/best-reasoning'`
- Position E (releve direct de `config.yaml`, 2026-10-06) : `model.default: deepseek-flash`, `model.provider: deepseek`
- Arbitrage : **tranche le 2026-10-06 par la source** — les deux references les plus recentes donnent un primaire qui n'est pas `eco` : `auto/best-reasoning` au 22/09 15:27, `deepseek-flash` au 2026-10-06. La note du 14:24, citee par la Position A, posait en realite `model.default: auto/best-free` (pas `eco`). `eco` n'est donc pas le primaire a ces dates.

## [2026-10-06] fallback-providers vs fallback-chain

- Sujet : composition et ordre de `fallback_providers`
- Position A (concepts/fallback-providers.md, source `raw/notes/siyuan-20260922-restauration-providers-depuis-repo-22-09-2026.md`, 22/09 13:58) : deux couples, `omniroute/nvidia-stack` puis `deepseek/deepseek-flash`
- Position B (concepts/fallback-chain.md, concepts/eco.md, concepts/free-openrouter.md ; source `raw/notes/siyuan-20260922-chaine-de-repli-finalisee-5-niveaux-22-09-2026.md`, 22/09 15:27) : quatre etages `eco` -> `free-openrouter` -> `nvidia-stack` -> `deepseek-flash`
- Position C (releve direct de `config.yaml`, 2026-10-06) : trois couples `omniroute/free-openrouter` -> `omniroute/nvidia-stack` -> `deepseek/deepseek-flash` (pas de `eco`)
- Arbitrage : **tranche le 2026-10-06 par la source la plus recente** — Position C pour la composition actuelle. L'ordre `free-openrouter` avant `nvidia-stack` (Position B) est confirme par les deux references les plus recentes ; l'ordre fige du repo (Position A, commit `aac90d5`) et la presence de `eco` dans `fallback_providers` sont perimes.
