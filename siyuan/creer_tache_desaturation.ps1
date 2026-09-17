# creer_tache_desaturation.ps1 - Cree (ou met a jour) la tache planifiee
# « Hermes - desaturer memoire » : chaque dimanche a 04h00, --auto.
# Texte en ASCII pur (les accents cassent PowerShell 5.1 sans BOM).
# Re-executable : -Force remplace la tache existante.
# Usage : powershell -NoProfile -ExecutionPolicy Bypass -File creer_tache_desaturation.ps1

$hermes   = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA + "\hermes" } else { Join-Path $env:USERPROFILE "AppData\Local\hermes" }
$python   = Join-Path $hermes "hermes-agent\venv\Scripts\python.exe"
$script   = Join-Path $hermes "scripts\desaturer_memoire.py"
$journaux = Join-Path $hermes "scripts\desaturation.log"
$nomTask  = "Hermes - desaturer memoire"

if (-not (Test-Path $python)) { Write-Host "[ERREUR] python du venv Hermes introuvable : $python"; exit 1 }
if (-not (Test-Path $script)) { Write-Host "[ERREUR] script introuvable : $script"; exit 1 }

$action  = New-ScheduledTaskAction -Execute $python `
             -Argument ('"' + $script + '" --auto') `
             -WorkingDirectory (Split-Path $script)
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 4:00am
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew `
             -StartWhenAvailable `
             -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
             -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $nomTask -Action $action -Trigger $trigger `
  -Settings $settings -Force `
  -Description ("Desaturation de la memoire native Hermes (MEMORY.md / USER.md) : archive " +
                "les entrees perimees dans SiYuan avant reecriture, uniquement au-dessus du " +
                "seuil d'alerte de check_memory.ps1 (2100 / 1300). Log : " + $journaux) | Out-Null

$t = Get-ScheduledTask -TaskName $nomTask
$info = Get-ScheduledTaskInfo -TaskName $nomTask
Write-Host ("[OK] tache « {0} » : {1}" -f $t.TaskName, $t.State)
Write-Host ("     declencheur : dimanche 04h00 | action : {0}" -f $t.Actions[0].Execute)
Write-Host ("     argument   : {0}" -f $t.Actions[0].Arguments)
Write-Host ("     prochaine execution : {0}" -f $info.NextRunTime)
Write-Host "     test manuel : Start-ScheduledTask -TaskName '$nomTask'"
