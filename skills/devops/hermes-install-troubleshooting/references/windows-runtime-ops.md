# Hermes gateway & runtime operations on Windows

Non-install operational knowledge for a Windows host running Hermes as a
Scheduled Task. Load alongside this skill when restarting the gateway,
diagnosing recurring gateway/email log noise, or patching Hermes core.

## Correct gateway restart (the VBS → detached-python chain)

The `Hermes_Gateway` task runs `wscript.exe //B Hermes_Gateway.vbs`, which sets
env and runs `python.exe -m hermes_cli.main gateway run` DETACHED
(`sh.Run(..., 0, False)`). Consequences:

- `schtasks /End /TN Hermes_Gateway` kills only the `wscript.exe`, NOT the
  detached python — the python survives and keeps the OLD code loaded. This is
  why config/env/code changes "don't take effect" after a `schtasks /End`.
- The gateway is several python processes (main + workers) sharing the
  `gateway run` command line and the original CreationDate.

Reliable restart — kill the real python(s) by command line, then re-run the
task. Do it from a DETACHED script so it survives your own process dying:
```powershell
Start-Sleep -Seconds 15
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like '*hermes_cli.main gateway run*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 5
schtasks /run /tn "Hermes_Gateway"
```

Verify it ACTUALLY restarted (not silently a no-op): the new process
CreationDate must be ~now, not the old boot time.
```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like '*hermes_cli.main gateway run*' } |
  Select-Object ProcessId, CreationDate
```

## Reliable detach on Windows (MSYS pitfall)

`cmd //c 'start "" /min "script.cmd"'` from git-bash is UNRELIABLE — the `//c`
can be swallowed and cmd opens an INTERACTIVE banner instead of running the
script, so the restart silently never fires. Use PowerShell Start-Process:
```bash
powershell -NoProfile -Command "Start-Process -FilePath 'powershell' -ArgumentList '-NoProfile','-WindowStyle','Hidden','-File','C:\path\restart.ps1' -WindowStyle Hidden"
```

## Local patches to Hermes core are reverted by `hermes update`

Edits under `hermes-agent/` (plugins/, gateway/, agent/) are overwritten on
`hermes update` — they are NOT permanent. Re-apply after each update, or report
upstream. Patched 2026-08-31 (all benign, all Windows-specific):
- `plugins/platforms/email/adapter.py`: IMAP `timeout=30` → `90` (2 sites).
- `agent/lsp/client.py` `_win_wrap_cmd`: resolve extension-less npm shims → `.cmd`.
- `gateway/shutdown_watchdog.py`: gate `start_unix_server` behind `os.name == "posix"`.

## Windows-specific startup warnings (benign — do NOT chase as crashes)

Hermes' log router tags these WARNING-level logs as "critical/crash" (lvl10) in
Telegram. They are expected on Windows; the gateway keeps working:
- `AttributeError: module 'asyncio' has no attribute 'start_unix_server'` — the
  Windows Python runtime has no `socket.AF_UNIX`, so the function doesn't exist;
  `shutdown_watchdog.py` calls it and catches the error (loop-tick witness just
  stays disabled). Fix = gate behind `os.name == "posix"`.
- `lsp[pyright] spawn/initialize failed ... OSError: [WinError 193] %1 not a
  valid Win32 application` — LSP spawned the extension-less npm `.bin` POSIX
  shim (CreateProcess can't run `#!/bin/sh`); fix = resolve the `.cmd` sibling.
- `gateway.lifecycle_ledger: Previous gateway life (pid=...)` on restart — normal.

## Email gateway IMAP timeouts (Gmail)

Recurring `email_imap_fetch_failed / read operation timed out` is almost always
Gmail throttling the default **15 s** poll — NOT auth, DNS, or large messages
(verify with a direct imaplib login+select+search: 0.1 s each means creds are
fine and the mailbox is reachable). Fix BOTH, then restart the gateway:
1. `EMAIL_POLL_INTERVAL=120` in `.env`.
2. Raise the hardcoded IMAP `timeout=30` → `90` in
   `plugins/platforms/email/adapter.py` (2 sites).

## Killing Hermes-spawned background processes (elevation pitfall)

`terminal(background=true)` processes spawn **ELEVATED (HIGH integrity)**, while
foreground `terminal` commands run at **MEDIUM integrity**. Result: you CANNOT
kill your own background process from a foreground command — even though it is
the SAME user (e.g. `OMATHS\searc`) and SAME session id. Every kill path fails
with access-denied:

- `Stop-Process -Id <pid> -Force` → `Accès refusé`
- `taskkill /F /PID <pid>` → `Erreur: le processus ... n'a pas été arrêté. Raison: Accès refusé`
- WMI `(Get-WmiObject Win32_Process -Filter 'ProcessId=<pid>').Terminate()` → silently no-op (process still alive)

Diagnose (read-only): `Get-CimInstance Win32_Process | GetOwner()` shows the SAME
user, but your own shell's `IsInRole(Administrator)` is `False` while the target
is elevated. Don't waste time retrying taskkill/Stop-Process — they will keep
failing. The guard's approval prompt will also keep firing per kill command.

Fix — UAC elevation (triggers a "Contrôle de compte d'utilisateur" prompt the
user must click; works even when driving over Telegram):
```bash
powershell.exe -NoProfile -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-Command','Stop-Process -Id <pid> -Force -ErrorAction Continue'"
```
Then VERIFY the PID is gone (`Get-Process -Id <pid>` → "mort") and that the
resource actually freed (e.g. `nvidia-smi --query-gpu=memory.used` dropped).
Killing the `bash` wrapper via process_manage does NOT kill its elevated child
python — the child survives orphaned and keeps holding GPU VRAM.

## MSYS path conversion is DISABLED — single-slash flags for native tools

Unlike default MSYS/git-bash, path conversion is OFF on this host. `taskkill //F`
reaches taskkill literally as `//F` and errors
`Argument ou option non valide - '//F'`. Use SINGLE slashes for native Windows
flag tools: `taskkill /F /PID <pid>`, `tasklist /FI "..."`. `MSYS_NO_PATHCONV=1`
prefix is the belt-and-suspenders alternative for any native tool that still
mangles an arg.
