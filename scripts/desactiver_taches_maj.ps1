# Tentative de desactivation des taches UpdateOrchestrator (protegees par le systeme).
# Ces taches declenchent des sessions de mise a jour ; elles sont inutiles a desactiver
# si wuauserv et UsoSvc sont deja arretes et desactives, mais on tente proprement.

$cibles = @(
    'UIEOrchestrator', 'Schedule Wake To Work', 'Schedule Work',
    'Schedule Scan', 'Schedule Scan Static Task', 'USO_UxBroker',
    'Start Oobe Expedite Work', 'UUS Failover Task'
)
$base = 'C:\Windows\System32\Tasks\Microsoft\Windows\UpdateOrchestrator'

foreach ($t in $cibles) {
    $etat = (Get-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\*' -TaskName $t -ErrorAction SilentlyContinue).State
    if (-not $etat) { Write-Output "ABSENTE  $t"; continue }
    try {
        Disable-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\' -TaskName $t -ErrorAction Stop | Out-Null
        Write-Output "OK       $t (etait $etat)"
        continue
    } catch { }

    # deuxieme essai : prise de possession du fichier de definition
    $f = Join-Path $base $t
    if (-not (Test-Path $f)) { Write-Output "ECHEC    $t : acces refuse, fichier introuvable"; continue }
    takeown /f "$f" /a 2>&1 | Out-Null
    icacls "$f" /grant "Administrateurs:F" 2>&1 | Out-Null
    try {
        Disable-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\' -TaskName $t -ErrorAction Stop | Out-Null
        Write-Output "OK       $t (apres prise de possession, etait $etat)"
    } catch {
        Write-Output "PROTEGEE $t : $($_.Exception.Message.Split([Environment]::NewLine)[0])"
    }
}
Write-Output ''
Get-ScheduledTask -TaskPath '\Microsoft\Windows\UpdateOrchestrator\*' -ErrorAction SilentlyContinue |
    Select-Object TaskName, State | Format-Table -AutoSize
