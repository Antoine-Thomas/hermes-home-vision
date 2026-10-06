---
name: auto-context-reset
description: Traiter une saturation de contexte sans /new manuel.
version: 1
author: hermes-agent
license: mit
metadata:
  hermes:
    tags: [context, compression, saturation, handoff, hooks, devops]
    related_skills: [hermes-agent, omniroute-gateway, hermes-provider-config]
---

# Saturation de contexte : detecter, preserver, reprendre

But : qu'une session saturee ne demande PLUS d'intervention humaine
improvisee. Trois couches, dans cet ordre : la route de compression ne doit
pas etouffer (config), le plugin doit detecter et preserver le travail (hooks),
l'agent doit cloturer proprement (cette procedure).

## When to Use

- Un bloc `<auto_context_reset>` apparait dans le contexte (avis du plugin).
- La compression de contexte echoue ou n'avance plus (`no progress for 300.0s`,
  `stall_interrupted`, cooldown 300 s) et l'utilisateur doit faire `/new` a la main.
- L'utilisateur demande pourquoi une session longue sature ou perd du travail.
- `hermes -z` ne repond pas (primaire de session qui pend) ou un handoff de
  session doit etre produit / relu.

## 1. Signaux a connaitre (mesures reelles)

- Plugin `auto-context-reset` (actif, `plugins.enabled`) : hooks
  `post_auxiliary_call` (tache `compression`), `api_request_error`
  (erreur de fenetre), `pre_llm_call` (injection de l'avis).
- Au tour suivant un incident, le contexte du modele recoit un bloc
  `<auto_context_reset>` : **c'est le signal d'agir**, pas une information.
- Fichiers produits : `<HERMES_HOME>/logs/auto-reset.log` (JSONL, 1 ligne par
  incident + 1 par handoff) et `<HERMES_HOME>/handoffs/<session>_<horodatage>.md`
  (metadonnees de session + derniers messages actifs + commandes de reprise).
- Etat durable cote Hermes, lu en lecture seule dans `state.db` (`sessions`) :
  `compression_failure_error`, `compression_failure_cooldown_until`,
  `compression_fallback_streak`, `compression_ineffective_count`,
  `compression_overload_streak`. Exemple reel :
  `backoff:stall_interrupted:strategy=lean:msgs=102:tokens=129799:model=deepseek-flash`.
- Log de session : `Compression summary call dispatched` puis, en echec,
  `compression made no progress for 300.0s` / `stall_interrupted`,
  `cooldown 300s`.

## 2. Procedure quand l'avis tombe (ou quand l'utilisateur se plaint)

1. **Terminer le travail en cours** jusqu'a un etat coherent ; ne pas laisser
   une mesure a moitie faite ni un fichier a moitie ecrit.
2. **Completer le handoff** (section « Etat du travail ») : chemins ABSOLUS des
   livrables, ce qui est verifie, ce qui reste, les mesures a ne pas refaire,
   les commandes exactes de reprise. C'est ce fichier qui rend le `/new` sans
   perte ; le plugin l'amorce, l'agent le rend utile.
3. **Prevenir l'utilisateur** : la compression a echoue N fois, un `/new` est
   conseille, voici le handoff et la commande de reprise (`hermes -c`).
4. **Ne pas promettre un reset automatique** : aucun hook Hermes n'expose de
   directive de reinitialisation de session (`VALID_HOOKS` dans
   `hermes_cli/plugins.py` : les seuls hooks qui transforment quelque chose sont
   `pre_tool_call` = blocage et `pre_llm_call` = injection de contexte).
   L'agent peut tout automatiser SAUF le `/new`.

## 3. Reparer la cause (config), pas seulement la session

Symptome « la compression ne progresse plus (300 s) » : la route auxiliaire de
compression ne rend rien. Verifier et corriger :

    hermes config get auxiliary.compression
    hermes config set auxiliary.compression.provider deepseek
    hermes config set auxiliary.compression.model deepseek-flash
    hermes config set auxiliary.compression.base_url https://api.deepseek.com/v1
    hermes config set auxiliary.compression.fallback_chain '[{"provider":"omniroute","model":"nvidia-stack"}]'

- `auxiliary.<tache>.fallback_chain` est bien LUE par le client auxiliaire
  (`agent/auxiliary_client.py`, `_try_configured_fallback_chain`) meme si
  `hermes config set` affiche « not a recognized config key ». L'entree exige
  `provider` ; `model`/`base_url`/`api_key` sont optionnels.
- Le plafond de temps d'une compression est **plancher a 300 s**
  (`_COMPRESSION_TIMEOUT_FLOOR_SECONDS`). Le champ `timeout` de la config ne
  peut donc PAS raccourcir une route qui etouffe : la seule protection est de
  choisir un modele qui repond, pas de baisser le timeout.
- La fenetre du modele de compression **rabaisse le declencheur** de la session
  (`context_compressor._apply_threshold_tokens_cap` via `_aux_context_ceiling`) :
  un resumeur a 128 K fait compresser a 128 K meme si `threshold` vaut 0.4 d'un
  modele principal a 1 M. Choisir un resumeur a grande fenetre restaure le
  seuil configure.
- Verifier la route sans session vivante (1 appel reel, 1 a 2 s) :
  `get_text_auxiliary_client("compression")` puis un petit
  `chat.completions.create`. Un modele de raisonnement rend un `content` vide
  si `max_tokens` est minuscule (tout part en `reasoning_content`) : sonder avec
  `max_tokens >= 256`.

## 4. Si le PRIMAIRE de session est en cause

Un `model.default` pointe sur un combo dont la premiere cible pend (mesure
2026-10-05 : combo `eco`, cible `gemini/gemini-3-flash-preview` en 310 s,
0 token, puis 503/504 sur les 2 cibles NIM) : chaque NOUVELLE session paie
l'attente avant que la chaine `fallback_providers` ne bascule. Symptome :
`hermes -z "pong"` ne rend rien en 300 s.
- Le diagnostic et la reparation du combo appartiennent au skill
  `omniroute-gateway` (ne pas reconstruire un combo sur un seul echec ;
  verifier d'abord les quotas — gemini free = 20 requetes/JOUR — et la fenetre
  NIM 16 slots, qui sont partagees avec `nvidia-stack`).
- Changer `model.default` change le fournisseur de TOUTES les sessions :
  le remonter a l'utilisateur, ne pas le faire en silence.

## 5. Commandes de verification

    hermes auto-context-reset status                      # reglages + sessions suivies
    hermes auto-context-reset check                       # journal, handoff, state.db
    hermes auto-context-reset simuler --n 2               # fabrique des incidents + un VRAI handoff
    hermes auto-context-reset simuler --session <id> --n 3   # handoff d'une session passee
    hermes auto-context-reset off|on                      # mode

Tests hors ligne du plugin (33 assertions, aucun reseau) :
`hermes-agent/venv/Scripts/python.exe plugins/auto-context-reset/tests/test_hook.py`.

## Pieges deja payes

- Ecrire `mode: on` dans config.yaml : YAML 1.1 le relit en booleen `true`. Le
  plugin normalise `on/true/yes/1` ; le schema declare `mode: bool` pour eviter
  l'avertissement de validation au demarrage.
- `hermes config set <cle> '"on"'` ecrit `'"on"'` (guillemets litteraux) : pour un
  booleen, ecrire `on`/`off` et laisser la normalisation faire le reste.
- Le `patch` tool REFUSE d'ecrire `config.yaml` : utiliser `hermes config set`
  (et sauvegarder le fichier avant, `config.yaml.bak.<motif>_<date>`).
- `plugins.isolation: host` : `ctx.register_cli_command` est cable dans le CLI
  local, pas dans l'hote ; verifier une commande de plugin par
  `hermes <commande> status`, pas par `hermes plugins show`.
- Un handoff ecrit doit contenir des CHEMINS ABSOLUS : c'est ce qui le rend
  exploitable apres un `/new` (le plugin ne connait que `state.db`).
