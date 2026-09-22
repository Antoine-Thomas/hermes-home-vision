---
source_url: siyuan://20260921223640-38gbwri/20260922135842-wa8yqku
ingested: 2026-09-22
sha256: 10011656e3e3d8f21f804b8bc17e2b7250e54cc8dd3953f2ceae645b9fadf957
---

# Restauration providers depuis repo - 22-09-2026

---
title: Restauration providers depuis repo - 22-09-2026
date: 2026-09-22T13:58:42+02:00
lastmod: 2026-09-22T13:59:31+02:00
---

# Restauration providers depuis repo - 22-09-2026

# Restauration providers depuis le repo - 22-09-2026

## Déclencheur

Routeurs OmniRoute + ordre de switch cassés depuis la veille. Objectif : restaurer la config des  
providers/fallback depuis le repo `Antoine-Thomas/hermes-home-vision`​, **sans toucher aux clés(.env) ni à la mémoire**.

## Source de vérité (constat : pas de clonage nécessaire)

- `C:\Users\searc\AppData\Local\hermes`​ **est déjà le clone** du repo (origin = hermes-home-vision, branche `main`).
- Second clone existant : `C:\Users\searc\Projets\hermes-home-vision`​ (branche `v1.2-ameliorations`).
- `config.yaml`​ est **identique sur toutes les refs** (`origin/main`​, `origin/v1.2-ameliorations`​, tags `v1.1-original`​, `v1.2`).
- Dernier commit touchant `config.yaml`​ : `aac90d5` — 2026-09-17 15:42 — « config bureau: repli gratuit nvidia-stack avant deepseek-flash ».
- `.env`​ est gitignoré (`**/.env`) : aucune clé dans le repo.

## Diagnostic avant restauration

|Clé|État cassé|Repo (cible)|
| -----------| ----------------------------------------| ---------------------------------------------------|
|`model.provider`​ / `model.default`|**deepseek / deepseek-flash** (payant en primaire)|omniroute / eco|
|`fallback_providers`| **[omniroute/eco]**  (1 seul étage, plus de repli payant)|[omniroute/nvidia-stack, deepseek/deepseek-flash]|
|`agent.api_max_retries`|2|3|

Écarts hors périmètre, **conservés** (ajouts du 21/09, absents du repo) : blocs `providers.groq`​ et  
​`providers.google`​, `web.search_backend=exa`​, `web.extract_backend=firecrawl`​,  
​`fallback.min_switch_reset_seconds=30`​, `gateway.multiplex_profiles=true` (décision utilisateur).

## Méthode

`patch`​/`write_file`​ sont refusés sur `config.yaml`​ (fichier de config sensible) ; un  
​`yaml.safe_dump`​ global aurait perdu commentaires et ordre. Utilisé `hermes config set` :

```
hermes config set model.provider omniroute
hermes config set model.default eco
hermes config set fallback_providers '[{provider: omniroute, model: nvidia-stack}, {provider: deepseek, model: deepseek-flash}]'
hermes config set agent.api_max_retries 3
```

Vérifié ensuite : `hermes config get model`​ → `default: eco / provider: omniroute`​ ;  
​`hermes fallback list`​ → `Primary: eco (via omniroute)`, chaîne de 2 entrées (nvidia-stack via  
omniroute, puis deepseek-flash via deepseek). Blocs groq/google toujours présents (lignes 25 et 37).

## Preuves (state.db — quel étage a servi le tour)

`$LOCALAPPDATA\hermes\state.db`​, tables `session_model_usage`​ / `sessions`​ (colonnes  
​`billing_provider`​, `billing_base_url`).

- Test primaire `hermes -z`​ → session `20260922_135431_215d83`​ : **model** **​`eco`​**​ **, billing_provider**​**​`custom`​**​ **, base_url** **​`http://127.0.0.1:20128/v1`​**​ → l'étage gratuit OmniRoute a réellement servi  
  le tour (pas de bascule silencieuse). Réponse : `pong-restore` en 8,5 s.
- Tests isolés (billing relu en base) :

  - `--provider omniroute -m eco`​ → `pong`​, billing `custom` / 127.0.0.1:20128 ;
  - `--provider omniroute -m nvidia-stack`​ → `pong`​, billing `omniroute` ;
  - `--provider deepseek -m deepseek-flash`​ → `Pong — je suis là.`​, billing `deepseek`.
- **Preuve dans la cascade** (et non forcée) : primaire neutralisé proprement via  
  ​`hermes --provider xiaomi -m mimo-v2.6-pro -z "ping"`​ (compte en 402), puis relecture de l'étage  
  qui a effectivement servi — 5 tirs : **4 servis par** **​`nvidia-stack`​**​ **/**​**​`omniroute`​**​  **(gratuit)** ,  
  1 servi par `deepseek-flash`​/`deepseek`​ (payant). Le tir payant correspond à une saturation  
  d'OmniRoute, côté proxy et non côté Hermes : log `~/.omniroute/call_logs/2026-09-22/`​ →  
  ​`[503] openai/nvidia/nemotron-3.5-lightning-30b-a3b ... [504] Request exceeded OmniRoute's local rate-limit execution expiration (legacy resilienceSettings.requestQueue.maxWaitMs=15000ms) ... RATE_LIMIT_EXECUTION_TIMEOUT`.  
  Conclusion : la chaîne avance bien, l'étage gratuit est atteignable, et la bascule payante  
  occasionnelle est un plafond de file local OmniRoute (15 s), pas un défaut de config.

## OmniRoute

- Config réelle : `C:\Users\searc\.omniroute`​ (storage.sqlite, combos, backups, call_logs).  
  **Absente du repo** (n'y figurent que `omniroute-launch.cmd/.vbs`​, `docs/omniroute/fix_combo_nvidia_prefix.py`).
- Daemon : écoute sur 127.0.0.1:20128 (PIDs suivis), HTTP 401 sans clé = vivant.
- Combos relus via `GET /api/combos`​ : `eco`​ 3 membres, `eco-fast`​ 8, `nvidia-stack`​ 3, `vision` 1.
- L'ordre de switch est à **deux niveaux** : intra-combo (ordre des membres, côté OmniRoute) et  
  inter-étages (chaîne `fallback_providers`, côté Hermes/config.yaml). La régression réparée  
  aujourd'hui était inter-étages.

## État résiduel (non réparé, décision utilisateur)

- `eco-fast`​ → 502 : `zc/glm-5.3`​ spawn zcode ENOENT + 4 membres `oc/*` en 403  
  (« OpenCode's free tier can only be used from within OpenCode »).
- `vision`​ → 502 : `gemini/gemini-3-flash-preview` renvoie une réponse vide sans sortie exploitable.
- Premier tir sur un combo fraîchement sollicité : 503 transitoire (déjà observé sur `eco` puis 200  
  au tir suivant) — rejouer avant de conclure à une panne.

## Backups conservés

- `config.yaml.bak.repair_20260922_115138`​, `.env.bak.repair_20260922_115138`​,  
  ​`cron.bak.repair_20260922_115138`​, `skills.bak.repair_20260922_115138`
- `config.yaml.bak.avant_restore_20260922_135355`​ (état juste avant les 4 `config set`)
- `.env` : jamais ouvert ni modifié — contrôle de présence 7/7 (GROQ, GOOGLE, DEEPSEEK, OPENROUTER,  
  OMNIROUTE, SIYUAN_TOKEN, XIAOMI).

## État final

Primaire `eco`​ (via omniroute, gratuit) → étage 1 `nvidia-stack`​ (gratuit) → étage 2  
​`deepseek-flash`​ (payant, dernier recours). `api_max_retries = 3`​. Gateway redémarrée  
(PID 24364, tâche planifiée `Hermes_Gateway`​), profils `default`​ (eco), `veille`​ et `watch`  
(nvidia-stack) en running.

## Comparaison finale avec le repo (relecture programmatique de config.yaml)

Identique au repo : `fallback_providers`​ (2 entrées, mêmes couples provider/model), le bloc  
​`providers.omniroute`​ (et `providers.ollama-launch`​), `agent.api_max_retries = 3`.

Écarts assumés et volontaires :

- `model.base_url`​ : **absent** côté actuel (le repo porte `http://127.0.0.1:20128/v1`​).  
  Le CLI supprime cette clé au changement de provider. Sans conséquence : la résolution du  
  provider `omniroute`​ rend le base_url défini dans `providers.omniroute.api`​, et c'est bien  
  ​`http://127.0.0.1:20128/v1`​ qu'on relit dans `state.db`​ (`billing_base_url`) pour le tour servi.
- `providers.groq`​ et `providers.google` : conservés (ajouts du 21/09, absents du repo).
- `gateway.multiplex_profiles = true` (repo : false) : conservé, décision utilisateur.
- `fallback.min_switch_reset_seconds = 30` : conservé, absent du repo.
