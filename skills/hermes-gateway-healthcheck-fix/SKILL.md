---
name: hermes-gateway-healthcheck-fix
description: "Correct PID mismatch causing false gateway alerts."
version: 1.0.0
author: searching-murphy
license: MIT
platforms: [windows]
---

# Hermes Gateway Healthcheck Fix

Procedure to resolve false "gateway dead" alerts when the PID in gateway_state.json does not match the actual gateway process.

## Procedure

1. **Identify the gateway process PID**
   ```
   tasklist.exe | findstr hermes.exe
   ```
   Note the PID (e.g., 21152).

2. **Check gateway_state.json**
   ```
   type C:\Users\searc\AppData\Local\hermes\gateway_state.json
   ```
   Verify the `pid` field matches the PID from step 1.

3. **If mismatched, update the state**
   *Backup:*
   ```
   copy C:\Users\searc\AppData\Local\hermes\gateway_state.json C:\Users\searc\AppData\Local\hermes\gateway_state.json.bak
   ```
   *Update PID and refresh start_time:*
   ```
   python -c "import json, time; d=json.load(open('C:\\Users\\searc\\AppData\\Local\\hermes\\gateway_state.json')); d['pid']=<ACTUAL_PID>; d['start_time']=int(time()*1000); open('C:\\Users\\searc\\AppData\\Local\\hermes\\gateway_state.json','w').write(json.dumps(d))"
   ```
   Replace `<ACTUAL_PID>` with the PID from step 1.

4. **Restart / re-enable the healthcheck task**
   ```
   schtasks /run /tn "Hermes_Gateway_HealthCheck"
   ```
   To turn a DISABLED task back on, prefer the cmdlet over `schtasks`:
   `powershell -NoProfile -Command "Enable-ScheduledTask -TaskName 'Hermes_Gateway_HealthCheck'"`,
   then read `State` back (must be `Ready`, not `Disabled`) plus the trigger repetition (`Get-ScheduledTask`
   / `Get-ScheduledTaskInfo`). In git-bash the native `schtasks /Change /TN "name" /ENABLE` has its
   quotes doubled and fails with « le nom de tache ... n'existe pas » while the task exists — a pure
   argument-mangling artefact, not a missing task.

5. **Confirm no new alerts for 5 minutes**
   ```
   tail -f C:\Users\searc\AppData\Local\hermes\logs\gateway-health.log
   ```
   Wait 5 minutes; absence of "MORT" alerts indicates success. If "MORT" keeps appearing
   while the gateway process is alive, the state file was NOT the fault — go to step 6.

6. **If alerts persist: fix the DETECTION, not just the state**
   The detector lives in `%LOCALAPPDATA%\hermes\scripts\check_gateways.ps1` (run by the
   scheduled task). A stale `pid` is only one cause; a detector that greps the process
   command line for `gateway run` reports a live gateway as dead every tick. Back up the
   script (`cp check_gateways.ps1 check_gateways.ps1.bak_<horodatage>`), then make detection
   read the source of truth:
   - read `pid` and `gateway_state` from the profile's `gateway_state.json`;
   - alive = process `Get-Process -Id <pid>` exists AND its name is one of
     `hermes` / `python` / `pythonw` AND `gateway_state -eq 'running'`;
   - **compare the base name, not the `.exe` name**: on this host `(Get-Process -Id <pid>).Name`
     returns `python` / `hermes` WITHOUT the extension, so an allow-list of `'python.exe','hermes.exe'`
     never matches and a live gateway is declared MORT at every tick. Use
     `[IO.Path]::GetFileNameWithoutExtension($proc.Name)` against `@('hermes','python','pythonw')`;
   - drop any `CommandLine -match 'gateway\s+run'` test and the python "superviseur" fallback.
   Test with `-DryRun` (logs + no alert, no restart) and require a line
   `[<profil>] OK pid=<pid> vivant` and `aucune transition d'etat, pas d'alerte`. Never
   disable the task, and never touch an unrelated listening port (20128 = OmniRoute).

## Pitfalls

- **Do not confuse ports** – The healthcheck monitors the gateway process, not a specific port. A listening port (e.g., 20128) may belong to another service and does not reflect gateway health.
- **PID must match the actual gateway executable** – If the gateway runs via `hermes.exe`, use that PID, not a Python PID.
- **Always backup gateway_state.json** – A malformed JSON can break the gateway and healthcheck.
- **Ensure the gateway is actually running** – If the gateway process is not alive, updating the state alone will not resolve the issue; start the gateway first.
- **A stale `pid` can also MASK a real death — confirm the process before calling any alert false.** The very state that reports a live-looking `pid` while the process is gone is what makes a genuine outage look like a false alert. `Get-Process -Id <pid>` (or `tasklist`) must confirm the process EXISTS; if it does not, the gateway is really down (cron jobs stop firing, `cron/ticker_heartbeat` freezes) and correcting the state alone changes nothing — start the gateway first. And while `Hermes_Gateway_HealthCheck` is `Disabled`, no "MORT" line is ever written: absence of alerts in `gateway-health.log` is NOT evidence of health. For the full stalled-ticker diagnostic, see `hermes-operations` → `references/cron-heartbeat-diagnosis.md`.
- **Updating `gateway_state.json` alone is not the fix** – When the alert keeps firing while the process is alive, the detector is wrong (see step 6). Repairing the state on a broken detector produces a fixed-looking file and an unchanged alert.
- **Never detect a Hermes process by its command line** – Since v0.21.5+ the gateway runs under `hermes.exe` (PyInstaller bundle) / `python.exe` and no longer carries `gateway run` in its `CommandLine`; a `-match 'gateway\s+run'` test marks it dead forever. Use the `pid` from `gateway_state.json` plus the process name.
- **`Get-Process .Name` has no extension on this host** – the silent killer: `$proc.Name` returns `python`, not `python.exe`. An allow-list written with `.exe` suffixes returns `$false` for a perfectly healthy gateway, so the detector logs `MORT` every PT5M tick, tries to relaunch endlessly, and (with healthcheck enabled) spams false alerts. Always normalise with `GetFileNameWithoutExtension` before comparing. Verify the fix with `check_gateways.ps1 -DryRun`: it must print `[<profil>] OK pid=<pid> vivant` and `aucune transition d'etat, pas d'alerte` while the gateway is alive — run the dry-run BEFORE re-enabling `Hermes_Gateway_HealthCheck`, never after.

## References

- See `hermes-operations` skill for general gateway control commands.
- Gateway state format: refer to the official Hermes documentation on `gateway_state.json`.
