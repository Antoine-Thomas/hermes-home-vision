# Remise en service des deux taches UpdateOrchestrator restees Disabled apres
# restaurer_maj.ps1 (leur re-activation exige la meme prise de possession que la
# desactivation : elles appartiennent au systeme).

$ErrorActionPreference = 'Continue'
$taches = @('Schedule Wake To Work', 'Schedule Work')

foreach ($t in $taches) {
    $etat = (Get-ScheduledTask -TaskName $t -TaskPath '\Microsoft\Windows\UpdateOrchestrator\').State
    Write-Output "[$t] etat avant : $etat"
    if ($etat -eq 'Disabled') {
        Enable-ScheduledTask -TaskName $t -TaskPath '\Microsoft\Windows\UpdateOrchestrator\' -ErrorAction SilentlyContinue | Out-Null
        $f = "C:\Windows\System32\Tasks\Microsoft\Windows\UpdateOrchestrator\$t"
        takeown /f "$f" /a 2>&1 | Out-Null
        icacls "$f" /grant "BUILTIN\Administrators:F" 2>&1 | Out-Null
        Enable-ScheduledTask -TaskName $t -TaskPath '\Microsoft\Windows\UpdateOrchestrator\' -ErrorAction SilentlyContinue | Out-Null
        $etat = (Get-ScheduledTask -TaskName $t -TaskPath '\Microsoft\Windows\UpdateOrchestrator\').State
        Write-Output "[$t] etat apres : $etat"
    }
}

Write-Output ''
Write-Output '=== etat final des taches de mise a jour ==='
Get-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\*' |
    Select-Object TaskName, State | Format-Table -AutoSize

Write-Output '=== pause des mises a jour ==='
$k = 'HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings'
foreach ($n in @('PauseUpdatesExpiryTime', 'PauseFeatureUpdatesStartTime', 'PauseQualityUpdatesStartTime')) {
    $v = (Get-ItemProperty -Path $k -Name $n -ErrorAction SilentlyContinue).$n
    Write-Output ("  {0} = {1}" -f $n, $(if ($v) { $v } else { '(absent)' }))
}
