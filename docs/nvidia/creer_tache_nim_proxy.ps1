# ---------------------------------------------------------------------------
# Recree / durcit la tache planifiee 'Hermes_NVIDIA_NIM_Proxy'
# (proxy NVIDIA NIM sur 127.0.0.1:20200, lanceur nvidia-nim-launch.vbs).
#
# Re-executable apres incident : ce script est la source de verite de l'etat
# cible de la tache. Relance-le tel quel pour revenir a l'etat voulu.
#
# Etat cible :
#   - Declencheur logon conserve a l'identique (contrat d'origine du parc)
#   - + declencheur horaire "Once" ancre dans le passe, portant une repetition
#     toutes les 15 min, duree illimitee.
#     POURQUOI un second declencheur : la repetition d'un declencheur *logon*
#     ne s'arme qu'au prochain logon (NextRunTime reste vide). Un proxy qui
#     meurt en cours de session ne serait releve qu'a la prochaine session
#     utilisateur -- c'est exactement la panne de 4 jours du 13 au 17/09.
#     La repetition n'est PAS posee sur le declencheur logon : deux repetitions
#     desynchronisees doubleraient la cadence pour rien.
#   - StartWhenAvailable = True  (rattrape un run manque, PC eteint)
#   - MultipleInstancesPolicy = IgnoreNew (jamais deux lancements concurrents ;
#     le VBS est de toute facon idempotent : si 20200 ecoute, il sort)
#   - ExecutionTimeLimit inchange (PT72H)
#
# Backup automatique de la definition XML avant toute modification.
# ---------------------------------------------------------------------------
param(
    [string]$TaskName          = 'Hermes_NVIDIA_NIM_Proxy',
    [string]$VbsPath           = 'C:\Users\searc\AppData\Local\hermes\data\nvidia\nvidia-nim-launch.vbs',
    [int]   $RepetitionMinutes = 15,
    [string]$BackupDir         = 'C:\Users\searc\AppData\Local\hermes\data\nvidia\backups',
    [switch]$NoBackup
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $VbsPath)) { throw "Lanceur introuvable : $VbsPath" }
if (-not (Test-Path $BackupDir)) { New-Item -ItemType Directory -Path $BackupDir | Out-Null }

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop

# 1) Backup XML avant modif ---------------------------------------------------
if (-not $NoBackup) {
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $bp = Join-Path $BackupDir ("$TaskName.$stamp.xml")
    Export-ScheduledTask -TaskName $TaskName | Out-File -FilePath $bp -Encoding UTF8
    Write-Host "[backup] $bp"
}

# 2) Declencheur logon conserve, a l'identique --------------------------------
$logon = $task.Triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger' } | Select-Object -First 1
if (-not $logon) {
    Write-Host "[info] aucun declencheur logon trouve - creation d'un declencheur AtLogOn"
    $logon = New-ScheduledTaskTrigger -AtLogOn
}
# Le declencheur logon doit rester SANS repetition : sinon, une fois arme au
# prochain logon, il se desynchronise du declencheur horaire et la cadence
# double. La repetition vit uniquement sur le declencheur horaire.
$logon.Repetition = $null

# 3) Declencheur horaire qui arme la repetition des maintenant -----------------
$timer = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(-1) `
            -RepetitionInterval (New-TimeSpan -Minutes $RepetitionMinutes)

# 4) Reglages ----------------------------------------------------------------
$s = $task.Settings
$s.StartWhenAvailable = $true
$s.MultipleInstances  = 'IgnoreNew'

# 5) Action (conservee a l'identique) ----------------------------------------
$action = New-ScheduledTaskAction -Execute 'wscript.exe' -Argument ('"{0}"' -f $VbsPath)

Set-ScheduledTask -TaskName $TaskName -Trigger @($logon, $timer) -Settings $s -Action $action | Out-Null

# 6) Verification ------------------------------------------------------------
Write-Host "[ok] tache '$TaskName' mise a jour"
$t = Get-ScheduledTask -TaskName $TaskName
$i = $t | Get-ScheduledTaskInfo
Write-Host ("     State={0} Enabled={1}" -f $t.State, $t.Settings.Enabled)
Write-Host ("     Trigger: {0}" -f (($t.Triggers | ForEach-Object { $_.CimClass.CimClassName + ' start=' + $_.StartBoundary + ' rep=' + $_.Repetition.Interval + ' dur=' + $_.Repetition.Duration }) -join ' | '))
Write-Host ("     Settings: StartWhenAvailable={0} MultipleInstances={1} ExecTimeLimit={2}" -f $t.Settings.StartWhenAvailable, $t.Settings.MultipleInstances, $t.Settings.ExecutionTimeLimit)
Write-Host ("     Action: {0}" -f (($t.Actions | ForEach-Object { $_.Execute + ' ' + $_.Arguments }) -join ' | '))
Write-Host ("     NextRunTime={0}" -f $i.NextRunTime)
if (-not $i.NextRunTime) { Write-Warning "NextRunTime vide : la repetition n'est pas armee" }
