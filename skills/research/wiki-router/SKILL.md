---
name: wiki-router
description: Use when routing a question to the wiki or the RAG.
version: 1
author: hermes-agent
license: mit
metadata:
  hermes:
    tags: [wiki, rag, jev, routing, knowledge-base, cron]
    category: research
    related_skills: [llm-wiki, typesafe-ai, rag-second-cerveau, omniroute-gateway]
---

# Routeur L1 / L2 (wiki compilé ↔ RAG brut)

Hermes n'a **aucun hook `memory.prefetch`** (`hermes memory` ne connaît que des
providers externes : honcho, openviking, mem0, hindsight, holographic, retaindb,
byterover — et `hermes config get memory` n'expose aucune clé `prefetch`). Le
routage se fait donc **côté skill**, pas côté config.

## Architecture

| Niveau | Support | Chemin | Usage |
| --- | --- | --- | --- |
| **L1** | wiki compilé (motif Karpathy, skill `llm-wiki`) | `%LOCALAPPDATA%\hermes\wiki` (`WIKI_PATH`) | Connaissances déjà synthétisées, cross-référencées |
| **L2** | RAG maison | `data/rag` (serveur 8200, e5-base, cache TTL 24 h) | Recherche brute, fait précis, source primaire |
| Routeur | Jev `choice` | `wiki\scripts\jev_router.py` | Décide `wiki` / `rag` / `both` |

Jev coûte ~1,3 × 10⁻⁵ $ et ~0,4 s par question : router **avant** de générer.

## Procédure

1. Router :

   ```bash
   python "$LOCALAPPDATA/hermes/wiki/scripts/jev_router.py" --json "<question>"
   ```

   `--json` renvoie `route`, `route_confidence`, `wiki_coverage`, `wiki_state`,
   `usage.cost`, `elapsed_s`. Codes de sortie : `0` OK, `2` Jev injoignable
   (l'erreur brute est affichée — **ne jamais inventer une route**).

2. Selon `route` :
   - `wiki` → lire `index.md` puis les pages `[[citées]]` ; répondre en citant
     `[[page-a]]`, `[[page-b]]`.
   - `rag` → interroger le RAG sur `data/` (skill `rag-second-cerveau`) ; citer
     les documents, pas les pages.
   - `both` → synthèse L1 **puis** vérification L2 des chiffres/dates/PID.

3. Une réponse non triviale (comparaison, synthèse) se **classe dans le wiki**
   (`comparisons/` ou `queries/`) — c'est ce qui fait composer le L1.

## Réglages et pièges mesurés

- **Wiki vide ⇒ `rag` forcé, sans appel Jev.** La règle est dans le code
  (`jev_router.py`, fonction `route`) : décider `wiki` sans page compilée
  garantit une réponse creuse. Ne pas « corriger » ce comportement.
- **Une compilation n'est pas une route.** Ne pas confondre : router = choisir
  le niveau ; compiler = écrire les pages (`wiki/scripts/prompts/compile.md`).
- **Erreur Jev = erreur à remonter.** Le routeur sort en code 2 avec l'erreur
  brute (`Jev HTTP …`, `Jev injoignable …`). Ne jamais retomber silencieusement
  sur une route par défaut.
- **Un modèle gratuit n'est pas un modèle d'agent long.** Mesure : un modèle
  gratuit abandonne la tâche de compilation au-delà de ~15 appels d'outils
  (exploration en boucle, 0 fichier écrit). Les prompts de maintenance doivent
  **borner le nombre d'appels** et interdire les relectures.
- **Les routes gratuites saturent, elles ne meurent pas.** Symptômes réels, à
  citer tels quels : `gemini | all 1 active accounts cooling down … (429)`,
  `[504] Request exceeded OmniRoute's local rate-limit execution expiration
  (legacy resilienceSettings.requestQueue.maxWaitMs=15000ms)`, puis `omniroute
  rate-limited every one of 3 attempts`. **Re-sonder après 2-3 min** avant de
  conclure ; un `200` en appel direct ne garantit pas une session longue.
- **Ordre de repli pour une compilation gratuite** : combo `eco` → combo
  `nvidia-stack` → **autre route gratuite hors OmniRoute** (`--provider google
  -m gemini-3.8-flash` ou `--provider groq -m openai/gpt-oss-120b`). Jamais le
  primaire payant (`deepseek-flash`) : une compilation de wiki n'a aucune raison
  de facturer.
- **Les `fallback_providers` restent actifs pendant un `-z` en modèle imposé.**
  Un run lancé en `--provider google` peut repartir sur la chaîne de repli
  (`omniroute/eco` → `omniroute/nvidia-stack`) si sa cible échoue en cours de
  route : l'erreur finale cite alors OmniRoute et non le provider imposé. Lire
  le log entier (`cache/wiki-compile-*.log`) et `sessions.billing_provider`
  avant d'attribuer l'échec au mauvais provider.
- **Un seul compilateur à la fois.** Deux runs qui écrivent le même wiki
  (manuel + cron tombé sur la même heure) se marchent sur `index.md` et `log.md`.
  Avant de lancer une compilation manuelle, vérifier qu'aucun tick cron de wiki
  n'est en cours (`cron/executions.db`, colonne `status`), et préférer une cadence
  cron décalée.
- **Facturation à vérifier, jamais supposée** : `select model, billing_provider,
  estimated_cost_usd from sessions` sur le `state.db` du profil (lecture
  `mode=ro`). Mesure : un run `-m eco` peut se facturer `billing_provider:
  custom` à **0 $** ; un run servi par un LLM payant s'y voit immédiatement.

## Vérifications

```bash
python "$LOCALAPPDATA/hermes/wiki/scripts/jev_router.py" "Qu'est-ce que le LLM Wiki ?"
hermes cron list | grep -i wiki      # 3 jobs : compile, contradictions, archive
find "$LOCALAPPDATA/hermes/wiki" -name '*.md' -newermt '-1 day'
```
