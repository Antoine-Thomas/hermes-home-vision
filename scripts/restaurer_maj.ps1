# Remet Windows Update et ses taches dans l'etat d'avant proteger_maj.ps1.
# A lancer APRES la fin du run LatentSync v5, quand la mise a jour peut se faire.

$ErrorActionPreference = 'Continue'
$journal = 'C:\Users\searc\AppData\Local\hermes\scripts\maj_etat_initial.json'
$UX = 'HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings'

if (-not (Test-Path $journal)) { Write-Output "journal introuvable : $journal"; exit 1 }
$etat = Get-Content $journal -Raw | ConvertFrom-Json
Write-Output "etat initial du $($etat.date)"

# 1. Retirer la pause
Remove-ItemProperty -Path $UX -Name 'PauseUpdatesExpiryTime' -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $UX -Name 'PauseFeatureUpdatesStartTime' -ErrorAction SilentlyContinue
Remove-ItemProperty -Path $UX -Name 'PauseQualityUpdatesStartTime' -ErrorAction SilentlyContinue
Write-Output '[1] pause des mises a jour retiree'

# 2. Heures actives d'origine
Set-ItemProperty -Path $UX -Name 'ActiveHoursStart' -Value $etat.active_hours_start -Type DWord
Set-ItemProperty -Path $UX -Name 'ActiveHoursEnd'   -Value $etat.active_hours_end   -Type DWord
if ($etat.smart_active_hours -and $etat.smart_active_hours -ne '') {
    Set-ItemProperty -Path $UX -Name 'SmartActiveHoursState' -Value ([int]$etat.smart_active_hours) -Type DWord
} else {
    Remove-ItemProperty -Path $UX -Name 'SmartActiveHoursState' -ErrorAction SilentlyContinue
}
Write-Output "[2] heures actives restaurees : $($etat.active_hours_start) -> $($etat.active_hours_end)"

# 3. Services
foreach ($s in $etat.services) {
    try {
        Set-Service -Name $s.name -StartupType $s.start -ErrorAction Stop
        if ($s.status -eq 'Running') { Start-Service -Name $s.name -ErrorAction SilentlyContinue }
        Write-Output "[3] $($s.name) : demarrage=$($s.start) etat=$($s.status)"
    } catch {
        Write-Output "[3] $($s.name) : $($_.Exception.Message.Split([Environment]::NewLine)[0])"
    }
}

# 4. Taches
foreach ($p in $etat.taches.PSObject.Properties) {
    if ($p.Value -eq 'ABSENTE') {
        Write-Output "[4] $($p.Name) : etait absente, ignoree"
        continue
    }
    try {
        if ($p.Value -eq 'Disabled') {
            Disable-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\' -TaskName $p.Name -ErrorAction Stop | Out-Null
        } else {
            Enable-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\' -TaskName $p.Name -ErrorAction Stop | Out-Null
        }
        Write-Output "[4] $($p.Name) : remise en $($p.Value)"
    } catch {
        Write-Output "[4] $($p.Name) : $($_.Exception.Message.Split([Environment]::NewLine)[0])"
    }
}

Write-Output ''
Write-Output '=== ETAT FINAL ==='
Get-Service wuauserv, UsoSvc | Select-Object Name, Status, StartType | Format-Table -AutoSize | Out-String | Write-Output
Get-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\*' -ErrorAction SilentlyContinue |
    Select-Object TaskName, State | Format-Table -AutoSize | Out-String | Write-Output
Write-Output 'Windows peut reprendre ses mises a jour. Un redemarrage reste du (RebootRequired) : il se fera quand vous le deciderez.'
