# ESTOP / Pause Matrix

Quick reference for `/pause` vs `hermes pause` vs `/resume`.

## Command matrix

| Input | Where | What happens | Alias |
|---|---|---|---|
| `/pause` | Telegram (any hermes-telegram chat) | `estop.engage(reason=None)` — cron+kanban+new gateway turns on hold | — |
| `/pause <raison>` | Telegram | `estop.engage(reason="<raison>")` — reason stored + echoed | — |
| `/pause off` | Telegram | `estop.disengage()` — tick-based resume | `/pause resume`, `/pause stop`, `/pause disengage` |
| `hermes pause` | CLI (PC) | same engage | `hermes pause --reason "..."` |
| `hermes resume` | CLI (PC) | same disengage | — |
| `/resume [name]` | Telegram | resumes NAMED session (CommandDef resume) — does NOT lift ESTOP | `/sessions` to browse |

## What ESTOP gates (checked via `check_paused`)

- `cron/scheduler.py:check_paused("cron", logger)` — skips dispatch, logs once per engagement
- `gateway/kanban_watchers_common.py:check_paused("kanban", logger)` — skips kanban dispatch
- `gateway/run_inbound.py` + `gateway/run_busy.py` — new gateway turns queued/held; slash commands still dispatched (`estop_turn_allowed`)

## What ESTOP does NOT gate

- `agent/outbound_webhooks.py` — no `check_paused` call
- `gateway/platforms/webhook.py` / `webhook_filters.py` — no `check_paused` call
- In-flight agent turns — never killed, always allowed to finish

## Re-verify after any claim

```bash
grep -rn "check_paused\|is_engaged" hermes-agent --include="*.py" | grep -v .venv
cat "$LOCALAPPDATA/hermes/ESTOP" 2>&1  # JSON with reason + timestamp if paused
```
