# Finishing a deferred dependency install after `hermes update`

The code refresh (git pull / zip extract) SUCCEEDS and the HEAD moves; only the venv sync
is skipped. Signature:

```
Could not quarantine hermes.exe (PermissionError: another process is holding it open)
...
The dependency install has been deferred: close the process(es) above, then run any
`hermes` command to finish it automatically.
```

Every later `hermes` invocation retries and prints the pending-install banner; the app keeps
working on the current venv, so this is cosmetic until the venv genuinely needs the new deps —
check the delta before alarming the user (see `SKILL.md`: compare `pyproject.toml`
`dependencies` against `pip freeze` and DISCARD platform-gated entries, e.g. a lone
`ptyprocess` under Windows).

## Why the pip command alone is not enough

A venv holder is any process whose command line names THIS checkout's
`venv\Scripts\python.exe`. `hermes update --list-venv-holders` prints them as JSON (exit code 3
when occupied).

**Three services = six holders.** Each service runs as a *supervisor*
(`venv\Scripts\python.exe -m hermes_cli.main ...`) plus a *worker* re-executed from a quarantined
runtime copy (`.hermes-runtime\python\generation-<id>\python.exe`):

```
gateway   <sup> supervisor / <w> worker
backend   <sup> supervisor / <w> worker   (owns :9119)
NIM proxy <sup> supervisor / <w> worker   (owns :20200)
```

Read the pairs by which PID owns the port instead of assuming a duplicated stack: only one of
each pair binds. Kill both members of a pair, not just the visible one.

**The agent's own CLI session holds the venv too — and it is NOT listed.**
`--list-venv-holders` excludes the invoking session, so an empty list is not proof the venv is
free. Close the Hermes session (and any editor/LSP python started from the venv) before
installing, otherwise `pip install` rewrites `site-packages` under a live interpreter.

## The marker

The checkout root carries `.update-incomplete` (JSON, e.g. `{"attempts": 3}`), written by
`hermes_cli/main_install_repair.py`. It is what makes every command print the pending-install
banner, and it clears ONLY when the recovery pass confirms the install healthy. Do not delete it
by hand: if it survives a successful install plus a cold `hermes --version`, that is a real signal
to report, not noise to silence.

## Order that works (plain PowerShell, no Hermes session open)

```powershell
cd "<HERMES_HOME>\hermes-agent"

# 1. Stop the repeating tasks recreating holders mid-install
'Hermes_Gateway','Hermes_Gateway_HealthCheck','Hermes_NVIDIA_NIM_Proxy','Hermes - serve backend' |
  ForEach-Object { Disable-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue | Out-Null }

# 2. Kill the holders (supervisors + workers) and the NIM proxy chain
$h = .\venv\Scripts\python.exe -m hermes_cli.main update --list-venv-holders | ConvertFrom-Json
$h | ForEach-Object { Stop-Process -Id $_.pid -Force -ErrorAction SilentlyContinue }
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'nvidia-nim-proxy|hermes_cli.main (gateway|serve)' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# 3. Prove the venv is free before writing into it
.\venv\Scripts\python.exe -m hermes_cli.main update --list-venv-holders

# 4. Install
.\venv\Scripts\python.exe -m pip install -e ".[all]"

# 5. Verify
Test-Path .\.update-incomplete          # expect False
.\venv\Scripts\python.exe -c "import hermes_cli.main, agent; print('imports ok')"
.\venv\Scripts\python.exe -m hermes_cli.main doctor

# 6. Restart EVERY task you disabled (the NIM proxy included)
'Hermes_Gateway','Hermes_Gateway_HealthCheck','Hermes_NVIDIA_NIM_Proxy','Hermes - serve backend' |
  ForEach-Object { Enable-ScheduledTask -TaskName $_ | Out-Null; Start-ScheduledTask -TaskName $_ }
```

Then re-verify from a neutral cwd: `hermes --version`, `hermes gateway status`, the NIM proxy
(`curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:20200/v1/models`) and the backend port.

## Pitfalls

- **Verify the extra exists before handing the command over**: read
  `[project.optional-dependencies]` in `pyproject.toml` first. Where `all` is declared it is
  usually a bundle of light sub-extras (cron/pty/mcp/uvloop/web/...), so no toolchain downgrade
  risk. Never substitute `pip install -r <freeze>` here: a freeze-driven install can DOWNGRADE
  toolchain packages.
- **Restart the proxy task too.** Disabling the tasks then restarting only the gateway and the
  backend leaves `eco`/`nvidia-stack` without an upstream on :20200.
- `hermes gateway stop` is the graceful path for the gateway; there is no `serve stop` and no
  `profile stop`, so the backend and the proxy tree get killed by PID.
- Announce the downtime: the Telegram bots are offline for 1-3 min while the venv is being
  rewritten.
- A `--backup` run on a home with a big `data/` leaves multi-GB `.pre-update-*.zip.<pid>-<tid>.partial`
  orphans in `backups/`. They are hidden dotfiles, so a `*.partial*` glob misses them — use
  `Get-ChildItem <home>\backups -Force -Filter "*.partial*"` (or `ls -a`). Confirm no updater is
  running, then delete them.
