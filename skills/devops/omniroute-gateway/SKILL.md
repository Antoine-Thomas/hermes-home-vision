---
name: omniroute-gateway
description: Use when reordering OmniRoute combos to prefer free models.
version: 1
author: hermes-agent
license: mit
metadata:
  hermes:
    tags: [omniroute, llm-routing, free-models, hermes-config, devops]
    related_skills: [hermes-agent]
---

# OmniRoute Gateway Management

OmniRoute is a local LLM routing proxy (npm `omniroute`) running at
`http://127.0.0.1:20128` (dashboard + `/api` on :20128, inference on `/v1`).
It fans a single request across many upstream providers and exposes
**combos** — ordered model lists with a fallback strategy. The user's
`eco` combo is the default Hermes model and must prefer FREE models, only
falling back to paid in last resort.

## eco : cibles reellement atteignables dans un combo

Le combo resout le provider par le **prefixe du nom de modele** et filtre les cibles
AVANT dispatch. Consequence : les alias `auto/*` (`auto/gemini`, `auto/zai`, `auto/best-free`)
repondent `200` en appel direct mais sont **ecartes dans un combo** — log
`AUTH No credentials for auto`, puis `Provider <p> connection noauth auth failure (403)
— marking for skip on remaining targets (#8133)` : le combo renvoie un 403/402 global
en ~2 s alors que des modeles vivants figurent dans sa liste. Ne jamais mettre `auto/*`
dans `eco` ; ecrire les cibles en **provider/modele reels** :

- `gemini/gemini-3-flash-preview` — providerId `gemini` (cle Google, gratuit)
- `openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` — providerId `openai` (proxy NIM local :20200)

Diagnostic : dans `~/.omniroute/logs/application/app.log`, chaque requete detaille ses
targets (`Trying model i/N`, `No credentials for <provider>`, `marking for skip`).
Un echec de combo en ~2 s = cibles filtrees, pas un modele en panne.
Validation obligatoire apres toute ecriture de combo : `POST /v1/chat/completions
{"model":"eco"}` -> `200` + `content` non vide, et lire `model` dans la reponse (route
reellement servie) + 3 essais pour ecarter un coup de chance.

**Un combo qui echoue n'est pas forcement casse : verifier le PLAFOND DE CONTEXTE des cibles vivantes.**
Un combo dont les seules cibles vivantes n'ont pas le meme plafond echoue uniquement AU-DESSUS de ce
plafond. Mesure : le meme combo repond `200` en 2-5 s sur un prompt court (la premiere cible vivante
sert) et echoue en session longue parce que la cible a grand contexte (1 M) est en `429 cooldown` et
que les survivantes plafonnent a 128 K. Diagnostic dans cet ordre : (1) sonde courte — si elle passe,
le combo n'est pas en panne ; (2) `GET /v1/models` pour lire `context_length` de chaque cible vivante ;
(3) comparer au contexte reel de la session qui echoue. Ne jamais reconstruire un combo sur un seul
echec en session longue.

**Un job de maintenance additif accumule les cibles mortes.** Un probe qui n'ajoute jamais ne retire
rien : au bout de quelques semaines la majorite des cibles peut etre morte (providers fermes, modeles
retires du catalogue) et chaque appel paie leurs tentatives. Elaguer le combo ne suffit pas — le job le
re-remplira a son rythme : corriger aussi **son script** (retirer les familles mortes, purger au-dela de
N echecs consecutifs), le tester sur une copie du combo, puis relire le combo apres le passage horaire.

**Les alias `auto/*` resquillent dans `eco` via le probe lui-meme — CORRIGE le 2026-09-17 19:03.**
`CANDIDATES` les incluait et la phase additive ajoute tout modele vivant absent du combo : retirer
`auto/*` a la main dans `eco` etait **annule au tick suivant**. Corrige sur les deux cotes (retires de
`CANDIDATES` dans `scripts/probe_omniroute.py` + `PUT` du combo ; backup
`data/omniroute/backups/eco_before_alias_fix_20260917_190258.json`). `eco` = 3 cibles reelles
(gemini/gemini-3-flash-preview, openai/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning,
openai/nvidia/nemotron-3.5-lightning-30b-a3b). Preuve apres ecriture : log `Combo "eco" [priority]
with 3 models` -> `Trying model 1/3: gemini/...` -> `succeeded (6ms, 0 fallbacks)`, 3 appels de controle
`200` sur `gemini-3-flash-preview`, et **0 ligne** `No credentials for auto` apres 17:03Z (contre 3 par
appel eco avant). Ne pas re-ajouter `auto/*` a `CANDIDATES` : la sonde directe rend `200` et ferait
revenir l'alias dans `eco`.

**Deux fichiers nommes `probe_omniroute.py`** : `data/omniroute/probe_omniroute.py` (obsolete, version
reconstructive) et `scripts/probe_omniroute.py` (celui que le cron execute, additif + elagage).
Patcher `scripts/` et le verifier par `grep -n "auto/" <fichier>` — un `patch` sur le mauvais fichier
ne leve pas d'erreur explicite, il liste des suggestions sans rapport.
**Une TROISIEME copie hors `AppData` peut remettre les `auto/*` dans `eco`.** Mesure 2026-09-21 :
`Projets\hermes-home-vision\scripts\probe_omniroute.py` (copie de publication du home Hermes) contenait
encore `auto/gemini` + `auto/zai` dans `CANDIDATES` (l. 59-60) ; sa relance manuelle a ecrit `eco` a
12:01:57Z (`updatedAt`), remettant les 2 alias en tete. La version active ne peut PAS les retirer :
l'elagage ne considere que les membres d'eco presents dans `CANDIDATES` ayant un statut terminal courant,
et `auto/*` n'y figure plus. Verifier donc `grep -rn "auto/gemini" ~/Projets/*/scripts/` avant de conclure
que le retrait a tenu ; le corriger des deux cotes si la copie sert de source de redeploiement.
**CORRIGE le 2026-09-21 17:08** : la copie `Projets\hermes-home-vision\scripts\probe_omniroute.py` a ete
rendue **identique octet pour octet** a la version active (`auto/best-free`, `auto/gemini`, `auto/zai`
retires de `CANDIDATES`) ; backup `probe_omniroute.py.bak-20260921` a cote. Controle qui doit rester vrai :
`diff <(sed 's/\r$//' $LOCALAPPDATA/hermes/scripts/probe_omniroute.py) <(sed 's/\r$//' ~/Projets/hermes-home-vision/scripts/probe_omniroute.py)` vide.
Les deux fichiers sont en **LF** : editer en bytes, pas en `open(...,'w')` texte ; un `replace` cale sur `\r\n`
matche 0 fois (assertion `count==1` obligatoire, sinon l'edition passe pour un no-op silencieux).
**Retirer les alias de la copie ne les sort PAS d'`eco`** (le script ne `PUT` que sur `changed`) : apres une
relance de la copie, remettre `eco` a 3 cibles reelles par `PUT /api/combos/<ECO_ID>` avec le corps complet
(`models` + `strategy: priority` + `config` repris de la lecture), apres backup du combo dans
`data/omniroute/backups/`. Preuve : plus aucune ligne `No credentials for auto` dans `app.log` apres le
`PUT` (0 sur la fenetre suivante) et 3 appels de controle `{"model":"eco"}` en 200 (2,2-2,6 s, servis par
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`).
**Ces alias en tete d'eco ne coutent PAS de latence** (mesure 2026-09-21, 5 cibles dont les 2 alias) :
appel `model=eco` -> `200` en 1,6-2,2 s, trace `decisions=5`, 4 lignes `AUTH No credentials for auto` =
filtrage pre-dispatch a ~0 ms. En appel **direct** les memes alias repondent `200` (`auto/gemini` 5,6 s,
`auto/zai` 12,8 s). Ne pas promettre un gain de vitesse en les retirant : le gain est du bruit de log.
**Un tick servi par l'etage 2 (`nvidia-stack`) ressemble a une facturation sans en etre une — ne pas le confondre
avec DeepSeek.** Mesure 2026-09-23 01:00 Paris : le tick `cron_5c9dd16aaa37_20260923_010051` porte
`model=nvidia-stack, billing_provider=omniroute, estimated_cost_usd=0,0082` alors que les ticks precedents
(00:00, 23:00) portaient `model=eco, billing_provider=custom, cost=0.0`. Cause : la passe de :01 met
`gemini-3-flash-preview` au plafond gratuit JOURNALIER (`limit: 20, model: gemini-3-flash`) et sature la
fenetre NIM, donc le premier appel `eco` du tick tombe sur l'etage 2. Le signal d'alerte reste
`billing_provider=deepseek` ; un `omniroute` + cout estime non nul sur `nvidia-stack` se lit
« chaine gratuite, etage 2 », pas « bascule payante ». Verifier `config.yaml`
(`model.default=eco` / `provider=omniroute`, `fallback_providers=[nvidia-stack, free-openrouter, deepseek-flash]`)
avant de conclure.

**Detecter une bascule payante du job, cote Hermes** : `sessions.billing_provider` du `state.db` du profil
(`select id, model, billing_provider, estimated_cost_usd from sessions order by rowid desc limit 5`).
Mesure 2026-09-21 : les ticks 15:01 et 16:01 de `omniroute-eco-autorefresh` sont sortis en
`model=deepseek-flash, billing_provider=deepseek` (~0,013 et 0,017 $) alors que `jobs.json` porte
`model_snapshot=eco` — la chaine `eco -> nvidia-stack -> deepseek-flash` a bascule deux fois (log
`agent.log` : `Fallback activated: ...`). Cause : le probe tape les cibles NIM a :01 et epuise la limite
NIM par cle (`Worker local total request limit reached (16/16)`, grappes a :01/:02 a chaque heure) au
moment ou l'agent fait son premier appel eco. Un `billing_provider=deepseek` sur un job `eco` est le
signal a rapporter, pas un detail interne.
**Recidive mesuree 2026-09-22 (5 ticks d'affilee)** : ticks 01:00-05:00 (Paris) tous en `deepseek-flash`/
`billing_provider=deepseek` (~0,0066-0,0102 $ chacun, ~0,042 $), 11 des 14 derniers ticks factures hors
`omniroute` (~0,097 $). Meme mecanique : la sonde de :01 met `gemini-3-flash-preview` en `429 cooling down`
et sature le worker NIM (`503 ResourceExhausted: Worker local total request limit reached (16/16)`) ;
l'appel de controle `{"model":"eco"}` fait juste apres le probe rend alors `503` (~2 s, `decisions=3`) avant
un `200` servi par la cible NIM 1-2 min plus tard. Ne pas conclure au combo casse : attendre 2-3 min et
re-sonder. Deux causes cote Hermes a verifier dans ce cas : (1) `jobs.json` porte `model_snapshot: eco` mais
`provider_snapshot: custom` alors que la config nomme le provider `omniroute` ; (2) `config.yaml` peut avoir
derive en `model.default: deepseek-flash` / `provider: deepseek` (PAYANT) avec `eco` en simple
`fallback_providers` — l'inverse de la regle « gratuit d'abord ». Remonter ces deux points, ne pas les
corriger en silence : une modification de `model.default` change le fournisseur de TOUTES les sessions.
Cout mesure : sur un appel `eco`, le log ecrit exactement 3 x `AUTH No credentials for auto` puis
`Trying model 1/6:gemini/...` — filtrage pre-dispatch, latence ~0 ms. C'est du poids mort et du bruit,
pas une panne de latence : ne pas conclure a un combo casse a cause de ces lignes 40. Les 3 cibles
REELLES restent `gemini/gemini-3-flash-preview` + les 2 NIM : quand gemini prend un
`Model-only lockout ... 429 rate_limited 21s`, la priorite retombe sur la cible 2 et le combo repond
toujours `200` en ~3,4 s (verifie le 2026-09-17).

**Un `503` NIM peut venir de l'UPSTREAM, pas du proxy local — ne pas chercher un consommateur.**
Mesure 2026-09-22 06:05Z : appels `{"model":"eco"}` en `503` (`Worker local total request limit reached
(16/16)`, compteur monte a `221/16`) alors que `data/nvidia/proxy.log` ne bougeait plus (**0 requete en 30 s**,
mesure avant/apres par comptage d'octets) et qu'un appel **DIRECT** a `https://integrate.api.nvidia.com/v1`
avec la cle du poste rendait `503` en **0,42 s**. C'est la cle NIM qui a epuise sa limite de requetes cote
fournisseur : relancer le proxy ou le gateway ne sert a rien, et il n'y a pas de consommateur concurrent a
chercher. Consequence de disponibilite : quand `gemini-3-flash-preview` est en `429 all 1 active accounts
cooling down` (pool = 1 compte) **et** NIM en limite upstream, `eco` n'a **aucune cible vivante** -> le tick
horaire part sur le payant. Prudence sur la sonde : un probe qui enchaine 17 candidats juste avant un appel de
controle ajoute ses propres requetes NIM a la fenetre ; ne pas conclure d'une rafale `503` sur la sante du combo.

**Le plafond gemini free tier est JOURNALIER (20 requetes), pas un simple cooldown.** Le 429 porte le
detail : `Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests,
limit: 20, model: gemini-3-flash` (pool = 1 compte, aucune rotation). Consequence : la sonde horaire touche
gemini a chaque passe et consomme elle-meme ce plafond ; une fois les ~20 requetes du jour brulees, la
route reste fermee jusqu'au lendemain et les `resets` annonces (14-60 s) sont trompeurs — un
`model_cooldown` qui revient avec un `reset_seconds` toujours court = plafond journalier atteint, pas un
cooldown transitoire. Ne pas enchainer les appels de controle : ils aggravent la consommation.
**La fenetre NIM `16/16` peut rester explosee >8 min** (5 appels espaces de 40-110 s tous en 503,
`reset after 1-35s` reaffiche a chaque fois) : la regle « re-sonder apres 20-90 s » ne suffit pas. Quand
gemini est au plafond journalier ET NIM en fenetre saturee, `eco` n'a aucune cible disponible — mais ce
n'est PAS un combo casse : le probe reste la meilleure preuve de sante (les 3 cibles ont rendu 200 en
73-139 ms, 15 s avant que les deux fenetres se referment). Rapporter « cibles vivantes, quota gratuit
ferme », pas « combo en panne ».

**Attribuer un tick facture : lire `config.yaml` AVANT d'accuser la sonde.** Mesure 2026-09-22 : 9 ticks
consecutifs (01:00->09:00 Paris, jusqu'au tick 09:00) du job `omniroute-eco-autorefresh` en
`deepseek-flash`/`billing_provider=deepseek` (~0,087 $) alors que `jobs.json` porte `model_snapshot: eco`
et que `eco` repond `200` en 1,9-2,9 s (servi par `gemini-3-flash-preview`) : une recidive horaire persistante
n'est PAS un symptome de sonde saturee, c'est le primaire payant qui facture. Cause reelle :
`model.default = deepseek-flash` / `model.provider = deepseek` (**payant en primaire**) avec
`fallback_providers: [omniroute/eco, omniroute/nvidia-stack]` — l'inverse de « gratuit d'abord ». La derive est
datable par les backups : `config.yaml.bak.avant_groq_*` (default=eco/omniroute) -> `bak.reconfig_*`,
`bak.avant_openrouter_*`, `bak.fix_omniroute_*` (default=gemini-*/google, gratuit) -> `bak.primary_eco_20260922_001147`
(default=deepseek-flash/deepseek), fichier vivant mtime 00:44. Les ticks servis en `gemini-*`/`billing_provider
None` sont ceux d'avant la bascule : comparer l'horodatage des sessions a celui des backups avant d'attribuer
la facturation a la saturation NIM. **Corollaire** : quand `model.default` est deja le payant, le job `eco`
facture a chaque tick quoi que fasse la sonde — le diagnostic « la sonde sature NIM » n'explique alors qu'une
partie des faits (les `503`). Remonter la derive telle quelle (le corriger change le provider de TOUTES les
sessions), avec le geste exact : `python - <<` non — editer par iteration ligne a ligne (voir « Editing Hermes
config.yaml safely ») puis valider `model.default == eco` et `fallback_providers == [nvidia-stack, deepseek-flash]`.

Etat du pool gratuit (verifie 2026-09-17) : tout `oc/*` et `opencode/*` renvoie
`403 OpenCode's free tier can only be used from within OpenCode` (ou `402 requires an
opencode API key`) — le pool gratuit OpenCode n'est plus exploitable via OmniRoute.
Les seules routes gratuites vivantes sont Gemini (cle perso) et le proxy NIM local.
Un tick sain peut afficher **2/17** sans que rien ne soit casse : si `gemini/gemini-3-flash-preview`
prend un `429 All credentials ... are cooling down` pendant la sonde (echec transitoire, compteur non
incremente), seules les 2 cibles NIM passent et le script rend `changed=false` avec `eco` intact a 3
cibles ; l'appel de controle `{"model":"eco"}` rend alors `200` servi par
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` (cible 2). Lire `alive`/`changed` ensemble : un vivant en
moins n'est pas un signal d'elagage tant que `pruned_from_eco` est vide.

Mesure de reference d'un tick sain (2026-09-17 22:01) : **3/17 candidats vivants** = exactement les
3 cibles d'`eco`, `changed=false`, 14 morts. Deux candidats sont des cibles mortes **definitives**
qui ne servent qu'a bruyamment echouer : `gemini/gemini-2.5-flash` et `gemini/gemini-2.5-flash-lite`
(`404 ... no longer available to new users`, retires du catalogue) — a retirer de `CANDIDATES` si l'on
veut reduire la sonde ; `zc/glm-5.3` (`502 spawn zcode ENOENT`, binaire local absent) et
`cloudflare-ai/*` (`502 requires an Account ID`) ne comptent pas comme echecs terminaux.

## eco auto-refresh (cron `omniroute-eco-autorefresh`, horaire)

`~/AppData/Local/hermes/scripts/probe_omniroute.py` (job `5c9dd16aaa37`) probe les
modeles gratuits et maintient le combo `eco` (modele par defaut de Hermes).

- Le script est **additif + elagage** : il ajoute en tete les modeles nouvellement vivants absents du
  combo, et ne retire une cible qu'apres **N echecs consecutifs a code TERMINAL** (`401/402/403/404` =
  acces ferme ou modele retire du catalogue). Un modele qui rate un probe est souvent juste rate-limite :
  les echecs **transitoires** (`429` cooldown, `502/504`, timeout, `200` a contenu vide) n'incrementent
  pas le compteur et ne le remettent pas a zero — **seul un succes remet le compteur a zero**. Reference :
  `PRUNE_AFTER = 3`, etat persistant dans `data/omniroute/probe_omniroute_state.json` (hors depot git :
  `data/` est ignore), donc les compteurs survivent entre deux passages horaires.
- **Les compteurs `terminal_failures` ne concernent que les membres d'`eco`.** Un modele mort du pool
  qui n'est pas dans le combo accumule un compteur qui monte indefiniment (mesure 2026-09-18 : 40-45
  echecs terminaux sur 12 candidats hors `eco`) sans jamais declencher d'elagage — c'est normal, pas un
  bug du garde-fou. Un tick sain reaffiche donc `changed=false` avec des compteurs eleves ; ne pas
  conclure que le job est bloque.
- **Plancher obligatoire** : refuser tout elagage qui ferait descendre le combo sous `FLOOR_MODELS = 2`
  cibles, et evaluer ce plancher sur la liste **fusionnee** (pas sur les seuls vivants du moment). Sans
  ce garde-fou, un elagage agressif reproduit le scenario catastrophique decrit juste apres (combo reduit
  a 1 cible -> tout le trafic part sur le fallback payant).
- **Tester l'elagage sans attendre N heures** : relancer le script N fois de suite simule N ticks ; relire
  ensuite `GET /api/combos` (nombre de cibles) et le fichier d'etat (compteurs par modele). **Ne pas
  enchainer une rafale puis conclure sur un `503`** : plusieurs passes en quelques minutes saturent les
  quotas gratuits et le combo repond `503 all targets were skipped by pre-dispatch filters` pendant
  quelques minutes — re-sonder 2-3 min plus tard avant de declarer le combo casse. Cadence prevue :
  1 passe/heure.
- Interdit : reconstruire `eco` a partir des seuls modeles "vivants du moment".
  Si aucun ne passe le seuil (tous rate-limites), `eco` tombe a 1 modele, celui-ci
  echoue aussi et **tout le trafic Hermes part sur le fallback payant DeepSeek**.
  Symptome : `POST /v1/chat/completions {"model":"eco"}` -> `504 ... requestQueue.maxWaitMs`.
  Reparation : `data/omniroute/restore_eco_20260912.py` (backup + PUT 10 modeles gratuits verifies).
- **Lire `Worker local total request limit reached (N/LIMIT)` comme une FENETRE de quota, pas comme un
  plafond de parallelisme.** Le numerateur depasse largement le denominateur quand la fenetre est
  explosee : mesures `551/16` et `221/16`, alors qu'un appel isole sur le meme modele rend `200` en
  ~1 s dans la minute qui suit. Ce n'est donc ni un probleme de concurrence, ni le proxy NIM local
  (:20200, `ThreadingHTTPServer`, aucun plafond interne), ni les cibles du combo : c'est le quota par
  cle/modele cote NVIDIA, et relancer le proxy ou le gateway n'y change rien. Ne pas elaguer la cible
  ni toucher au combo : re-controler apres 20-90 s, un appel de controle `eco` peut rendre `200` deux
  fois puis `503` une fois sans que rien ne soit casse.
- **Discriminer plafond de concurrence / fenetre de quota en un test : 3 appels en PARALLELE en direct
  sur le proxy** (`POST http://127.0.0.1:20200/v1/chat/completions`, meme modele que la cible suspecte,
  lances en tache de fond puis `wait`). Mesure : `1 x 200` + `2 x 503` a ~0,2 s avec un numerateur deja
  tres au-dessus du plafond = fenetre de quota amont ; trois `503` immediats sur un compteur proche du
  plafond = plafond de concurrence local. Ce test tranche mieux qu'une serie d'appels sequentiels, qui
  peut tous passer sur une fenetre deja saturee.
- Pas de seuil de latence pour declarer "vivant" : `200` + `content` non vide suffit
  (les modeles froids repondent en 5-12 s et sont parfaitement utilisables).
- Sonde avec `max_tokens >= 200`. Avec un budget minuscule (5-10), les modeles
  "reasoning" mettent tous les tokens dans `reasoning_content`, OmniRoute rejette
  en `502 ... failed quality validation` et le probe conclut a tort "mort".
- `providerId` : `oc` pour `oc/*`, `opencode` pour `opencode/*`, `auto` pour
  `auto/*` (convention du combo `eco-fast`, verifiee fonctionnelle).
- **Le pre-run script du job execute DEJA `probe_omniroute.py` : ne pas le relancer dans la meme fenetre.**
  Le job cron `omniroute-eco-autorefresh` lance la sonde avant l'agent ; son stdout (`probe done: N/17 alive`,
  `eco unchanged: ...`) et le mtime de `%TEMP%\omniroute_probe_result.json` datent le tick. Relancer le script
  a la main quelques minutes plus tard = 2 passes pour un seul tick horaire : quotas gratuits satures, `eco`
  en `503 all targets were skipped` pendant quelques minutes et trafic Hermes renvoye sur les cibles 128 K ou
  sur le payant. Verifier la fraicheur du resultat (`ls -la %TEMP%\omniroute_probe_result.json` + `cron/executions.db`,
  (entree `running` sur le job) avant toute re-execution, et se contenter d'un appel de controle `{"model":"eco"}`.
  - **Le probe sonde AUSSI les cibles d'`eco`, a chaque passage.** `CANDIDATES` contient
    `gemini-3-flash-preview` et les 2 cibles NIM, et la phase 1 les teste toutes
    (`ThreadPoolExecutor(max_workers=4)`) : le job consomme donc lui-meme le quota des cibles dont `eco`
    depend, et l'auto-saturation est **structurelle**, pas un accident de diagnostic. Ne pas « nettoyer »
    ces entrees : la phase d'elagage ne voit un membre mourant que s'il figure dans `CANDIDATES` —
    retirer un membre d'`eco` de la liste desarme l'elagage. Arbitrer explicitement (espacer le tick, ou
    sonder les membres moins souvent) et le dire a l'utilisateur.
  - **Le champ `script` d'un job cron est resolu sous `<HERMES_HOME>\scripts\`**
    (`hermes_cli/cron.py`, `_scripts_dir_for_cron` / `_script_health_issue`) : un `script: probe_omniroute.py`
    sans chemin designe `%LOCALAPPDATA%\hermes\scripts\probe_omniroute.py`, pas la copie du projet. Le
    prouver avant d'editer, et apres toute edition verifier que le fichier reste dans ce dossier (un
    script hors de `scripts/` remonte `script resolves outside ...` dans le health check du job).
    Verifier aussi qu'aucun AUTRE job ne cite les noms de candidats retires (`grep` du `jobs.json`) avant
    de conclure que l'elagage de la liste est sans effet de bord.
- **Le script ne `PUT` `eco` que si `changed`** (nouveau modele vivant, ou elagage effectif) : le
  champ `updatedAt` du combo date donc le **dernier changement**, pas le dernier tick. Un `updatedAt`
  vieux de plusieurs heures est normal et ne prouve **pas** que le job n'a pas tourne — croiser avec
  `cron/executions.db` (entree `completed` sur la fenetre). Inversement, toute assertion « combo
  inchange » doit etre **horodatee** (ou prise juste apres lecture) : attribuer un ecart a sa propre
  session sans comparer `updatedAt` est une erreur de diagnostic.

## Cles API dediees (isolation par consommateur)

Une cle par consommateur plutot que la cle du poste : degats bornes, usage attribuable, revocation
ciblee. `GET /api/keys` liste (`keys[]`, plus `allowKeyReveal`) ; `DELETE /api/keys/<id>` supprime.

- **`POST /api/keys` n'applique PAS `allowedModels`.** Il repond `201` avec la cle (et echoit
  `allowedConnections`), mais la relecture donne `allowedModels: []` — aucune restriction, alors qu'on
  croit l'avoir posee. La portee se pose par **`PATCH /api/keys/<id>`** (`{"allowedModels": […]}` →
  `200`), puis se **verifie par relecture**, jamais sur le retour de creation.
- **La liste doit nommer les modeles REELLEMENT dispatches, pas les alias du combo.** Un combo
  autorise sous son seul nom produit `503 all targets were skipped by pre-dispatch filters` (le filtre
  s'applique aux cibles, avant dispatch) ; le modele concret absent de la liste produit
  `403 Model "…" is not allowed for this API key`. Donc : autoriser l'alias **et** les membres
  concrets des combos concernes.
- **Une cle restreinte perd ses cibles des que la rotation sort de sa liste — l'echec est un `503`.**
  Une cle dont `allowedModels` n'est pas vide passe en `modelAccessMode: restricted` : le filtre
  s'applique aux **cibles resolues**, avant dispatch, alors qu'un alias `auto/*` resout sa cible a chaque
  appel dans un pool de plusieurs centaines de modeles. Diagnostic : la reponse porte `poolSize` non nul
  avec `attempted: 0` et `terminalReason: all_targets_skipped` — ca ressemble a une panne de pool et ca
  revient par vagues. Correctif : autoriser l'alias **et** les cibles concretes vivantes du pool, ou
  rendre le modele determineste (un combo dont tous les membres sont autorises, p. ex. `nvidia-stack`).
  Verifier aussi les **replis** : un `fallback_model` absent de `allowedModels` echoue en `403`.
- **Le jeton n'est lisible qu'a sa creation.** `POST /api/keys` renvoie la cle en clair une seule fois ;
  ensuite `GET /api/keys` la masque (champ `key` tronque, `allowKeyReveal: false`) et `keyPrefix` derive
  du `machineId` — deux cles differentes peuvent donc partager leur prefixe, ce n'est pas un doublon.
  Consequence pratique : creer la cle **et** la poser chez son consommateur dans le meme appel.
- Preuve de portee, cote client : `GET /v1/models` avec la cle restreinte n'annonce que les modeles
  autorises. C'est la verification la plus lisible qu'une restriction est bien active.
- **Sonder une API d'ecriture avec un corps bidon cree quand meme l'objet.** Un `POST` incomplet peut
  repondre `201` au lieu de `400` : lire la reponse avant de la boucler, et supprimer l'objet parasite
  (`DELETE`) en le signalant.

## Un alias `auto/*` en PRIMAIRE Hermes : mesurer avant d'y croire

Un alias `auto/*` repond `200` en appel direct **quand son pool contient encore un membre vivant** — ce
n'est pas une garantie. Mesure 2026-09-22 : `auto/best-free` -> **502 sur 3 tirs** (dont un apres 150 s
de retombee de quota), `diagnostics.poolSize = 38` mais `attempted = 6` et tous morts
(`oc/deepseek-v4-flash-free` + `oc/north-mini-code-free` en `400 Model is unavailable`,
`oc/muse-spark*` + `oc/big-pickle` en `403 OpenCode's free tier can only be used from within OpenCode`,
`felo/*` en `400 Felo thread creation failed`, `cloudflare-ai/*` `exhausted`). **Un `200` sur un alias ne dit RIEN de son cout** : le meme jour `auto/best-reasoning` -> `200`
(amont `gemini-3.5-flash` sur un tir) s'est revele resoudre sur `openrouter/anthropic/claude-opus-5`
puis `claude-sonnet-5` sur les autres tirs — des modeles PAYANTS (voir « Un alias `auto/*` peut etre
PAYANT et bruyant »). Ne pas deduire l'etat d'un alias de `/v1/models` (il y figure toujours) ni de son
nom : sonder `POST /v1/chat/completions
{"model":"auto/<alias>"}` **2-3 fois**, apres une retombee de quota, puis **lire le champ `model` de la
reponse ET `~/.omniroute/call_logs/<date>/*.json`** (l'alias s'y journalise sous le modele RESOLU, jamais
sous l'alias : chercher par fenetre horaire) avant de l'inscrire ou non dans `config.yaml`.

**Cout mesurable d'un primaire mort : +25 s par tour.** Meme prompt, `state.db` comme juge :
primaire `eco` -> `pong` en **8,5 s** ; primaire `auto/best-free` (mort) -> **34,7 s** et la session est
facturee `model = eco` (l'etage 1 a servi). Aucune erreur visible cote utilisateur : seul
`session_model_usage.model` / `billing_provider` revele que le primaire n'a jamais servi. Donc :
mesurer, remonter, et proposer un primaire vivant plutot que de laisser la config « au cas ou ».

**Sonder un modele de raisonnement avec `max_tokens` minuscule fabrique un faux 502.** Avec
`max_tokens: 12`, `auto/best-reasoning` rend `502 ... reasoning consumed 8/8 tokens — no content output`
(« failed quality validation ») : le modele a bien repondu, mais tout son budget est parti en
`reasoning_content`. Reprendre la sonde a `max_tokens >= 256` avant de declarer la route morte
(regle deja connue du probe : « Sonde avec `max_tokens >= 200` »).

**Un probe de modeles peut TUER le daemon — et le controle qui suit ment.** Mesure 2026-09-22 :
rafale de sondes sur des alias `auto/*` -> port 20128 ferme (plus de `LISTENING`, PID du fichier
`~/.omniroute/server/.pid` perime), puis relance `wscript.exe //B
"%LOCALAPPDATA%\hermes\omniroute-launch.vbs"` -> `LISTENING` apres ~45 s. Le premier appel de controle
`{"model":"eco"}` a rendu `503 ResourceExhausted: Worker local total request limit reached (16/16)` en
**59 s** : ce 503 etait cause par la rafale elle-meme (fenetre de quota NIM), pas par le combo — apres
150 s d'attente, `eco` -> `200` (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`). Toujours re-sonder
apres une attente avant de conclure.

## Ajouter une connexion provider + un combo par script (recette REST verifiee)

L'OpenAPI embarquee est la source de verite des schemas : `dist/docs/openapi.yaml` (aussi servi sur
`/api/...`), et le CLI l'expose sans deviner : `omniroute api providers post-api-providers --help`,
`omniroute api combos --help` (corps brut via `--body <jsonOrPath>`).

`ProviderConnectionCreate` **exige `provider` ET `url`** (`apiKey`/`name`/`isActive`/`maxConcurrent`
optionnels) — omettre `url` fait echouer la creation. Exemple verifie (OpenRouter, 2026-09-22) :

    POST /api/providers  {"provider":"openrouter","name":"OpenRouter",
                          "url":"https://openrouter.ai/api/v1","apiKey":"<cle>","isActive":true}
    -> 201, corps envelopee dans {"connection": {...}} : lire d["connection"]["id"], pas d["id"].
    POST /api/providers/{id}/test -> {"valid":true,"latencyMs":218} = cle valide.
    GET  /api/providers/{id}/models -> {"provider","connectionId","models","source"} : catalogue live.

**Le prefixe de routage est le type de provider**, pas le nom de la connexion : une connexion
`openrouter` expose ses modeles en `openrouter/<id upstream>` (`providerId` reste a renseigner dans les
entrees de combo). Meme regle que pour le proxy NIM (`openai/nvidia/...`).

**Les ID de modeles se verifient dans le catalogue live, jamais de memoire.** OmniRoute repond
`400 Model '<id>' is not available in the active live catalog for provider '<p>'` quand le modele a
disparu en amont : c'est une reponse nette, pas un incident. Mesure 2026-09-22 : `qwen/qwen3-coder:free`
et `deepseek/deepseek-r1:free` n'existent plus alors que le nom circulait encore ; seuls 21 modeles
`:free` subsistaient. Toujours `GET /api/providers/{id}/models` (ou filtrer `/v1/models`) avant
d'inscrire un modele dans un combo, puis sonder en vrai chaque membre.

**Creer un combo** : `GET /api/combos` (backup JSON dans `~/.omniroute/backups/` avant ecriture),
puis `POST /api/combos` avec `{name, models:[{id,kind:"model",model:"<provider>/<id>",providerId,weight:0}],
strategy:"priority",config:{...copie d'un combo existant...}}` -> **201**. Convention d'`id` d'entree :
`<combo>-NN-<provider>-<modele, / remplaces par ->`. Tester le combo **par son nom**
(`{"model":"<combo>"}`) 2-3 fois : en `priority`, tous les membres ne servent pas forcement (un membre
recemment sollicite peut passer la main) — c'est normal, pas une panne.

## Generations longues : ce qui tue une requete de 12 K tokens

Trois plafonds distincts, tous invisibles sur une sonde courte « pong ». **Un
combo qui repond `200` en 2 s sur une sonde peut etre inutilisable pour un vrai
travail** : ne jamais deduire la sante d'une route d'une sonde courte.

| Chemin | Plafond | Symptome |
|---|---|---|
| OmniRoute (`eco`, `nvidia-stack`, `free-openrouter`) | `requestQueue.maxWaitMs=15000`, applique **apres dispatch** | `504 ... Request exceeded OmniRoute's local rate-limit execution expiration` |
| Proxy NIM local :20200 | `timeout=120` du `urlopen` amont | `502 {"error": "The read operation timed out"}` a ~120,1 s |
| NIM amont direct, mode bloque | passerelle NVIDIA | `504` **corps vide** |

- **Le streaming debloque le chemin direct.** La MEME requete (prompt 12 K
  tokens, sortie longue) qui rend `504` en mode bloque passe en `stream: true` :
  les octets arrivent en continu, plus de coupure a l'echeance. Reassembler le
  SSE cote client (`delta.content`) avec son propre timeout de lecture.
- Le proxy local force `stream=false` : il ne peut donc servir aucune reponse
  longue, quel que soit le quota disponible. Pour ces cas, appeler l'amont en
  direct (`https://integrate.api.nvidia.com/v1`, cle `NVIDIA_API_KEY_GEMMA4` de
  `data/nvidia/.env` — c'est le proxy qui la charge, un appel direct n'exige
  aucune auth locale).
- **Un flux SSE peut porter une erreur avec un statut HTTP 200** : un chunk
  `{"error": {...}}` suivi de `[DONE]` en 0,6 s. Sans lecture de ce champ,
  l'echec se lit « reponse vide » et la cause reelle (ici `ResourceExhausted:
  Worker local total request limit reached (16/16)`) est perdue.

### Un alias `auto/*` peut etre PAYANT et bruyant

Mesure du 22/09 : `auto/best-reasoning` resout vers
`openrouter/anthropic/claude-opus-5` puis `claude-sonnet-5` (274 jetons d'entree
par tour) — ce n'est PAS une route gratuite. Et une seule requete declenche un
fan-out de 30+ tentatives journalisees `virtual-auto-smart-<n>-<provider>`
(openrouter, gemini, openai, felo-web...), la plupart en 404/402/422, avec 1 tir
sur 3 qui ne repond jamais (timeout 120 s).

- Le suffixe dit la contrainte : `auto/best-free`, `auto/coding:free` sont
  contraints au gratuit, `auto/best-reasoning` / `auto/reasoning:pro` ne le sont
  pas. Ne jamais supposer le cout d'apres la famille de l'alias.
- Pour un primaire gratuit, mesurer un modele NOMME ou un combo nomme :
  `eco` (3/3 + prompt de 57 K car. en 5,1 s), `nvidia-stack` (3/3 + 17,5 s).
- **Diagnostic** : `~/.omniroute/call_logs/<date>/*.json`. Un alias `auto/*` s'y
  journalise sous le modele RESOLU, jamais sous l'alias — chercher par fenetre
  horaire, pas par nom. `summary.comboExecutionKey` (`virtual-auto-smart-N-...`)
  identifie le fan-out, `summary.tokens` donne ce qui a reellement ete consomme
  (0/0 = echec avant generation).
- Une sonde courte ne suffit pas : tirer la cible 3 fois et ajouter un prompt de
  taille reelle (~45-57 K car.) — c'est la seule facon de voir le fan-out et les
  timeouts, tous absents d'un appel isole.

### Deux 429 qui n'ont rien a voir

| Message | Niveau | Conduite |
|---|---|---|
| `Model-only lockout for <provider>:<model> — 429 rate_limited 3s (failureCount=N)` | modele | transitoire : reessayer, le cooldown de 3-6 s retombe |
| `[RATE-LIMIT] <provider>:<connection> — 429 received, pausing for 60s` avec `All credentials for model X are cooling down (reset after Ns)` qui se RE-ARME a chaque essai | **compte** | palier gratuit du JOUR consomme : arreter de boucler. Dater la saturation (`grep -c "RATE-LIMIT] openrouter"`) avant de parler de panne |

Un 429 qui met 30-40 s a repondre = relances internes du routeur, pas un modele
lent : mesurer le temps de reponse, pas seulement le code HTTP.

### Gemini : « cooling down » peut etre une erreur de budget

`EMERGENCY_FALLBACK gemini/... -> nvidia/... | reason=Budget error detected
('billing') → emergency` dans `app.log`. Le message renvoye par l'API (« All
credentials ... are cooling down (reset after 56s) », `credentials_cooling: 1`)
fait croire a un cooldown d'une minute. La cause est un quota gratuit
JOURNALIER epuise : 150 s sans aucune requete ne le font PAS retomber, alors
qu'une route reellement limitee par minute revient toute seule. Croiser avec
`app.log` avant de conclure, et ne pas facturer d'attente fondée sur le
`reset_seconds` annonce.

## Recommended Workflows

- **Silent Launch**: Use `omniroute-launch.vbs` to launch the server without a visible console window.
- **Model Discovery**: Use the `omniroute-auto-update` skill to discover and apply free models periodically via `/api/combos`.

## Diagnostics & API
- **API Endpoints**: Use `/api/combos` for management (requires Bearer token) and `/v1/models` for inspection.
- **Silent Launch Technique**: See `references/silent-launch-vbs.md`.
- **API Tips**: See `references/api-tips.md`.
- **Adding a new upstream provider (e.g. Minimax)**: See `references/minimax-provider.md`.
- **Brancher un consommateur local** (app qui parle au routeur en OpenAI-compatible, cle dediee posee
  dans SA config, verification de bout en bout) : `references/openai-compatible-consumers.md`.

### Connexion en erreur : lire `/api/providers`, pas la topologie du dashboard

`GET /api/providers` rend `connections[]` avec `testStatus` (`active` / `expired`) et
`providerSpecificData.apiKeyHealth` (`ok` / `warning` / `invalid`). La connexion hors `active` est
l'« Erreur 1 » du dashboard, et **tous ses modeles renvoient la meme erreur** — d'ou l'impression que
les modeles sont casses alors que c'est la cle de la connexion :

| Reponse du modele | Cause | Correctif |
|---|---|---|
| `401 A valid API key is required. Get one at …` | cle de la connexion morte/expiree (`testStatus: expired`) | renouveler cote fournisseur, ou desactiver la connexion **et** retirer ses modeles des combos (sinon le bruit continue). `PATCH /api/providers/<id> {"isActive": false}` desactive sans supprimer (garder la trace) — relire `isActive` pour le prouver, `DELETE` n'est pas necessaire |
| `502 spawn <binaire> ENOENT` | provider adosse a un executable local, sans connexion enregistree : le modele reste au catalogue et rend `0 token` indefiniment | installer/configurer le provider, ou retirer le modele |
| `429 All credentials for model X are cooling down` | quota fournisseur epuise, transitoire | attendre — ne pas conclure a une panne de configuration |
| `404 … no longer available to new users` | modele retire du catalogue cote fournisseur | retirer des combos |

Un modele du catalogue sans connexion pour son prefixe n'est pas « a tester » : verifier d'abord
`GET /api/providers`.

### Taille du pool de comptes : la vraie limite des routes gratuites

Le log écrit `gemini | all N active accounts cooling down for model <m> (reset after Ns)` : le routeur
gère un **pool de comptes par provider** et fait tourner les credentials, donc **un pool de 1 compte
n'a aucune rotation possible** pendant le cooldown — la cible est écartée et le combo retombe sur ses
cibles 128 K (ou sur le payant). C'est ce qui rend une route gratuite « fiable sur petit prompt,
abandonnée en session longue ».

- **Diagnostiquer la taille du pool** : `grep -o "all [0-9]* active accounts cooling down" app.log |
  sort | uniq -c` — le nombre annoncé est la taille **réelle** du pool. Ne pas la déduire du nombre de
  connexions affichées par le dashboard : seule la ligne du log l'annonce.
- **Élargir une route gratuite** : déclarer une **seconde connexion du même provider**, adossée à un
  **AUTRE compte** du fournisseur (`POST /api/providers {"name":"<Prov> Account 2", "provider":
  "<même providerId>", "authType":"apikey", "apiKey":"<clé du second compte>"}`). Une seconde clé du
  **même** compte ne change rien : le quota est par compte, pas par clé.
- **Valider par le log, pas par `/api/providers`** : `all 1 active accounts` → `all 2 active accounts`
  est la seule preuve que la rotation survit à un cooldown (relire après un `429` réel).
- **Aucun réglage du combo dans ce cas** : `eco` continue de pointer `gemini/<modèle>` ; c'est la
  résolution de compte à l'intérieur du provider qui change, pas la liste des cibles.

## Fallback payant — canonique DeepSeek V4.1 Flash

DeepSeek V4.1 Flash (552B MoE, 10/09/2026) — nom canonique `deepseek-flash` (version-less, futur-proof). `deepseek-v4-flash` n'est qu'un alias de compatibilite ; `deepseek-v4-pro` sera route vers Flash apres le 14/09/2026 12:00 Pekin. Toujours configurer `model: deepseek-flash` (pas l'alias) dans `fallback_providers` et dans l'alias `flash:` du config.yaml.
Option B validee : fallback mono-entree `provider: deepseek / model: deepseek-flash` — retirer `omniroute/auto/best-chat` du fallback economise 60s de timeout a chaque echec d'eco. **Mais le mono-entree payant n'est plus la cible** : l'etage gratuit deterministe passe AVANT le payant (voir ci-dessous) — ne garder le mono-entree payant que si aucun target gratuit fiable n'existe, car il facture au premier rate-limit du primaire. Editer via `terminal` (le guard `patch` refuse `~/AppData/Local/hermes/config.yaml`), appliquer sur default ET `profiles/watch/config.yaml` en une commande.

**Mais un repli mono-entree payant facture au premier hoquet du primaire.** Mesure : sur le profil
du bureau (`fallback_providers: [deepseek/deepseek-flash]`), un `hermes -z` de controle a ete servi
par DeepSeek **payant** alors que le primaire `eco` repondait `200` en 2 s en appel direct — l'echec
etait un `429 cooldown` transitoire de la premiere cible du combo, invisible dans les logs de la
session. Intercaler un etage **gratuit et deterministe** (combo local dont toutes les cibles sont
autorisees, p. ex. le combo NIM local) avant l'etage payant : un repli unique payant transforme
chaque rate-limit en facture.

**Prouver l'etage qui a servi, cote Hermes** : le profil garde le modele et le provider factures —
`SELECT id, model, billing_provider, api_call_count FROM sessions ORDER BY rowid DESC LIMIT 1` sur le
`state.db` du profil (lecture en `mode=ro`, le gateway ecrit pendant qu'on lit). C'est cette colonne,
ou le call log OmniRoute, qui dit si une session a coute : la verifier **avant** d'annoncer « test
OK », et signaler la bascule payante comme l'exige la regle « gratuit d'abord ».
Verifier le normaliseur : `hermes_cli/model_normalize.py` doit contenir `deepseek-flash` dans `_DEEPSEEK_CANONICAL_MODELS` et `_normalize_for_deepseek` doit laisser passer `deepseek-flash` tel quel (bug #107389 corrige).

Ne jamais scraper de tokens communautaires — violation ToS et meme pool deja en 429/cooling-down, aucun gain. Ajouter un vrai provider via dashboard OmniRoute (`POST /api/providers`) avec cle API fournie par l'utilisateur. communautaires pour `oc`/`opencode` — ces providers exposent deja le pool `muse-spark`/`big-pickle`/`mimo` en 429 cooling-down, ajouter d'autres tokens ne les dedouane pas et viole le ToS du source.

## Editing Hermes config.yaml safely

- The `patch` tool REFUSES to write `~/AppData/Local/hermes/config.yaml` (security guard on agent modifying Hermes config). Edit it via `terminal` instead.
- NEVER use `sed` block-range substitutions (`/^A:/,/^- B$/c\...`) on this file — multi-line range ends are fragile (a missing boundary matched nothing or swallowed to EOF) and truncated the whole file to a few lines. The failure is silent: file just shrank.
- Edit via Python line-by-line iteration instead: read lines, on a header line skip its indented block (lines starting `  -` or `    `), emit replacement. This is precise and leaves unrelated lines untouched.
- ALWAYS back up `config.yaml` before touching it (rely on the auto-update `.bak.update_YYYYMMDD_HHMMSS` Hermes drops before updates). Restore is trivial when an edit nukes the file; the damaged file is otherwise unrecoverable by hand.
- After editing, validate with `python -c "import yaml; c=yaml.safe_load(open('<path>',encoding='utf-8')); print(c['model']['default'], c['fallback_providers'])"` and confirm the file still has ~its original line count, not a few dozen.
- **Preserver les fins de ligne** : lire et ecrire avec `newline=""` (ou en binaire). Un `open(...).read()`
  en mode texte traduit CRLF -> LF et l'ecriture qui suit normalise **tout** le fichier : ~1 octet par
  ligne en moins, ce qui ressemble a une perte de contenu (`wc -c` qui chute de plusieurs centaines
  d'octets pour 3 lignes ajoutees) et fait perdre du temps en investigation. Comparer le contenu avec un
  diff qui retire les CR (`diff <(sed 's/\r$//' avant) <(sed 's/\r$//' apres)`), et savoir que git
  (autocrlf) stocke en LF et n'affichera pas la conversion : le controle honnete est le diff ligne a
  ligne plus `python -c "import yaml; ..."`, pas la taille du fichier.
- Default Hermes model lives at `model.default` (`auto/best-chat` = premium; `eco` = free) plus per-provider `default_model`. `fallback_providers: []` makes the setup 100% free.
- **Ancrer sur le BLOC, pas sur une ligne — et compter les occurrences avant de remplacer.**
  `provider: deepseek` figure 3 fois dans le fichier : une ancre d'une ligne est ambigue (un
  `replace_all` aveugle toucherait les 3). Ancre sure = le bloc englobant
  (`model:\n  default: …\n  provider: …\n`). Le script d'application doit **refuser d'ecrire**
  (exit non nul) des que `count != 1` et le dire, jamais ecrire « au plus proche ».
- **Prouver l'APPLICATION, pas seulement l'ecriture.** Trois controles, dans cet ordre :
  (1) diff contre le backup + `yaml.safe_load` + nombre de lignes stable ;
  (2) un tour reel (`hermes -z "…"`) qui repond — les processus NEUFS lisent la nouvelle chaine ;
  (3) `hermes gateway restart` puis, dans le log de demarrage du gateway,
  `gateway.run: Model context warmed: <modele> -> <N> tokens (detected)` : c'est cette ligne qui
  prouve que le gateway a charge le nouveau primaire (elle nommait l'ancien avant le redemarrage).
- **Une session DEJA ouverte garde son modele** (lie au demarrage de la conversation) : `agent.log`
  continue d'afficher `model=<ancien>` apres un changement de `model.default` — ce n'est PAS un echec
  de l'edition. Basculer par `/new` (processus neuf), `hermes model` (defaut) ou `hermes -m <modele>`
  (invocation).
- **Mesurer la cible demandee AVANT de l'inscrire.** « Mets X en primaire » ne dit pas que X est
  gratuit : 3 tirs + un prompt de taille reelle (~45-57 K car.), en lisant `model` et `call_logs`.
  Si la mesure contredit la demande (cout, timeouts), la remonter et laisser trancher — ne pas
  inscrire un primaire payant en silence, ne pas non plus substituer un autre modele sans le dire.

## Tuer le daemon par un appel cloudflare-ai (mesure 2026-09-22)

`cloudflare-ai` sans Account ID ne se contente pas de rendre 502 : il leve un
**`unhandledRejection`** qui tue le daemon OmniRoute en pleine passe, ce qui fait tomber
eco ET nvidia-stack d'un coup. Ligne brute :

    2026-09-22T13:34:36.763Z app | [ERROR] [502]: Cloudflare Workers AI requires an Account ID...
    2026-09-22T13:34:36.768Z app | ⨯ unhandledRejection: Cloudflare Workers AI requires an Account ID...

Mitigation reversible : `PATCH /api/providers/<id> {"isActive": false}` sur LES deux
connexions cloudflare-ai (le host en avait deux, `main` et `main-2`), puis relire
`GET /api/providers` et compter les `isActive` pour le prouver. Aucun combo de la chaine
eco ne reference de modele cloudflare-ai : c'est cette verification (les 5 combos) qui
autorise la desactivation. Ne PAS sonder un modele cloudflare-ai pour « confirmer » : la
confirmation est le log, la sonde ne ferait que re-tuer le daemon.

## `POST /api/providers/<id>/test` valide ne prouve PAS que les modeles servent

Mesure 2026-09-22 : les 6 connexions suspectes (`gemini`, `openai` proxy NIM,
`openrouter`, `opencode`, les 2 `cloudflare-ai`) rendaient toutes
`{"valid":true,"latencyMs":116-355}` — et `opencode/claude-fable-5` rendait quand meme
`402 This model requires an opencode API key`, avec un `testStatus` qui ne bascule en
`credits_...` qu'APRES le PATCH. Le test porte sur la connexion, pas sur la route modele :
conclure au niveau modele par un appel reel (`POST /v1/chat/completions`).

## Discriminer un 503 NIM en 3 appels (proxy local vs amont vs combo)

Le 503 `ResourceExhausted: Worker local total request limit reached (16/16)` peut venir de
trois endroits qu'il faut separer avant de toucher au combo :

1. `POST http://127.0.0.1:20200/v1/chat/completions` (proxy local, meme modele) ;
2. `POST https://integrate.api.nvidia.com/v1/chat/completions` avec la cle de
   `data/nvidia/.env` (amont direct) ;
3. `POST /v1/chat/completions {"model":"eco"}` (via OmniRoute).

Mesure 2026-09-22 : les chemins 1 et 2 echouaient PARIELLEMENT (5/6 et 4/6 en 503 dans la
meme minute) tandis que le chemin 1 rendait `200` en 0,94 s avec `content: pong` quelques
secondes plus tard → limite de debit intermittente cote NVIDIA par cle/modele, ni le proxy
(203 lignes de `ThreadingHTTPServer`, aucun plafond local) ni le combo. Le proxy NIM tourne
en chaine cmd -> python -> python : deux PID homonymes, UN seul port tenu — ce n'est pas un
doublon d'instance.

**Vos propres sondes fabriquent les 503 que vous diagnostiquez.** Correlier les grappes
`16/16` d'`app.log` a vos appels de controle : le 2026-09-22 les clusters de 14:32 et
14:34Z correspondaient exactement aux essais de l'agent, et `eco` rendait `200` trois fois
de suite dans une fenetre calme (2,73 / 0,76 / 1,18 s, servi par la cible NIM nano-omni).
Ne pas conclure d'une rafale sur la sante d'un combo : espacer les essais de 20-90 s et
lire `model` dans la reponse.

## Relaunch watchdog — piege TIME_WAIT (no-op silencieux)

`OmniRoute-Watchdog` (toutes les 5 min) et `OmniRoute-AutoLaunch` appellent
`omniroute-launch.vbs` / `.cmd`, qui sortent en no-op si `netstat -an | findstr ":20128 "`
matche. Or les sockets clients en `TIME_WAIT` du process mort matchent aussi : le watchdog
croit le serveur up et ne relance jamais — l'incident ne s'auto-repare pas et tout le trafic
Hermes bascule sur DeepSeek payant.

- Fix (applique le 2026-09-16) : filtrer l'etat, `netstat -an | findstr /i LISTENING | findstr /r ":20128 "`
  dans LES DEUX launchers (`%LOCALAPPDATA%\hermes\omniroute-launch.vbs` et `.cmd`).
- **Un probe reussi ne prouve pas que le gateway est encore vivant a la fin du tick.** Mesure 2026-09-18 :
  sonde a 21:00:45 (3/17 vivants, `changed=false`), daemon mort a ~21:02:42 **sans ligne `Shutdown`**
  (log s'arretant sur `ConnectionRecovery`, juste apres un combo non-eco en 504/500) ; l'appel de
  controle a 21:03:33 rend `WinError 10061` alors que le probe venait de rendre `200`. **Reproduit le
  2026-09-21** : passe du probe a 17:01:05 (2/17 vivants), `LISTENING` disparu a 17:01:42 (log s'arretant
  sur `[ProxyFetch] Direct response-start timeout (30000ms) ... 127.0.0.1:20200`, sans ligne `Shutdown`),
  `eco` refuse en `10061` -> le tick horaire part sur **DeepSeek payant** (`billing_provider=deepseek`
  dans `state.db`, ~0,009 $ ; 3 sessions consecutives facturees deepseek sur la fenetre 15h-17h).
  Relance `wscript.exe //B` -> `LISTENING` de nouveau a ~45 s, `eco` 200 en 2,2-2,6 s. Donc : apres
  avoir verifie la fraicheur du resultat, faire l'appel de controle `{"model":"eco"}` et, s'il est refuse,
  relancer `wscript.exe //B "%LOCALAPPDATA%\hermes\omniroute-launch.vbs"` (idempotent : filtre
  `LISTENING`) puis re-controler (200 + `content` non vide). 45 s suffisent avant que le port ecoute ;
  ne pas attendre le watchdog (5 min) quand le trafic Hermes part sur le payant.
- Diagnostic d'un OmniRoute down : `netstat -ano | grep 20128` -> aucun `LISTENING` (que des
  `TIME_WAIT`) et `~/.omniroute/logs/application/app.log` s'arrete net sans ligne `Shutdown`
  = crash, pas arret propre. Les taches planifiees `LastTaskResult=0` ne prouvent rien :
  le launcher est sorti en no-op.
- Relance manuelle (detachee, sans fenetre) : `wscript.exe //B "%LOCALAPPDATA%\hermes\omniroute-launch.vbs"`,
  puis ~30-45 s avant que `127.0.0.1:20128` accepte. Verification obligatoire apres relance :
  `POST /v1/chat/completions {"model":"eco"}` -> 200 + `content` non vide (un 401 sur `/v1/models`
  prouve seulement que le port ecoute).

## Gateway-down diagnosis (10061-compatible)

Symptom burst in Hermes logs (NOT a model problem):
- `httpx.ConnectError: [WinError 10061] Aucune connexion...refusé` — port closed
- `Auxiliary compression: connection error ... falling back` then `Error code: 402` — context compressor tried `auto` → connection refused → paid fallback → 402. Root cause is the LOCAL gateway being down, not billing.
- `Streaming failed before` — same root cause (gateway not responding).

## NVIDIA NIM Provider — Critical Distinction

**The OmniRoute `dva` provider is NOT NVIDIA NIM** — it's a "Devin Agentic" bridge that fails with `DEVIN_AGENTIC_HOME must be an absolute path inside the bridge sandbox`.

**Real NVIDIA NIM endpoint**: `https://integrate.api.nvidia.com/v1`

User's NIM keys are in `~/AppData/Local/hermes/data/nvidia/.env`:
- `NVIDIA_API_KEY_SVD` — Synthetic Video Detector
- `NVIDIA_API_KEY_SD` — Stable Diffusion
- `NVIDIA_API_KEY_GEMMA4` — Gemma 4 vision (also works for chat models)

**Working models on this account** (via NIM API directly):
- `nvidia/nemotron-3.5-lightning-30b-a3b` — 30B MoE, fast, chat
- `nvidia/nemotron-3-super-120b-a12b` — 120B MoE, chat/reasoning
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` — 30B MoE, reasoning

**Non-working models** (404, not deployed on this account):
- `nvidia/llama-3.1-nemotron-70b-instruct`, `nvidia/llama-3.1-nemotron-ultra-253b-v1`, etc.

**Model alias**: `auto/best-chat` is a dynamic auto-routing alias, not a fixed model. It iterates through models and in testing resolved to `oc/mimo-v2.5-free`. DeepSeek only appears as a paid fallback in `fallback_providers`, never in the normal routing.

### Wiring NVIDIA NIM into OmniRoute (the proxy pattern)

OmniRoute has NO native `nvidia-nim` provider type — `openai`/`pollinations`/`auto`
all REWRITE model names per their own prefix scheme (`nvidia/nemotron-...` →
`openai/nemotron-...`), which NVIDIA NIM rejects (404). It also injects
`prompt_cache_key`, which NIM rejects with 400. The working fix is a **local
proxy** (`data/nvidia/nvidia-nim-proxy.py`, port 20200) that normalizes the
model name (strips router prefixes, re-adds `nvidia/`) and drops unsupported
params before forwarding to `https://integrate.api.nvidia.com/v1`. Full recipe
in `references/nvidia-nim-models.md`.

**Combo `providerId` pitfall**: in a combo's `models[]` entries, `providerId`
must be the provider TYPE string (`"openai"`) — NOT the connection UUID. Using
the UUID yields `ALL_TARGETS_SKIPPED` ("all targets were skipped by pre-dispatch
filters").

**`providerId` alone is not enough — the model NAME must carry the provider prefix the router
resolves on.** OmniRoute picks the provider from the PREFIX of the model string, not from
`providerId`. An entry written `"nvidia/nemotron-3.5-lightning-30b-a3b"` with
`providerId: "openai"` is routed to a provider called `nvidia` that has no credentials:
`401 No active credentials for provider: nvidia` when called by model name, and `502` (with a
nested message) when called by combo name — while the very same model answers `200` as
`openai/nvidia/nemotron-3.5-lightning-30b-a3b`. Rule: write each `models[].model` in the form the
downstream provider expects (for the local NIM proxy: `openai/nvidia/<modele>`), and validate by
calling the COMBO name (`{"model":"<combo>"}`), never only the bare model name — a combo can be
fully wired and still be unreachable from Hermes.

## File Lock Diagnosis Pattern (Windows)

When `rm -rf` fails with `Device or resource busy`:
1. Use Sysinternals `handle64.exe -accepteula "<filename>"` to find which process holds the lock
2. Check the process: `Get-CimInstance Win32_Process -Filter 'ProcessId=<PID>'`
3. For locks from Hermes components (omniroute, guardian): prefer RunOnce at reboot over killing the process

## Python Instance Locking (Anti-Duplicate)

To prevent multiple instances of a long-running Python daemon:
1. Create lock file with PID: `open(LOCK_FILE, 'x').write(str(os.getpid()))`
2. On startup, check lock: if exists and PID alive → exit silently
3. Use `ctypes.windll.kernel32.OpenProcess()` to check PID liveness on Windows
4. Clean up lock in `finally:` block
5. Handle stale locks: if PID dead → delete lock and restart

## Silent Python Wrapper Pattern (VBS)

When scheduled tasks need to run Python without console flash:
- Use `wscript.exe` (not `pwsh.exe` which may flash briefly on some Windows configs)
- Create `.vbs` file: `sh.Run "python.exe script.py", 0, False` (second arg 0 = hidden)
- Register VBS in scheduled task with action `wscript.exe "path/to/launch.vbs"`