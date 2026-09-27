---
name: telegram-bot-polling
description: Use when building/debugging Telegram bots via getUpdates.
---

# Telegram Bot getUpdates Long-Polling

Covers the long-polling (`getUpdates`) pattern for Telegram bots in any language
(PowerShell, Python, Node...). The subtle failure modes here are easy to miss and
cause "the bot stopped responding" or "the bot re-fires commands in a loop".

## Core loop (correct pattern)

Use an incrementing offset and confirm every update:

```
offset = 0
loop:
    updates = GET /bot<TOKEN>/getUpdates?offset={offset}&timeout=20
    for u in updates.result:
        handle(u.message.text)
        offset = u.update_id + 1   # <-- this line "confirms" the update
```

`offset = update_id + 1` is what confirms an update. Without it Telegram keeps
re-delivering the same update forever.

## Pitfalls

- **`offset=-1` never confirms.** Many scripts poll with `offset=-1` (or omit offset
  entirely) and never advance it. Result: updates are re-delivered on EVERY poll, so
  one-shot commands (e.g. `/video`) re-fire endlessly. Symptom: a bot that worked
  "before" suddenly spins or floods. Fix: incremental offset as above.
- **`409 Conflict` is a liveness signal, not an error.** Telegram allows only one
  in-flight `getUpdates` per bot. If a probe `getUpdates` returns HTTP 409, the bot
  is actively long-polling — i.e. it IS running. Two concurrent polls on the same bot
  also block each other (the second waits for the first's timeout), so you cannot
  cleanly inspect pending updates while the bot is healthy. A set webhook also blocks
  `getUpdates` with a 409, but a different description (`can't use getUpdates method
  while webhook is active` vs `terminated by other getUpdates request`) — rule it out
  with `getWebhookInfo` (empty `url` = no webhook) before concluding a concurrent poller.
- **`offset=-1&timeout=N` returns only the latest pending update** and confirms
  nothing — fine for a quick "what's pending" peek, never for the running loop.
- **A second Hermes gateway profile hijacks a dedicated bot's token.** If a dedicated
  bot (e.g. `surveillance.ps1`) suddenly "becomes a second chat" — answers everything
  like an assistant instead of only its commands — OR replies "Unrecognized slash
  command /X" to its own commands (the gateway ate the command but has no /X handler,
  while the real bot is down or starved), a second gateway (e.g. `--profile watch`) is
  polling the same token. Confirm with `getMe` — both tokens resolving to the same
  `@username`/id is conclusive; a hash comparison is only valid on the raw token value,
  not the `KEY=value` line. Detect the duplicate declaratively, before any `getMe`:
  `hermes profile list` prints "Profile '<x>' shares its email credential with default: the bot can
  only belong to one profile" when two profiles carry the same token. Then stop the rogue gateway and disable its
  `Hermes_Gateway_<name>` scheduled task. Full procedure in
  `references/windows-surveillance-bot.md`.
- **Un 409 qui survit a ~200 s de retries n'est pas forcement un second poller — verifier le
  MULTIPLEXAGE avant de chercher un process rogue.** Avec `gateway.multiplex_profiles: true`, UN
  gateway sert tous les profils : `hermes gateway list` affiche `veille — served by the default
  multiplexer` / `watch — …`, et les taches `Hermes_Gateway_<nom>` n'existent legitimement pas — donc
  `Get-CimInstance … -match 'profile <nom>'` ne trouve rien et la these du doublon est sans objet.
  Prouver d'abord que les jetons sont distincts (`getMe` sur le `.env` de CHAQUE profil -> `@username`
  et id differents), puis lire `profiles/<nom>/logs/gateway.log` : l'adaptateur integre retente 5 fois
  etalees sur ~200 s (`Telegram polling conflict (n/5) — previous session still held open`) puis
  **abandonne ce profil pour de bon** (`Fatal telegram adapter error for multiplexed profile <nom>
  (telegram_polling_conflict)`) alors que les autres profils continuent de servir. La reprise est
  `hermes gateway restart`, qui re-etablit l'adaptateur — **valable seulement si le concurrent est
  le gateway lui-meme** (tache `Hermes_Gateway_<nom>` oubliee). Si le concurrent est externe au
  poste, le restart ne fait que rejouer le conflit : le diagnostiquer comme ci-dessous. Deux process `gateway run` portant la meme
  `CreationDate` dont l'enfant a pour PPID le parent sont un couple lanceur/enfant, pas deux pollers.

- **Trancher « concurrent local » vs « concurrent externe » : arreter le gateway, puis sonder chaque
  jeton.** Une fois le multiplexage ecarte, l'ordre des operations decide du verdict :
  `hermes gateway stop`, attendre >10 s (le long-poll d'un process tue reste tenu cote Telegram
  quelques secondes — sonder trop tot rend un 409 trompeur), puis
  `curl -s -o /dev/null -w '%{http_code}' "https://api.telegram.org/bot<TOKEN>/getUpdates?timeout=25&limit=1"`
  sur le `.env` de CHAQUE profil — probe LONG (25 s), jamais 3 s : un probe court peut se glisser
  entre deux long-polls du concurrent et rendre un faux 200. 200 = jeton libre ; 409 = un poller le
  tient encore. Un 409 qui
  survit plusieurs minutes gateway eteint n'est pas un residu, c'est un autre consommateur. Localiser
  ensuite : `Get-NetTCPConnection -State Established | Where-Object { $_.RemoteAddress -like
  '149.154.*' }` (plage API Telegram) puis mapper le PID au process. Si seul le PID du gateway
  apparait, et qu'une recherche hors du home Hermes (`search_files`) ne trouve aucun fichier, le concurrent est
  EXTERNE (autre machine, service, deploiement oublie) : rien de local ne peut le corriger, la
  seule issue est la rotation du jeton (BotFather -> Revoke) + bot neuf, valeur posee UNIQUEMENT
  dans `profiles/<nom>/.env`. `getWebhookInfo` (url vide) elimine le cas webhook en une requete.
- **Le compteur de conflit dit si le concurrent est persistant.** `Telegram polling conflict (n/5)`
  qui repart a `(1/5)` apres chaque reconnexion = l'adaptateur se reconnecte avec succes puis se fait
  tuer a nouveau -> concurrent persistant ; une session perimee, elle, escalade 1->5 une seule fois
  sans jamais repartir de 1. Corollaire : `gateway_state.json` peut afficher
  `"watch:telegram": {"state": "connected"}` alors que le log conflicte encore — l'etat alterne
  `connected` / `retrying`, donc un `connected` lu une fois ne prouve pas un profil sain : lire le
  log de l'adaptateur avant de declarer le profil UP.

## Validating a bot without printing secrets

- `getMe` → validates the token and returns username/first_name (`ok=true` + `@username`). It is also
  the **liveness triage** for a leaked token: HTTP 200 = still usable from anywhere, HTTP 401 =
  revoked. Sort the cleanup by that, not by where the token was found.
- Report any token you had to handle as a **fingerprint** — `sha256("id:secret")[:10]` over the whole
  token, `id:` included — in tool output as well as in chat. Hashing the secret alone and comparing it
  to a full-token hash reads as "does not match" when the two tokens are identical: fix the scheme
  before concluding anything.
- `getUpdates?offset=-1&timeout=3` → shows the latest pending update + its `chat.id`.
- To DETECT a concurrent poller, probe with a long `timeout` (25 s), not 3 s: a short probe
  returns `ok` by finishing before the other poller's next long-poll and under-reports the conflict.
- Read the token out of the bot's config via regex; never echo it back to the user.

## See also

- `references/windows-surveillance-bot.md` — full diagnosis/restart playbook for the
  PowerShell + ffmpeg surveillance bot on this Windows tower (OMATHS), including the
  `powershell` vs `pwsh` encoding gotcha and scheduled-task `0xC0000142` diagnosis.
