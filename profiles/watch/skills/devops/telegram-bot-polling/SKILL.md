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

## Validating a bot without printing secrets

- `getMe` → validates the token and returns username/first_name (`ok=true` + `@username`).
- `getUpdates?offset=-1&timeout=3` → shows the latest pending update + its `chat.id`.
- Read the token out of the bot's config via regex; never echo it back to the user.

## See also

- `references/windows-surveillance-bot.md` — full diagnosis/restart playbook for the
  PowerShell + ffmpeg surveillance bot on this Windows tower (OMATHS), including the
  `powershell` vs `pwsh` encoding gotcha and scheduled-task `0xC0000142` diagnosis.
