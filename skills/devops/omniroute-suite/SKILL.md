---
name: omniroute-suite
description: "OmniRoute compression, cost tracking, and auto-update — requetes compressees, monitoring budget, mises a jour auto."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [linux, windows, macos]
metadata:
  hermes:
    tags: [omniroute, compression, cost-tracking, auto-update]
    category: devops
    created: "2026-09-10"
    umbrella_of: [compression-tokens, omniroute-cost-tracker, omniroute-auto-update]
---

# OmniRoute Suite — Compression, Cost Tracking & Auto-Update

Pipeline de compression OmniRoute, suivi des couts et mises a jour automatiques. Les skills proteges `fallback-intelligent` et `omniroute-gateway` restent independants.

## When to Use

- Reduire les tokens LLM via OmniRoute (`compression-tokens`)
- Suivre / auditer les couts par combo et par modele (`omniroute-cost-tracker`)
- Mettre a jour OmniRoute automatiquement (`omniroute-auto-update`)
- Ne pas utiliser pour `fallback-intelligent` ou `omniroute-gateway` (proteges)

## Compression — points cles

- Auth d'abord : le CLI ment sur les echecs — verifier le header echo.
- Endpoint de compression empilee (stacked) : seul vrai endpoint.
- RTK ne touche que `role="tool"` messages.
- Verifier avec le header de reponse echoe.
- Preview endpoint : sur, sans burn de rate-limit.
- Combos : adresser par BARE NAME, prober les membres (modeles morts = 1er hop perdu).
- Binding OmniRoute en loopback seul, wiring dans Hermes.

Voir `references/compression-tokens.md` pour la procedure complete (241l, decoupee en refs par H2).

## Cost Tracker

Contexte, etapes et pieges du suivi des couts OmniRoute.

Voir `references/omniroute-cost-tracker.md` (32l).

## Auto-Update

Mises a jour automatiques d'OmniRoute via GitHub releases. Cron job de veille + script de mise a jour automatique.

Voir `references/omniroute-auto-update.md` (72l).

## Probe des modeles gratuits (`scripts/probe_omniroute.py`)

- Verifier que `127.0.0.1:20128` est toujours en ECOUTE apres une passe : le probe tape des cibles aux credentials incomplets (ex. `cloudflare-ai` sans Account ID) dont le rejet non gere peut tuer le daemon en pleine passe. La tache planifiee `OmniRoute-Watchdog` le relance dans les minutes qui suivent, mais pendant la coupure tout le trafic Hermes part sur le payant.
- Quand la lecture du combo eco echoue (`warn: lecture eco impossible`, puis `eco unchanged: 0 modeles (eco illisible)`), le script ne fait NI fusion NI elagage et `changed` reste faux : un vrai changement est manque jusqu'au tick suivant. Ne pas se fier au log du probe — relire l'etat reel par `GET /api/combos` (header `Authorization: Bearer $OMNIROUTE_API_KEY`) des que le port repond.
- **Fichiers reels du cron `omniroute-eco-autorefresh`** (verifies 2026-09-22) : script actif = `C:\Users\searc\AppData\Local\hermes\scripts\probe_omniroute.py` (twin identique dans `Projets\hermes-home-vision\scripts\`), etat = `hermes\data\omniroute\probe_omniroute_state.json`, log = `%TEMP%\omniroute_probe_result.json`. Le `probe_omniroute.py` de `hermes\data\omniroute\` (16/09) est un ancien exemplaire inutilise : ne pas le confondre.
- Verifier une passe sans relancer le probe : `GET /api/combos` (header `Authorization: Bearer $OMNIROUTE_API_KEY`, cle dans `~/.omniroute/.env`) puis un POST `model=eco` — le log seul ne prouve pas que le combo sert. `netstat -ano | grep 127.0.0.1:20128` + `schtasks /query /tn OmniRoute-Watchdog` (relance toutes les 5 min) pour la survie du daemon.
- Le nombre de cibles mortes rapporte par le log peut etre faux quand `eco illisible` : `added_to_eco` liste alors les seuls vivants du moment, pas un ajout reel.
- **Combo `eco-fast` = 8 membres 100% morts** (`auto/zai` et `auto/gemini` -> `No credentials for auto`, `zc/glm-5.3` -> `502 spawn zcode ENOENT`, `oc/*` -> 403 free tier) : tout appel qui le prend atteint le `Combo loop safety timeout (600000ms)` et pend 10 min avant de rendre 503. Ne rien router dessus tant que ses membres n'ont pas ete remplaces par des routes concretes ; le probe eco ne le touche pas (il ne `PUT` que `eco`).
- `cloudflare-ai/@cf/...` (Account ID absent : 502, ~9 s) et `zc/glm-5.3` (~3 s) sont les deux cibles les plus lentes du probe : elles pesent sur la duree de passe sans jamais pouvoir devenir vivantes.
- Source de la regression d'`eco` : copie divergente `Projets\hermes-home-vision\scripts\probe_omniroute.py` (contenait `auto/*` dans `CANDIDATES`). **Copie alignee sur la version active le 2026-09-21 17:08** (`diff` vide) et `eco` remis manuellement a 3 cibles reelles (`PUT /api/combos/<ECO_ID>`, backup dans `data/omniroute/backups/`). Le retrait dans `eco` reste une action manuelle : le probe ne `PUT` que sur `changed` et ne peut plus retirer les alias (hors `CANDIDATES`). Controle : `diff <(sed 's/\r$//' <active>) <(sed 's/\r$//' <copie>)` vide, et 0 ligne `No credentials for auto` dans `app.log` apres le `PUT`.
- Un probe honnete peut rapporter 2 vivants puis un appel `model=eco` echouer en 503/429 juste apres : les hops sont rate-limites par vagues (gemini 429 cooldown, NIM 503 « worker local total request limit reached (16/16) »). Pour dire si `eco` sert vraiment, appeler chaque cible en direct, pas seulement le probe.
- Le probe ne couvre pas tous les membres d'eco : toujours relire `GET /api/combos` avant de conclure « eco sain ».
- La sonde consomme le quota gratuit des cibles d'eco, et la route gemini a un plafond **journalier** de
  20 requetes (1 seul compte) : au-dela, elle est fermee jusqu'au lendemain meme si le log annonce un
  `reset` de quelques secondes. Un tick « 3/8 vivants, changed=false » avec un appel `eco` en 503 juste
  apres n'est donc pas contradictoire : les cibles vivent, c'est la fenetre gratuite qui est fermee.
- Les compteurs `terminal_failures` ne purgent que les membres d'eco : les cibles mortes hors combo (gemini-2.5-flash/-lite en 404 definitif, pool `oc/*` et `opencode/*` en 403, pollinations 401, cloudflare-ai sans Account ID) cumulent des compteurs >100 sans etre elaguees ni retirees de `CANDIDATES`, et brulent ~11 probes par passage. Verifier le catalogue avant de conclure a un modele « vivant mais ignore ».

## Proteges — non inclus

- `fallback-intelligent` (protege, 130l, 2026-09-08) — chaine de repli gratuit->payant
- `omniroute-gateway` (protege, 107l, 2026-09-08) — reordonnancement des combos

## References

- `references/compression-tokens.md` — verbatim from `devops/compression-tokens/` (archived 2026-09-10)
- `references/omniroute-cost-tracker.md` — verbatim from `devops/omniroute-cost-tracker/` (archived 2026-09-10)
- `references/omniroute-auto-update.md` — verbatim from `omniroute-auto-update/` (archived 2026-09-10)
