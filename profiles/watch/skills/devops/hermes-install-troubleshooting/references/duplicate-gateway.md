# Duplicate Hermes Gateway — detection & cleanup

Real-world scenario: TWO gateway daemon processes running because two Scheduled Tasks both
launch `hermes gateway run` at logon.

## Symptom
- Slow/confused boot with two `python -m hermes_cli.main gateway run` processes (different
  venvs / runtime pythons), each holding a few tens of MB and both claiming the gateway role.
- They can also share the same listening port or fight over it.

## Detect
```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*gateway run*' } |
  Select-Object ProcessId, Name, CommandLine | Format-List
"""
Expect the Output to show 2 rows with different CommandLine (e.g. venv python vs
.hermes-runtime python).

Then list the Tasks:
Get-ScheduledTask | Where-Object { $_.TaskName -like 'Hermes*' } | Select-Object TaskName, TaskPath, State
"""
Typical offenders:
- `HermesGateway`   -> pwsh -NoProfile -Command "hermes gateway start"  (Hidden=$true)
- `Hermes_Gateway`  -> wscript //B ...\Hermes_Gateway.vbs                (older launcher)

## Fix (single instance -> keep the newer one)
```powershell
Disable-ScheduledTask -TaskName 'Hermes_Gateway'   # keep HermesGateway
Set-ScheduledTask -TaskName '<keep>' -Settings (New-ScheduledTaskSettingsSet -Hidden)
```
Prefer the pwsh `hermes gateway start` one; retire the older VBS one. Kill the stray running
process after disabling (or leave for next session, the disabled task stops relaunching it).
Then verify only ONE gateway run-process remains.

## Related
- `hermes-install-troubleshooting` Step 1 relies on this: get PID via `hermes gateway status`.
