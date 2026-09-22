---
source_url: siyuan://20260921223640-38gbwri/20260922142451-fh6qw9i
ingested: 2026-09-22
sha256: e11a1c55b4d56e2a370ea3f638763c3205ff9f8a8aa1d23ecfb5397934fbccc2
---

# Primary auto-best-free mesure et derive - 22-09-2026

---
title: Primary auto-best-free mesure et derive - 22-09-2026
date: 2026-09-22T14:24:51+02:00
lastmod: 2026-09-22T14:24:51+02:00
---

# Primary auto-best-free mesure et derive - 22-09-2026

# Primary auto-best-free : mesure et dérive - 22-09-2026

## Changement appliqué (demande utilisateur)

Objectif annoncé : « un meilleur primary que eco ». Config posée via `hermes config set`​ (backup  
​`config.yaml.bak.avant_bestfree_20260922_142257`​), `.env`​ non touché, blocs `providers.groq`​ et  
​`providers.google` conservés :

|Clé|Valeur posée|
| ------| ------------------|
|`model.provider`|omniroute|
|`model.default`|**auto/best-free**|
|`fallback_providers`|`omniroute/eco`​ → `omniroute/auto/best-reasoning`​ → `deepseek/deepseek-flash`|
|`agent.api_max_retries`|3|

`hermes fallback list`​ confirme : `Primary: auto/best-free (via omniroute)`, chaîne de 3 entrées.

## Mesure : `auto/best-free` est une route MORTE (3/3)

Appels directs `POST /v1/chat/completions {"model":"auto/best-free"}`​ → **502 sur 3 tirs** (dont un  
après 150 s de retombée de quota). Membres réellement tentés et leurs causes :

- `oc/deepseek-v4-flash-free`​, `oc/north-mini-code-free`​ → `400 Model is unavailable`​ / absent du catalogue live `opencode`
- `oc/muse-spark-1.2`​, `oc/muse-spark-1.2-contributor-free`​, `oc/big-pickle`​ → `403 OpenCode's free tier can only be used from within OpenCode`​ (ou `402 requires an opencode API key`)
- `felo/felo-chat`​, `felo/felo-search`​, `felo/felo-scholar`​, `felo/felo-social`​ → `400 Felo thread creation failed`
- `cloudflare-ai/*`​ → `exhausted` (pas d'Account ID)

`diagnostics.poolSize = 38`​, `attempted = 6`​, `excluded`​ non vide : le pool est annoncé grand mais les  
membres gratuits sont fermés. Aucun membre de `auto/best-free` ne répond aujourd'hui.

## Preuve : quel étage a réellement servi le tour

`state.db`​ (`session_model_usage`​ / `sessions`​), baseline `rowid = 993` avant le test :

- Test primaire `hermes -z "Réponds uniquement par: pong-best-free"`​ → session  
  ​`20260922_142323_64e942`​ : **model** **​`eco`​**​ **, billing_provider** **​`omniroute`​**​ **, coût** **​`0.0`​**​ — donc le primaire  
  a échoué et c'est l'**étage 1 gratuit (**​**​`eco`​**​ **)**  qui a servi, pas `auto/best-free`​.  
  Latence du tour : **34,7 s** (contre 8,5 s quand `eco` est primaire) = le coût du tir perdu + la  
  bascule.
- `hermes --provider omniroute -m eco -z "ping"`​ → `pong`​ en 8,0 s, `session_model_usage`​ rowid 995  
  (`eco`​ / `custom`).
- `hermes --provider omniroute -m auto/best-reasoning -z "ping"`​ → `Pong.`​ en 8,3 s, rowid 996  
  (`auto/best-reasoning`​ / `custom`).

Conclusion : la configuration est bien posée et la chaîne fonctionne, mais **le primaire ne sertjamais** — il coûte un appel perdu (~2 à 25 s) à chaque tour avant de retomber sur `eco`.

## Incident OmniRoute pendant la session

Le daemon OmniRoute est **tombé** (port 20128 fermé, PID fichier 26832 périmé) après une rafale de  
sondes de modèles — piège documenté (un probe qui tape des cibles à credentials incomplets peut tuer  
le daemon). Relance par `wscript.exe //B "%LOCALAPPDATA%\hermes\omniroute-launch.vbs"`​ → `LISTENING`​  
(PID 12512) après ~45 s. Le contrôle `{"model":"eco"}`​ a d'abord rendu `503 ResourceExhausted: Worker local total request limit reached (16/16)`​ (fenêtre de quota NIM saturée par les sondes elles-mêmes) :  
après 150 s d'attente, `eco`​ → `200`​ servi par `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`.

## Inventaire des connexions OmniRoute (12, lecture `/api/providers`)

Actives : `hermes`​ (gemini, test active) · `NVIDIA NIM (Proxy)`​ (type openai, test unavailable) ·  
​`main`​ (g4f-pollinations, active) · `main`​ + `main-2`​ (cloudflare-ai, actives) · `Compte OpenCode 1`​  
(opencode, active mais tous ses modèles gratuits en 403/402) · `minimax`​ (test **error**, clé  
​`invalid`, 6/6 échecs).

Désactivées : `Pollinations AI`​ (expired), `kiro`​, `freeaiapikey`​, `huggingface`​, `huggingchat`.

**Aucune connexion OpenRouter n'existe dans OmniRoute** — l'étage OpenRouter gratuit du 21/09 est un  
provider Hermes (clé `.env`​), pas une connexion OmniRoute. Un combo « free-openrouter » ne peut donc  
pas être construit sans créer d'abord une connexion OpenRouter (`POST /api/providers`​, clé  
​`OPENROUTER_API_KEY`).

## Recommandation

`auto/best-free`​ étant mort, mettre le primaire sur **​`auto/best-reasoning`​**​ (mesuré `200`​, amont  
​`gemini-3.5-flash`​, 8,3 s en direct) et laisser `eco`​ en étage 1 : la chaîne devient  
​`auto/best-reasoning`​ → `eco`​ → `deepseek-flash`​, sans appel perdu. Alternative si l'on veut du  
« free » strict : garder `eco` en primaire (le comportement mesuré aujourd'hui).

## État des automatismes (non cassés)

Gateway `running`​ (PID 24580, tâche `Hermes_Gateway`​). Profils `default`​ (auto/best-free), `veille`​ et  
​`watch`​ (nvidia-stack) inchangés. 9 jobs cron (7 actifs, 2 en pause), `omniroute-eco-autorefresh`​  
dernier run 14:06 ok, prochain 15:00. Skills : 84 activées, 7 désactivées. Aucune modification de  
​`.env` (contrôle de présence 7/7).
