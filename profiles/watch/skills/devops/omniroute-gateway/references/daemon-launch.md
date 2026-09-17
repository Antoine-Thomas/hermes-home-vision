# OmniRoute Daemon Launch Reference

## Complete launcher template (`omniroute-launch.cmd`)

```cmd
@echo off
REM OmniRoute auto-launch for Hermes (MSYS-safe, no PowerShell Start-Process)
REM Uses omniroute's native --daemon (self-backgrounds + auto-restarts on crash)
setlocal

REM Idempotent: if port 20128 is already listening, do nothing
netstat -an 2>nul | findstr /r ":20128 " >nul
if %errorlevel%==0 (
  echo OmniRoute already running on :20128
  goto :eof
)

REM Detach via start so the launching process (schtask / bash) returns immediately.
start "" /min cmd /c "omniroute serve --daemon --no-open"
echo OmniRoute launch requested.
endlocal
exit /b 0
```

## Key persistence (required for non-bash launchers)

OmniRoute reads `~/.omniroute/.env` at startup. The daemon also inherits the Windows user environment.

```bash
# 1. Persist to OmniRoute's native load file (source of truth for daemon)
printf 'OMNIROUTE_API_KEY=%s\n' "$OMNIROUTE_API_KEY" >> "$USERPROFILE/.omniroute/.env"

# 2. Persist to Windows user env (visible to scheduled tasks)
cmd //c "setx OMNIROUTE_API_KEY \"$OMNIROUTE_API_KEY\""
```

## Scheduled task creation

```bash
schtasks /create /tn "OmniRoute-AutoLaunch" \
  /tr "cmd /c C:/Users/searc/AppData/Local/hermes/omniroute-launch.cmd" \
  /sc onlogon /rl highest
```

Task XML snippet (for advanced config via /XML):
```xml
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>OmniRoute daemon for Hermes (free model routing)</Description></RegistrationInfo>
  <Triggers><LogonTrigger><Enabled>true</Enabled></LogonTrigger></Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings><RestartCount>3</RestartCount><RestartInterval>PT1M</RestartInterval></Settings>
  <Actions><Exec><Command>cmd</Command><Arguments>/c C:/Users/searc/AppData/Local/hermes/omniroute-launch.cmd</Arguments></Exec></Actions>
</Task>
```

## Verification commands

```bash
# Is daemon up?
netstat -ano | findstr :20128

# Is scheduled task registered?
schtasks /query /tn "OmniRoute-AutoLaunch"

# Test launcher idempotency (should no-op if running)
cmd /c C:/Users/searc/AppData/Local/hermes/omniroute-launch.cmd
# Expected: "OmniRoute already running on :20128"

# View task XML
schtasks /query /tn "OmniRoute-AutoLaunch" /xml
```

## Pitfalls avoided

| Pitfall | Avoided by |
|---------|------------|
| PowerShell `Start-Process` hangs in MSYS | Use `cmd /c start "" /min` + native `--daemon` |
| Env vars only in bashrc | Persist to `~/.omniroute/.env` + Windows user env |
| Launcher spawns duplicate daemons | `netstat` idempotency check in launcher |
| Crash leaves no process | `--daemon` has built-in auto-restart (parent watcher) |
| Task needs password | `InteractiveToken` logon type (runs at login, no password) |
| Task runs too late (after Hermes) | `onlogon` trigger runs before user's desktop apps |

## Files created in this session

- `C:/Users/searc/AppData/Local/hermes/omniroute-launch.cmd` — launcher script
- Scheduled task: `OmniRoute-AutoLaunch` (logon trigger, `cmd /c` the launcher)