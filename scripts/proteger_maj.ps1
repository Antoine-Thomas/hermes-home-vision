# Protection anti-redemarrage pendant le run LatentSync v5.
# Ne desinstalle rien, ne redemarre rien : met en pause les mises a jour et le redemarrage.
# Reversible via restaurer_maj.ps1 (etat initial sauvegarde en JSON).

$ErrorActionPreference = 'Continue'
$journal = 'C:\Users\searc\AppData\Local\hermes\scripts\maj_etat_initial.json'
$UX = 'HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings'
$AU = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU'

Write-Output '=== ETAT INITIAL ==='

# --- services
$svc = Get-Service wuauserv, UsoSvc, BITS | Select-Object Name, Status, StartType
$svc | Format-Table -AutoSize | Out-String | Write-Output

# --- pause UX
$pause = Get-ItemProperty $UX -ErrorAction SilentlyContinue |
    Select-Object PauseUpdatesExpiryTime, PauseFeatureUpdatesStartTime, PauseQualityUpdatesStartTime
# --- heures actives
$ah = Get-ItemProperty $UX -ErrorAction SilentlyContinue |
    Select-Object ActiveHoursStart, ActiveHoursEnd, SmartActiveHoursState
# --- politique AU
$au = Get-ItemProperty $AU -ErrorAction SilentlyContinue |
    Select-Object NoAutoRebootWithLoggedOnUsers, AUOptions, NoAutoUpdate, AlwaysAutoRebootAtScheduledTime

# --- taches
$cibles = @(
    'UIEOrchestrator', 'Schedule Wake To Work', 'Schedule Work',
    'Schedule Scan', 'Schedule Scan Static Task', 'USO_UxBroker',
    'Start Oobe Expedite Work', 'UUS Failover Task'
)
$taches = @{}
foreach ($t in $cibles) {
    $st = (Get-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\*' -TaskName $t -ErrorAction SilentlyContinue).State
    $taches[$t] = if ($st) { "$st" } else { 'ABSENTE' }
}

$etat = [ordered]@{
    date                    = (Get-Date).ToString('s')
    services                = @($svc | ForEach-Object { [ordered]@{ name = $_.Name; status = "$($_.Status)"; start = "$($_.StartType)" } })
    pause_updates_expiry    = "$($pause.PauseUpdatesExpiryTime)"
    active_hours_start      = $ah.ActiveHoursStart
    active_hours_end        = $ah.ActiveHoursEnd
    smart_active_hours      = "$($ah.SmartActiveHoursState)"
    no_auto_reboot_loggedon = $au.NoAutoRebootWithLoggedOnUsers
    taches                  = $taches
}
$etat | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $journal
Write-Output "etat initial sauvegarde dans $journal"
Write-Output ''

Write-Output '=== APPLICATION DES PROTECTIONS ==='

# 1. Politique : jamais de redemarrage automatique avec un utilisateur connecte
if (-not (Test-Path $AU)) { New-Item -Path $AU -Force | Out-Null }
Set-ItemProperty -Path $AU -Name 'NoAutoRebootWithLoggedOnUsers' -Value 1 -Type DWord
Write-Output '[1] NoAutoRebootWithLoggedOnUsers = 1'

# 2. Pause des mises a jour (fenetre maximale cote UX : ~35 jours, on prend 7)
$debut = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$fin = (Get-Date).AddDays(7).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
Set-ItemProperty -Path $UX -Name 'PauseUpdatesExpiryTime'   -Value $fin   -Type String
Set-ItemProperty -Path $UX -Name 'PauseFeatureUpdatesStartTime'  -Value $debut -Type String
Set-ItemProperty -Path $UX -Name 'PauseQualityUpdatesStartTime'  -Value $debut -Type String
Write-Output "[2] mises a jour en pause jusqu'au $fin"

# 3. Heures actives : couvrir toute la duree du run (09:00 -> 02:00)
Set-ItemProperty -Path $UX -Name 'SmartActiveHoursState' -Value 0 -Type DWord
Set-ItemProperty -Path $UX -Name 'ActiveHoursStart' -Value 9  -Type DWord
Set-ItemProperty -Path $UX -Name 'ActiveHoursEnd'   -Value 2  -Type DWord
Write-Output '[3] heures actives 09:00 -> 02:00 (SmartActiveHours desactive)'

# 4. Desactiver les taches qui declenchent scan/veille/reboot
$rapport = @()
foreach ($t in $cibles) {
    try {
        Disable-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\' -TaskName $t -ErrorAction Stop | Out-Null
        $rapport += "OK      $t"
    } catch {
        $rapport += "ECHEC   $t : $($_.Exception.Message.Split([Environment]::NewLine)[0])"
    }
}
$rapport | ForEach-Object { Write-Output "[4] $_" }

# 5. Service Windows Update : arret + demarrage desactive
try {
    Stop-Service UsoSvc -Force -ErrorAction Stop
    Set-Service UsoSvc -StartupType Disabled -ErrorAction Stop
    Write-Output '[5] UsoSvc arrete et desactive'
} catch {
    Write-Output "[5] UsoSvc : $($_.Exception.Message.Split([Environment]::NewLine)[0])"
}
try {
    Stop-Service wuauserv -Force -ErrorAction Stop
    Set-Service wuauserv -StartupType Disabled -ErrorAction Stop
    Write-Output '[5] wuauserv arrete et desactive'
} catch {
    Write-Output "[5] wuauserv : $($_.Exception.Message.Split([Environment]::NewLine)[0])"
}
Write-Output ''

Write-Output '=== VERIFICATION ==='
Get-Service wuauserv, UsoSvc | Select-Object Name, Status, StartType | Format-Table -AutoSize | Out-String | Write-Output
$v = Get-ItemProperty $UX -ErrorAction SilentlyContinue | Select-Object PauseUpdatesExpiryTime, ActiveHoursStart, ActiveHoursEnd
Write-Output ("pause jusqu'a : " + $v.PauseUpdatesExpiryTime)
Write-Output ("heures actives : " + $v.ActiveHoursStart + " -> " + $v.ActiveHoursEnd)
foreach ($k in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired',
                 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending')) {
    Write-Output ("$k : " + $(if (Test-Path $k) { 'PRESENT (redemarrage toujours du, mais bloque automatique)' } else { 'absent' }))
}
Write-Output ''
Get-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\*' -ErrorAction SilentlyContinue |
    Select-Object TaskName, State | Format-Table -AutoSize | Out-String | Write-Output
