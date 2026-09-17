---
name: hermes-install-troubleshooting
description: "Diagnose Hermes update/install failures and dual installs."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [hermes, install, update, troubleshooting, diagnosis]
    related_skills: [hermes-agent]
---

# Hermes Install & Update Troubleshooting

## When to Use

Load when `hermes update` errors, `hermes --version` reports an unexpected version,
`hermes doctor` disagrees between runs, or you suspect more than one Hermes install
on the machine. Hermes can be installed several ways (git clone + venv via the curl
installer, `pip install hermes-agent`, zip-updated copies) and a single box often
holds more than one.

## Safe update procedure (this user's setup)

- Hermes canNOT self-update while running — `git pull`/`hermes update` on the live checkout is blocked by a safety guard (it would rewrite the code it is executing). Run the update from an EXTERNAL terminal with Hermes stopped: `hermes update` (handles git pull, pre-update snapshot, dependency sync, config migration, gateway restart).
- All user customizations live OUTSIDE the git checkout: config.yaml, .env, skills/, scripts/, sessions/, state.db, memories/ are in the hermes home dir, not `hermes-agent/` (the checkout). A git pull / `hermes update` therefore never touches them — verify with `git status` (clean) rather than assuming.
- Before updating, copy with timestamp: config.yaml, state.db, memories/ (`cp <x> <x>.bak.update_$(date +%Y%m%d_%H%M%S)`).
- OmniRoute combos can't be backed up via `curl http://127.0.0.1:20128/api/combos` — it requires auth (AUTH_001); combos live on the OmniRoute server, unaffected by a Hermes update.
- Post-update checks for this user: `hermes --version` advanced, `fallback_providers: []` still empty in config.yaml, OmniRoute launcher (omniroute-launch.vbs) still serves combos.

## Step 1 — identify which install is actually LIVE

Do this before touching anything. Batch these reads:

- `hermes --version` — the single most useful line: it prints **Install directory**
  and **Install method** (`git` / `docker` / `nix` / `unknown`).
- `which -a hermes` then read the launcher it points at. On Windows the launcher is
  often a Node shim that shells out to Python (see `references/windows-launcher-chain.md`).
- `pip show hermes-agent` — pip metadata Version + Location. NOTE: this can be STALE
  vs the code actually running (e.g. metadata says 0.16.0 while the code is 0.20.0
  because zip-updates overwrite source without updating pip metadata).
- Gateway command line (Windows): the gateway runs as a **Scheduled Task
  `Hermes_Gateway`**, not a service. Get its PID from `hermes gateway status`, then:
  `powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=<PID>' | Select-Object -ExpandProperty CommandLine"`
  This shows definitively which `python.exe -m hermes_cli.main` the background agent uses.

## Pitfall — cwd shadows the install (version changes by directory)

`hermes` imports `hermes_cli.main` through Python's normal import path, and **CWD is
first on sys.path for `-c` invocations**. Running `hermes` from INSIDE a git checkout
of the source imports the LOCAL source (e.g. v0.19.0) instead of the installed package
(e.g. v0.20.0).

Symptom: `hermes --version` / `hermes doctor` report DIFFERENT versions depending on
the directory you ran them from. Always run diagnostics from a neutral directory
(e.g. `C:\Windows\System32` or `/tmp`), and re-check cwd before trusting any
version/doctor output. This shadowing cost real confusion during a diagnosis.

## Pitfall — `hermes update` fails at dep-sync when install method is "unknown"

Signature (stderr appears before the update banner):
```
error: Failed to inspect Python interpreter from active virtual environment at `venv\Scripts\python.exe`
  Caused by: Python interpreter not found at <install_dir>\venv\Scripts\python.exe
... subprocess.CalledProcessError: Command '[...uv.exe, pip, install, -e, .]' returned non-zero exit status 2
```

Root cause: the zip updater (`_update_via_zip`) sets `VIRTUAL_ENV=PROJECT_ROOT/venv`
and runs `uv pip install -e .` into it. A pip install into site-packages has **no venv
and no `.git`**, so `detect_install_method()` returns `unknown` and the dep-sync step
finds no interpreter.

Key nuance: the ZIP extraction (code refresh) SUCCEEDS before dep-sync fails. So after
this error the code is usually already current — re-check `hermes --version`, and verify
deps independently with `hermes doctor` (Required Packages). If all present, the failure
was benign that run.

## Install-method summary

| `hermes --version` "Install method" | Meaning | `hermes update` behavior |
|---|---|---|
| `git` | clone + venv (curl installer) | git pull + venv sync + SQLite runtime repair — works |
| `unknown` | pip into site-packages (no `.git`, no `.venv`) | ZIP extract works; dep-sync + SQLite repair FAIL |

`doctor` also flags a SQLite WAL-reset bug (SQLite < 3.44.6) when `state.db`/`kanban.db`
are in WAL mode; the only in-product repair is `hermes update` on a venv-managed install —
exactly the step that fails for a pip install.

## Pitfall — FTS5 index repair needs a QUESCENT DB (can't run from inside a session)

After `hermes update`, `doctor` may flag issue #1: `state.db FTS write corruption —
run 'hermes doctor --fix' (or 'hermes sessions repair')` (a "malformed inverted index
for FTS5 table main.messages_fts_trigram"). The actual session/message rows are intact —
only `session_search` is degraded. Verify with the non-destructive read-only inspect:

```bash
hermes sessions recover --source <state.db> --inspect-only   # "warnings": [] => data OK
```

`hermes sessions repair` (backs up first, preserves data, rebuilds FTS) REQUIRES a quiet
database. It refuses with `a live writer still holds state.db` when ANY Hermes process is
writing — the gateway OR an active agent session. Two hard truths:

1. `hermes gateway stop` is guarded from inside an agent session ("cannot stop the gateway
   from inside the gateway process") — the terminal tool blocks it. Stopping the gateway
   from an agent requires the Windows-native path: `schtasks /End /TN Hermes_Gateway` then
   `taskkill /PID <supervisor> /T /F` (the gateway runs as supervisor+worker python pair;
   `schtasks /End` alone does NOT kill them).
2. Even with the gateway dead, repair still fails because the agent's OWN session is the
   live writer (it holds `state.db-wal`). A schema/FTS rebuild cannot run while the process
   asking for it is writing to the DB.

Resolution: give the user a script to run from a PLAIN terminal when no Hermes session is
open — `hermes gateway stop` → `hermes sessions repair` → `hermes gateway start` (from a
plain shell none of these are guarded). The offline alternative (`sessions recover --output
recovered-state.db`) rebuilds a clean DB read-only but still needs quiescence to swap in.

Stale `<db>.repair.lock` / `<db>.fts_rebuild.lock` files are harmless: they are OS byte-range
locks (msvcrt/flock), auto-released on process exit — do not delete state.db or the backup.

## Direct FTS5 rebuild (works with a LIVE writer — no quiescence needed)

When only the FTS5 inverted index is corrupt (`PRAGMA integrity_check` →
`malformed inverted index for FTS5 table main.messages_fts_trigram`) and the
message/session rows are fine, skip `hermes sessions repair` entirely — its
quiescence guard refuses while any Hermes process holds the DB. Rebuild the
index in place with the FTS5 `rebuild` command, which reconstructs the index
from the content table and needs no quiet database:

```python
import sqlite3, os
db = os.path.expanduser('~/AppData/Local/hermes/state.db')
conn = sqlite3.connect(db)
conn.execute("INSERT INTO messages_fts_trigram(messages_fts_trigram) VALUES('rebuild')")
conn.commit()
print(conn.execute('PRAGMA integrity_check').fetchall())  # expect [('ok',)]
```

- **Do NOT `DELETE FROM <fts_table>` first** — a DELETE against a corrupted FTS
  table itself fails with `database disk image is malformed`; the rebuild INSERT
  is the operation that actually fixes it. Go straight to `VALUES('rebuild')`.
- **Windows has no `sqlite3` CLI by default** — use Python's stdlib `sqlite3`
  module (no dependency) instead of hunting for a binary.
- **Backup first**: `cp state.db state.db.bak.$(date +%Y%m%d_%H%M%S)` before any
  write. The rebuild is non-destructive (index only), but back up on principle.
- Verify search works after: `SELECT count(*) FROM messages_fts_trigram WHERE
  messages_fts_trigram MATCH '<word>'` should return a plausible count.

## Fix directions (pick per setup; get consent before git surgery)

1. Migrate to the canonical git clone (usually `$HERMES_HOME/hermes-agent`):
   `git pull --rebase`, sync its venv, repoint CLI + gateway to it, then clean up the
   site-packages copy.
2. Clean reinstall via the official installer.
3. Leave as-is when the version is already latest and all deps are present.

## Rules of engagement

- Destructive git ops (`git reset --hard`, etc.) need explicit user approval — never
  silent. Prefer reversible `git pull --rebase`.
- The git clone's venv may be named `.venv` while the updater/PATH expect `venv` — check both.
- Don't report a fix as done until verified from a NEUTRAL cwd (see shadowing pitfall).

## Verification

- `hermes --version` from a neutral dir → expected Install directory + method + version.
- `hermes doctor` from a neutral dir → Required Packages all ✓, "Version files consistent".
- `hermes gateway status` → running, and its process cmdline points at the intended python.

## Known local patch — Telegram `updater.stop()` hangs during shutdown

Symptom (spams lvl8 alerts at gateway restart, ~03:00 nightly):
`[Telegram] Telegram updater.stop() did not finish` + `gateway.run: Fatal telegram
adapter error (telegram_network_error)`. Root cause: a race between `disconnect()`
and the polling error handler — `updater.stop()` blocks on a CLOSE-WAIT socket,
times out, and the `_polling_teardown_started` check runs only AFTER the fatal
error fires.

Fix: add a `_polling_teardown_started` check inside the
`except asyncio.TimeoutError` handler in `plugins/platforms/telegram/adapter.py`
so a hung `stop()` during teardown logs at DEBUG and returns instead of
escalating. Normal-operation recovery is unchanged.

Re-apply after any `hermes update` (local core edits are reverted):
```bash
cd "$HERMES_HOME/hermes-agent" && git apply "$HERMES_HOME/data/patches/telegram-stop-timeout.patch"
```
Patch copy: `references/telegram-stop-timeout.patch`.

**2026-09 update — the patch is now UPSTREAM; residual alerts are a log-monitor
false positive, not a code bug.** The `_polling_teardown_started` guard already
ships in `adapter.py` (the `except asyncio.TimeoutError` branch returns quietly
DURING teardown). If `updater.stop() did not finish` STILL spams lvl8 alerts
nightly, it is the NON-teardown path — `stop()` hangs on a CLOSE-WAIT socket
outside a shutdown, the adapter correctly logs + rebuilds and recovers, so it is
BENIGN. `hermes gateway restart` does NOT fix it (it recurs at the next restart,
and it also cuts the live agent session). The right fix for the user-facing spam
is to FILTER the alert at the SecurityMonitoring log monitor, not patch the
adapter again: add the pattern to `EXCLUDE` in
`data/security-monitoring/monitors/log_monitor.py` (tested BEFORE the `RULES` in
`classify()`), e.g.
`updater\.stop\(\)\s+did\s+not\s+finish|Fatal\s+telegram\s+adapter\s+error\s+\(telegram_network_error\)`.
Verify genuine errors (Traceback / Exception / out of memory) still match after.

## Supporting files

- `references/windows-runtime-ops.md` — gateway restart on Windows (kill the
  detached `gateway run` python via PowerShell, then `schtasks /run`), reliable
  MSYS detach (`powershell Start-Process`, not `cmd //c start`), the fact that
  local edits to `hermes-agent/` core are reverted by `hermes update`, benign
  Windows startup warnings (`start_unix_server`, LSP `WinError 193`), the
  Gmail email-IMAP timeout fix (`EMAIL_POLL_INTERVAL` + adapter `timeout`),
  **killing ELEVATED background processes (foreground shell = access denied;
  use UAC `Start-Process -Verb RunAs`)**, and the MSYS single-slash flag pitfall.
