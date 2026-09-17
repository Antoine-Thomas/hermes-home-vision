# Windows Startup Audit — Console Flashes & Duplicate Launchers

Session-proven diagnostic for "console windows flash at login" + "Windows boots slow".

## Sources of startup apps (check ALL)
- `HKCU\...\CurrentVersion\Run` and `HKLM\...\CurrentVersion\Run` (Get-ItemProperty, e.g.
  `powershell -Command "Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run' | Format-List"`)
- Startup folder: `C:/Users/<u>/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/`
- Scheduled tasks with a **Logon trigger** (users the tasks they trigger apps — Task Scheduler UI
  shows them but they live in the planifier, hidden from the Registry Run list)
- `Get-CimInstance Win32_StartupCommand` (merges registry + startup folder)

## Enumerate logon-trigger tasks + their actions (hidden/flash check)
```powershell
$all = Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' }
foreach ($t in $all) {
  if (-not $t.Triggers) { continue }
  $isLogon = $false
  foreach ($tr in $t.Triggers) {
    if ($tr.CimClass -and $tr.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger') { $isLogon = $true }
  }
  if ($isLogon) {
    foreach ($a in $t.Actions) {
      ($t.TaskPath + $t.TaskName) + " | " + $a.Execute + " | " + $a.Arguments + " | Hidden=" + $t.Settings.Hidden
    }
  }
}
```
Looping is REQUIRED: each task's Actions is an array; a bare `.Actions` select drops the arguments.

## Which tasks flash a console
- `Hidden=$false` + EXEC is a bare `.exe` (python/cmd/pwsh/bat) => flashes. Wrap in a VBS (`wscript.exe //B`)
  or restart the task action with `-WindowStyle Hidden`.
- EXEC is `wscript.exe //B <file.vbs>` (WSH) or the task itself is `Hidden=$true` => no flash.
- Get action detail with: `(Get-ScheduledTask -TaskName X).Settings.Hidden` and
  `(Get-ScheduledTask -TaskName X).Actions`.

## Apply the fix (force print hidden + dedupe)
```powershell
Set-ScheduledTask -TaskName '<name>' -Settings (New-ScheduledTaskSettingsSet -Hidden)  # mark Hidden
Disable-ScheduledTask -TaskName '<dup>'                                              # kill a duplicate
```
Run inside a Task Scheduler logon trigger with a shareable `.ps1` written to a temp file and
invoked via `powershell -ExecutionPolicy Bypass -File <tmp.ps1>` — this is the ONLY escape from
bash MSYS mangling `$_` and `{$_.X}` inside double-quoted `powershell -Command "..."`.

## Verify
- After fixing, check for the flash at next login (tell the user to reboot once).
- Check process count for a duplicate daemon directly:
  `powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*gateway*' }"`

## PITFALL — MSYS + PowerShell `$_` mangling
Under git-bash, double-quoted `powershell -Command "Get-Process | Where-Object { $_.ProcessName -eq 'x' }"`
corrupts `$_` and `{$_.X}`. Workarounds used in-session:
- Avoid `2>$null` inline (bash sees `$null` as a special word and breaks the redirect).
- Avoid `\`-escaped `$` inside the -Command string (ps sees mangled tokens).
- SAFEST: write the script to `$LOCALAPPDATA/Temp/x.ps1` with the write_file tool then run
  `powershell -ExecutionPolicy Bypass -File <path>`. No inline quoting issues at all.

## Line discipline for long /multi-part PowerShell
- Write the whole multi-step script as one `.ps1` file (write_file) and run it once. Do NOT let
  the bash history accumulate partial `-Command` calls — they fail on `$_` (loop warning).
- Use `-filter 'ProcessId=<PID>'` for a single process instead of a broad Where-Object.

## FREE-RAM MYTH
Do not "dump working sets" / call EmptyWorkingSet / kill Safe to Reclaim RAM by default.
- Big free RAM (e.g. 55 of 64 GB free) is healthy, not a problem. Advise NOT to force-drain it.
- Only genuine leaks (a process dragging RAM + disk over hours) justify a targeted restart.
- Libre/Fast est sain: the agent explaining "nothing to clean" is correct output, not a failure.
