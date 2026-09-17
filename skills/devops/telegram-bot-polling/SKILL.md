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
  cleanly inspect pending updates while the bot is healthy.
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

## Validating a bot without printing secrets

- `getMe` → validates the token and returns username/first_name (`ok=true` + `@username`). It is also
  the **liveness triage** for a leaked token: HTTP 200 = still usable from anywhere, HTTP 401 =
  revoked. Sort the cleanup by that, not by where the token was found.
- Report any token you had to handle as a **fingerprint** — `sha256("id:secret")[:10]` over the whole
  token, `id:` included — in tool output as well as in chat. Hashing the secret alone and comparing it
  to a full-token hash reads as "does not match" when the two tokens are identical: fix the scheme
  before concluding anything.
- `getUpdates?offset=-1&timeout=3` → shows the latest pending update + its `chat.id`.
- Read the token out of the bot's config via regex; never echo it back to the user.

## See also

- `references/windows-surveillance-bot.md` — full diagnosis/restart playbook for the
  PowerShell + ffmpeg surveillance bot on this Windows tower (OMATHS), including the
  `powershell` vs `pwsh` encoding gotcha and scheduled-task `0xC0000142` diagnosis.
