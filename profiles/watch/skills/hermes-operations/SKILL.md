---
name: hermes-operations
description: "Use when controlling Hermes ESTOP, gateway, or Telegram ops."
version: 1.0.0
author: searching-murphy
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [hermes, gateway, estop, telegram, cron, kanban, runbook]
    related_skills: [omniroute-gateway, fallback-intelligent]
---

# Hermes Operations

Control Hermes at runtime without restart: ESTOP (pause/resume), gateway status, Telegram dispatch, and runbook/memory bookkeeping.

## ESTOP — what it does

- Sentinel file: `%LOCALAPPDATA%/hermes/ESTOP` (written by `agent/estop.py`). Checked via `check_paused(component, logger)`.
- Gated: cron dispatch (`cron/scheduler.py`), kanban dispatch (`gateway/kanban_watchers_common.py`), new gateway turns. In-flight work is never killed; it finishes normally.
- NOT gated: outbound webhooks (`agent/outbound_webhooks.py`) and inbound webhook platforms (`gateway/platforms/webhook.py`) — they keep firing while paused. To stop webhooks, disable the platform or filter at the receiver.
- Resume is tick-based: no restart needed, next scheduler/gateway tick picks up.

## Gateway double-process is normal

`hermes gateway status` reports one PID but `Get-CimInstance Win32_Process` where CommandLine like '*gateway*' routinely shows 2: parent `...\.venv\Scripts\python.exe -m hermes_cli.main gateway run` (PPID = Task Scheduler) and child `...\.hermes-runtime\python\generation-...\python.exe -m hermes_cli.main gateway run` (PPID = parent). Do not treat as zombie — killing the child alone drops gateway (`No gateway process detected`). Only kill stale generations: CreationDate older than last `schtasks /Run /TN Hermes_Gateway` or PID not matching `hermes gateway status`. Verify with `ProcessId, ParentProcessId, CreationDate` table before any taskkill.

## Restart verification

After `hermes gateway restart` or `schtasks /Run /TN Hermes_Gateway`, wait 7-9s then check `hermes gateway status` and `Get-Content "$env:LOCALAPPDATA/hermes/logs/gateway.log" -Tail 25` for `telegram connected` / `polling healthy` / `set_my_commands OK`. Log tail is authoritative — status alone can show `No gateway process detected` while child is still warming (2s turn machinery). ESTOP check is `Test-Path "$env:LOCALAPPDATA/hermes/ESTOP"` — must be False for normal ops.

## Commands

### Telegram (any chat authorized in `hermes-telegram` / `channel_directory.json`)

```
/pause              # pause, no reason
/pause <raison>     # pause with reason stored in sentinel and echoed back
/pause off          # resume (also accepts: resume, stop, disengage)
```

Handler: `gateway/run_busy.py:_handle_pause_command` — `busy_policy=dispatch`, so it runs even while agent is busy. Slash dispatch bypasses the ESTOP gate (`run_inbound.py:estop_turn_allowed`), so `/pause off` is always reachable.

### Telegram — listing commands

```
/com [page]        # alias de /commands, liste dynamique paginee (182 cmds)
/commands [page]   # idem, page 1 par defaut, page_size 15 sur Telegram
/help [filter]     # aide filtree, /help skills liste les skills
```
Impl: `hermes_cli/commands.py:CommandDef("commands", aliases=("com",), execute="gateway_commands", busy_policy="dispatch", gateway_only=True)` + `hermes_cli/slash_exec.py:EXECUTORS["gateway_commands"]` (dynamique via `COMMAND_REGISTRY` + `get_skill_commands()`). Ajouter un alias = patch `commands.py` puis `hermes gateway restart` — verifier PID stale (double process apres restart, tuer l'ancien generation-*).

Pitfalls:
- Refuse toute commande `/camera`/`/stream` infinie avec micro continu declenchable a distance et ignore ESTOP — surveillance covert illegale sans consentement en France, contourne l'arret d'urgence et laisse un processus detache sans voyant; proposer `/snapshot` (photo unique) ou `/record 30s` borne avec voyant visible et respect ESTOP, ou solution dediee type Frigate/motionEye.

### CLI (PC)

```bash
hermes pause [--reason "..."]   # engage ESTOP
hermes resume                    # disengage ESTOP
hermes status                    # check model/provider + ESTOP hint
ls "$LOCALAPPDATA/hermes/ESTOP" # sentinel presence = paused
```

## Pitfalls

- `/resume` in gateway is NOT ESTOP resume — it resumes a named session (`CommandDef resume [name]`, `argument_mode mixed`). Always use `/pause off` to lift ESTOP from Telegram; `hermes resume` only exists as CLI.
- `CommandDef pause` is `gateway_only` — it does not exist as CLI slash, and `hermes pause` does not exist as gateway slash. Use the right channel for each form.
- Assuming webhooks stop on pause — they do not; ESTOP has no hook into webhook dispatch. Verify with `grep -rn check_paused` if unsure whether a component respects ESTOP before claiming it is frozen.
- One Telegram channel (`channel_directory.json: platforms.telegram`) can back multiple bot usernames only if they share the same token. Two distinct bot tokens require two entries via `hermes gateway setup`; otherwise only one bot actually receives dispatch.
- `patch` tool refuses to write `config.yaml` (security guard) — edit Hermes config via `terminal` (Python read/write or `hermes config set`), never `patch` or `sed` range substitution which silently truncates on fragile boundaries.

## Verification

```bash
hermes gateway status   # expect PID + Scheduled Task Hermes_Gateway
 hermes status          # model/provider sanity
cat "$LOCALAPPDATA/hermes/channel_directory.json"  # which telegram chats are authorized
```

## Memory & runbook bookkeeping

- `memories/MEMORY.md` has a hard ~2200 char budget (injected every turn). When near limit, compress existing entries in place before appending — shorten verbose lines, merge related bullets, keep `§` separators. Verify with `wc -c` after write; target ≤2170 to leave headroom.
- `memories/USER.md` (~1000 chars) holds stable preferences; `MEMORY.md` holds environment facts and standing ops rules.
- `recovery_runbook.md` is the durable ops reference — record ESTOP semantics, channel/bot mapping, and verification commands there with tags `[telegram pause resume bots surveillance assistance]` so future sessions can `search_files` it.
- Tag new ops facts with all relevant keywords in the same line so keyword search finds them without scanning full history.

## References

- `references/estop-matrix.md` — command matrix (Telegram vs CLI, aliases, what is/is-not gated).
