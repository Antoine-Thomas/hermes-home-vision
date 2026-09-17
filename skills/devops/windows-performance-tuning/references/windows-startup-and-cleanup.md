# Windows Startup Audit & Non-Interactive Cleanup

Complements the cleanup/debloat step of the main workflow. Use when the user reports:
- "empty PowerShell / console window at startup"
- "clean my temp files / old Windows updates / junk"

## 1. Audit startup points (READ-ONLY) — always as a `.ps1` run via `-File`

Enumerate every place that can launch a visible window at logon:

- Startup folders (user + common):
  `$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup`
  `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp`
- Registry Run / RunOnce: `HKCU:\...\Run`, `HKCU:\...\RunOnce`,
  `HKLM:\SOFTWARE\...\Run`, `HKLM:\SOFTWARE\WOW6432Node\...\Run`
- StartupApproved\Run (shows enabled/disabled):
  `HKCU` + `HKLM:\SOFTWARE\...\Explorer\StartupApproved\Run`
- Scheduled tasks at ROOT path, with trigger type + action:
  `Get-ScheduledTask | Where-Object { $_.TaskPath -eq "\" }`

Key facts:
- StartupApproved binary value first byte: `0x02` = enabled, `0x03` = disabled (Win10+).
- The classic cause of an "empty PowerShell window at startup" is a **SCHEDULED TASK
  with a LogonTrigger** whose action runs `pwsh.exe` / `powershell.exe` / `cmd.exe` /
  a `.cmd` or `.bat` WITHOUT `-WindowStyle Hidden`. Registry Run entries are rarely the
  culprit — check tasks first.
- Trigger type: `$task.Triggers | ForEach-Object { $_.CimClass.CimClassName }`
  -> `MSFT_TaskLogonTrigger` = runs at logon = visible-window risk.
  `MSFT_TaskBootTrigger` = runs at boot in session 0 = no visible window (safe junk).

## 2. Fix: replace a visible startup task with a hidden launcher

Do NOT just disable a legit service the user wants (e.g. the Hermes gateway). Instead:
1. Unregister the visible task: `Unregister-ScheduledTask -TaskName <name> -Confirm:$false`
2. Re-register pointing at a GUI/WScript launcher with a hidden window:
   `New-ScheduledTaskAction -Execute "C:\Windows\System32\wscript.exe" -Argument '"<path>.vbs"'`
   (`wscript.exe` opens NO console; a `.vbs` using `sh.Run cmd, 0, False` runs the
   child hidden and returns immediately, so the task itself exits fast.)
3. Trigger at logon for the specific user:
   `New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"`
   Principal: `-UserId $user -LogonType Interactive -RunLevel Limited`

## 3. `cleanmgr /sagerun:1` silently does NOTHING unless StateFlags0001 is pre-set

Configure it non-interactively by writing the registry, then run:

```powershell
$handlers = @(
  "Active Setup Temp Folders","Content Indexer Cleaner","Delivery Optimization Files",
  "Device Driver Packages","Downloaded Program Files","Internet Cache Files",
  "Memory Dump Files","Old ChkDsk Files","Previous Installations","Recycle Bin",
  "RetailDemo Offline Content","Setup Log Files","System error memory dump files",
  "System error minidump files","Temporary Files","Temporary Setup Files",
  "Temporary Sync Files","Thumbnail Cache","Update Cleanup","Upgrade Discarded Files",
  "User file versions","Windows Error Reporting Files","Windows Upgrade Log Files"
)
foreach ($h in $handlers) {
  $p = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VolumeCaches\$h"
  if (Test-Path $p) { New-ItemProperty -Path $p -Name StateFlags0001 -Value 2 -PropertyType DWord -Force | Out-Null }
}
Start-Process cleanmgr.exe -ArgumentList '/sagerun:1' -Wait -WindowStyle Hidden
```

- "Update Cleanup", "Previous Installations", "Device Driver Packages" free the most.
- "Update Cleanup" is I/O-bound (component-store compression): high disk activity,
  near-zero CPU, can take 30+ min. Run in background with notify_on_complete.

## 4. cleanmgr GUI lingers idle after finishing — do NOT force-kill

After the real work is done, `cleanmgr.exe` often stays around with ~0 CPU and 0 I/O
(Update Cleanup delegates to the servicing stack, then cleanmgr just sits). Confirm
it's done by sampling twice ~20s apart: free space and I/O bytes stop moving. It is
harmless and exits on reboot. `Stop-Process cleanmgr -Force` hits the approval gate
(user consent required) — don't attempt it proactively; just report the space freed.
