# Audit startup sources that can flash a console at login, detect duplicate daemons.
# Read-only. Run:  powershell -ExecutionPolicy Bypass -File audit-startup.ps1
$ErrorActionPreference = 'Continue'

"==== 1. Registry Run keys ===="
foreach ($hive in 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
                  'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run') {
  "--- $hive ---"
  Get-ItemProperty -Path $hive -ErrorAction SilentlyContinue | Format-List
}

"==== 2. Startup folder ===="
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup" -ErrorAction SilentlyContinue |
  Select-Object Name, Length | Format-Table -AutoSize

"==== 3. Logon-trigger scheduled tasks (incl Hidden flag + action detail) ===="
$all = Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' }
$logon = @()
foreach ($t in $all) {
  if (-not $t.Triggers) { continue }
  $isLogon = $false
  foreach ($tr in $t.Triggers) {
    if ($tr.CimClass -and $tr.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger') { $isLogon = $true }
  }
  if ($isLogon) {
    foreach ($a in $t.Actions) {
      $logon += (($t.TaskPath + $t.TaskName) + " | " + $a.Execute + " | " + $a.Arguments + " | Hidden=" + $t.Settings.Hidden)
    }
  }
}
$logon

"==== 4. Duplicate daemon check (sample gateway) ===="
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -like '*gateway*m' -or $_.CommandLine -like '*gateway run*' } |
  Select-Object ProcessId, Name, CommandLine | Format-List
