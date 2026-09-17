# Recovery Runbook — OmniRoute + Hermes (état de référence : 2026-09-08)

But : auto-réparer les pannes fréquentes de la pile "Hermes → OmniRoute → modèles gratuits".
Ce fichier est une référence ; les procédures équivalentes vivent aussi dans les skills
`omniroute-gateway` et `fallback-intelligent`.

## Configuration cible (état sain)

- Hermes model :
    default   = eco
    provider  = omniroute
    base_url  = http://127.0.0.1:20128/v1
- fallback_providers (chaîne de repli) :
    1. {provider: omniroute, model: auto/best-chat, base_url: http://127.0.0.1:20128/v1}
    2. {provider: deepseek, model: deepseek-v4-pro}   ← payant, dernier recours
- Combo "eco" (texte gratuit, strategy priority, modèles CONCRETS) :
    1. oc/muse-spark-1.2-contributor-free   (providerId oc)
    2. oc/big-pickle                        (providerId oc)
    3. opencode/big-pickle                  (providerId opencode)
- Combo "nvidia-stack" (via proxy local 20200, providerId openai) :
    1. nvidia/nemotron-3.5-lightning-30b-a3b
    2. nvidia/nemotron-3-super-120b-a12b
    3. nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
- Vision Hermes : auxiliary.vision → NVIDIA NIM direct
    model = meta/llama-3.2-11b-vision-instruct, clé = NVIDIA_API_KEY_GEMMA4
- Compression : providers.omniroute.extra_headers → X-OmniRoute-Compression: default
- Clés :
    OMNIROUTE_API_KEY      → ~/.omniroute/.env (Bearer pour /api/* et /v1/*)
    NVIDIA_API_KEY_GEMMA4  → %LOCALAPPDATA%/hermes/data/nvidia/.env (+ hermes/.env)
    DEEPSEEK_API_KEY       → %LOCALAPPDATA%/hermes/.env
- Processus :
    OmniRoute   → port 20128 (launcher VBS omniroute-launch.vbs, idempotent)
    NIM proxy   → port 20200 (VBS data/nvidia/nvidia-nim-launch.vbs + tâche planifiée Hermes_NVIDIA_NIM_Proxy ONLOGON)
    Gateway     → hermes gateway restart
- Crons :
    Monitoring vision gratuite → 493da894d8db (chaque heure, no-agent, scripts/monitor_vision.py)
    Relance fin de vacances    → f48b2ebfdd6f (épinglé omniroute/eco)

## Health-check rapide (30 s)

    KEY=$(grep -E '^OMNIROUTE_API_KEY=' ~/.omniroute/.env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d '\r')

    # 1. OmniRoute répond ? (401 = OK, auth requise ; 000 = down)
    curl -s -m 5 http://127.0.0.1:20128/v1/models -o /dev/null -w "%{http_code}\n"

    # 2. combo eco répond ?
    curl -s -m 40 -X POST http://127.0.0.1:20128/v1/chat/completions \
      -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" \
      -d '{"model":"eco","messages":[{"role":"user","content":"dis bonjour"}],"max_tokens":20,"stream":false}'

    # 3. NIM proxy up ?
    curl -s -m 5 http://127.0.0.1:20200/health    # attendu : {"status":"ok"}

## Panne 1 — eco renvoie 503 "all targets skipped" ou 400

Cause A : model.base_url pointe vers Pollinations/OpenRouter au lieu du proxy OmniRoute.
Cause B : le combo eco contient des alias auto/* (auto/best-free...) au lieu de modèles concrets.

Réparation :
1. Vérifier le base_url :
       hermes config get model
   base_url DOIT être http://127.0.0.1:20128/v1. Sinon :
       hermes config set model.base_url http://127.0.0.1:20128/v1
2. Vérifier le contenu du combo :
       curl -s -H "Authorization: Bearer $KEY" http://127.0.0.1:20128/api/combos
   Les modèles d'eco DOIVENT être oc/*-free ou opencode/*-free CONCRETS, jamais auto/*.
3. Si ce sont des alias auto/* : réécrire le combo avec des modèles concrets validés
   (script existant : scripts/fix_eco_combo.py — récupère, sauvegarde, PUT, vérifie).
4. Re-prober les modèles concrets du jour (les -free sont volatils) :
       for M in oc/muse-spark-1.2-contributor-free oc/big-pickle opencode/big-pickle; do
         curl -s -m 35 -X POST http://127.0.0.1:20128/v1/chat/completions \
           -H "Content-Type: application/json" -H "Authorization: Bearer $KEY" \
           -d "{\"model\":\"$M\",\"messages\":[{\"role\":\"user\",\"content\":\"dis bonjour\"}],\"max_tokens\":20,\"stream\":false}" \
           -w "\n[$M HTTP %{http_code}]\n"; done
   Ne garder que les HTTP 200 avec content non vide.

## Panne 2 — tout en 5xx / aucune réponse

1. OmniRoute down (curl /v1/models → 000) :
       wscript //B %LOCALAPPDATA%/hermes/omniroute-launch.vbs
   (ou omniroute-launch.cmd ; idempotent sur le port 20128)
2. Gateway down :
       hermes gateway status
       hermes gateway restart

## Panne 3 — nvidia-stack échoue (502)

Cause : proxy 20200 éteint (ne survit pas au reboot si la tâche planifiée n'a pas tourné).

1. Tester : curl -s -m 5 http://127.0.0.1:20200/health → 000 = down.
2. Relancer :
       wscript %LOCALAPPDATA%/hermes/data/nvidia/nvidia-nim-launch.vbs
   (le script charge NVIDIA_API_KEY_GEMMA4 depuis data/nvidia/.env automatiquement)
3. Vérifier la persistance : schtasks /Query /TN "Hermes_NVIDIA_NIM_Proxy"
4. Attendre l'expiration du backoff (le 502 "exhausted" persiste ~1-2 min après le
   lancement), puis retester nvidia-stack : la connexion "NVIDIA NIM (Proxy)" dans
   OmniRoute repasse à 200.

## Panne 4 — vision en échec

- Vision Hermes (NVIDIA NIM direct). Tester (texte) :
      curl -s -m 30 -X POST https://integrate.api.nvidia.com/v1/chat/completions \
        -H "Content-Type: application/json" -H "Authorization: Bearer $GEMMA4" \
        -d '{"model":"meta/llama-3.2-11b-vision-instruct","messages":[{"role":"user","content":"dis bonjour"}],"max_tokens":20}'
  IMPORTANT : les images doivent être envoyées en data-URI (base64), pas en URL
  externe — les URLs distantes font 500 sur le backend NIM.
- Vision OmniRoute (modèles gratuits) : gérée automatiquement par le cron
  493da894d8db (scripts/monitor_vision.py, chaque heure, watchdog silencieux).
  Dès qu'un modèle vision free (gemini-flash, pol/qwen-vision, oc/gemini, zc/glm…)
  repasse en 200, le script crée/met à jour le combo "vision".
  Journal : ~/.omniroute/vision_monitor.log

## Panne 5 — clé / auth

- 401 sur /v1/* ou /api/* → OMNIROUTE_API_KEY absente/erronée dans ~/.omniroute/.env.
- 401 sur pol/* → Pollinations exige une clé API (inutilisable sans).
- 4xx/500 sur NIM → vérifier NVIDIA_API_KEY_GEMMA4 dans data/nvidia/.env.

## Règles invariantes (ne jamais violer)

- model.base_url pointe TOUJOURS sur http://127.0.0.1:20128/v1 (jamais Pollinations/OpenRouter direct).
- Les alias auto/* (auto/best-free, auto/vision…) s'appellent DIRECTEMENT comme model ;
  JAMAIS comme cibles d'un combo priority → sinon 503 "all targets skipped by pre-dispatch filters".
- Les modèles concrets -free sont volatils : re-prober avant de les remettre en combo.
- Ne PAS supprimer le combo eco : colonne vertébrale gratuite (scripts + cron le ciblent).
- fallback_providers ne se déclenche que sur rate-limit / 5xx / erreur réseau (jamais sur un 400/401).

## Commandes clés

- hermes config get model / fallback_providers
- hermes config set model.<cle> <val> / fallback_providers '<json>'
- hermes cron list / hermes gateway status / hermes gateway restart
- API combos (Bearer) : GET /api/combos, POST /api/combos, PUT /api/combos/<id>, DELETE /api/combos/<id>
- Scripts : scripts/fix_eco_combo.py, scripts/monitor_vision.py

## Commandes pause / resume (Telegram & CLI) [telegram pause resume bots surveillance assistance]

Source: Hermes main @abd83ab560 (08/09/2026). Gateway: hermes-telegram via channel_directory.json. Bots concernés: @Omaths2_watch_bot (surveillance) + @Hermes_assistante_2026_bot (assistance) — tout chat autorisé hermes-telegram fonctionne.

### Ce que fait /pause (ESTOP)
- Écrit le sentinel %LOCALAPPDATA%/hermes/ESTOP (agent/estop.py). Fige NOUVEAU travail uniquement: cron dispatch + kanban dispatch + nouveaux tours gateway en attente. In-flight non tué. Reprise au tick suivant après levée.
- Webhooks sortants (agent/outbound_webhooks.py) et inbound webhook platforms non gatés par ESTOP — pas ‘suspendus’ par /pause. Pour couper les webhooks: désactiver la plateforme ou filtrer côté récepteur.
- Commande gateway_only (CommandDef pause, busy_policy dispatch) mais ESTOP laisse passer les slash commands — /pause off reste toujours joignable même pausé (run_busy.py _busy_pause_command + run_inbound.py estop_turn_allowed).

### Commandes
- Telegram (depuis n'importe quel chat autorisé hermes-telegram):
  - `/pause` ou `/pause <raison>` → pause globale (raison stockée dans ESTOP, affichée dans le reply).
  - `/pause off` (alias: `/pause resume`, `/pause stop`, `/pause disengage`) → lève ESTOP, réponse “Resumed”.
- CLI (PC):
  - `hermes pause [--reason "..."]` → engage ESTOP.
  - `hermes resume` → lève ESTOP (≠ /resume qui est reprise de session nommée).
- Vérifier l'état: `hermes status`, présence de %LOCALAPPDATA%/hermes/ESTOP, logs cron “check_paused”.

### Pièges
- `/resume` en gateway = reprise de session (CommandDef resume [name]), PAS levée d’ESTOP. Toujours utiliser `/pause off` pour reprendre.
- Cli_only vs gateway_only: /pause n'existe pas en CLI slash, hermes pause n'existe pas en gateway slash — passer par le bon canal.

### /com alias de /commands
- `/commands [page]` et `/com [page]` (alias) → liste paginée dynamique de toutes les commandes (182, CommandDef + skills). S'actualise auto. gateway_only, busy_policy dispatch.
- Pagination: `/com 2`, `/commands 2` etc. Aussi `/help` et `/help skills`.
- Impl: CommandDef("commands", aliases=("com",), execute=gateway_commands) dans hermes_cli/commands.py; executor gateway_commands dans hermes_cli/slash_exec.py (page_size 15 sur Telegram).


## Commandes de surveillance legale [telegram pause resume surveillance photo record bots]

Alternative legale au flux infini refuse (/camera infini ignore ESTOP = surveillance covert, illegal, non cree).

- **/photo** (skill photo) : 1 photo unique. Voyant Tkinter rouge 800x60 topmost 1.5s "CAPTURE PHOTO EN COURS". Capture: OpenCV VideoCapture(0) sinon PIL.ImageGrab.grab(). Sauve %LOCALAPPDATA%/hermes/captures/photo_YYYYmmdd_HHMMSS.jpg, envoie MEDIA:. Respecte ESTOP (refuse si %LOCALAPPDATA%/hermes/ESTOP existe, indique /pause off). Script skills/photo/scripts/capture_photo.py.
- **/record [30|60]** (skill record) : video max 60s (defaut 30). Voyant rouge clignotant pendant toute la duree. OpenCV VideoWriter mp4 640x480 15fps -> record_*.mp4, fallback rafale ImageGrab -> gif. Respecte ESTOP, plafonne 5-60s. Script skills/record/scripts/capture_record.py. Usage: /record / /record 30 / /record 60.
- **/status** natif : `hermes status` / `/status` (gateway) = session, model, tokens, contexte. Pour ESTOP/gateway, voir plus haut /pause.
- **/com alias /commands** : liste dynamique 185 cmds (gateway_commands paginee). Ex: /com / /com 2. Apparait dans Telegram menu (60 visibles, reste via /com).

Tests: /photo seul -> 1 jpg. /record 30 -> mp4/gif apres 30s. /pause puis /photo -> refuse (ESTOP). /pause off puis /photo -> OK.
