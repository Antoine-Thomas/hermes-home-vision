---
name: surveillance-control
description: "Use when @Omaths2_watch_bot (Bot video) stops responding or when working on webcam/mic surveillance commands."
version: 1.1.0
author: Hermes Agent
license: MIT
---

# Bot de surveillance @Omaths2_watch_bot ("Bot video")

Le bot est **un programme PowerShell autonome**, PAS le profil Hermes `watch`.

## Architecture
- `%LOCALAPPDATA%/hermes/data/surveillance/surveillance.ps1` — le poller du bot (getUpdates) + commandes. C'est LUI le bot.
- `surveillance-launch.ps1` — lanceur idempotent (verifie l'unicite avant de relancer).
- `stealth.ps1` — mute/demute son, ecran on/off (appele par /watch et /stopcam).
- `audio_guardian/guardian.py` — detection bruit YAMNet autonome, envoie video seul (aucune commande ne le controle).
- Le profil Hermes `watch` (`profiles/watch/`) est un agent distinct (skills, cron, memoire) — il N'implémente AUCUNE fonction de surveillance.

## Token — point critique
- Le bot lit son token dans `data/surveillance/token.sec` (46 chars), PAS dans `profiles/watch/.env`.
- `profiles/watch/.env` contient LE MEME token → le gateway multiplexé Hermes essaie aussi de le poller → conflit `watch:telegram` en etat `fatal` (telegram_polling_conflict). C'est ATTENDU : surveillance.ps1 reste le poller unique.
- Verifier la validite : `curl -s "https://api.telegram.org/bot<token>/getMe"` → `401 Unauthorized` = token revoque/rote.

## Commandes (source de verite = $COMMAND_INDEX de surveillance.ps1)
- `/com`, `/help`, `/start` — liste des commandes
- `/watch` — demarre la surveillance (ecran eteint, son coupe, veille bloquee, 1 image/3s + extrait audio 15s/60s)
- `/stopcam` — arrete, retablit son/ecran/veille
- `/video [s]` — video webcam+micro (defaut 15s, max 60s)
- `/photo` — photo unique webcam
- `/status` — etat (active/repos)

## Config codee en dur (surveillance.ps1 lignes ~38-47)
CAMERA=`Microsoft LifeCam VX-800`, MIC=`Microphone (2- Microsoft LifeCam VX-800)`, CHAT_ID=8956868107, INTERVAL=3s, QUALITY=8, AUDIO 15s/60s, VIDEO 15/60s.

## Diagnostic "le bot ne repond plus"
1. `getMe` sur token.sec → `401` = token rote (cause la plus frequente).
2. `getUpdates` → `409 Conflict` = un poller est actif (sain) ; `200 ok result:[]` = AUCUN poller (bot orphelin).
3. Process : `Get-CimInstance Win32_Process -Filter "Name='pwsh.exe'" | Where-Object { $_.CommandLine -match 'surveillance.ps1' }`.

## Reparation
1. Si token rote : copier le nouveau token (valide) dans `token.sec` (backup d'abord). Attention aux espaces parasites (46 chars exactement).
2. Redemarrer : tuer le process pwsh surveillance.ps1 PUIS relancer via `surveillance-launch.ps1` (jamais deux pollers en parallele — un token Telegram n'accepte qu'un getUpdates).
3. Verifier `getUpdates` → 409.

Reference detaillee : repo `Antoine-Thomas/hermes-home-vision` → `docs/COMMANDES_WATCH.md`.
