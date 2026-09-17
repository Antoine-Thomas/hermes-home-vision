<#
    creer_tache_gateway.ps1 - SOURCE DE VERITE des taches planifiees du gateway Hermes.

    Role : produire un etat cible reproductible pour Hermes_Gateway (profil default) et
    Hermes_Gateway_watch (profil watch) :
      - declencheur Logon conserve (c'est le chemin historique)
      - PLUS un declencheur horaire avec repetition PT15M (releve un gateway mort en <=15 min)
      - StartWhenAvailable=True, MultipleInstances=IgnoreNew, ExecutionTimeLimit=PT0S

    Pourquoi une repetition est sure (verifie dans le code, pas suppose) :
      gateway/run.py::_start_gateway_claim_pid_file() est le verrou AUTORITATIF. Un second
      `gateway run` qui demarre alors qu'un gateway est vivant echoue au claim
      (get_running_pid -> "Another gateway instance (PID N) started during our startup",
      acquire_gateway_runtime_lock -> "runtime lock is already held", write_pid_file O_EXCL)
      et sort SANS double-run. Ce verrou est un fichier OS (msvcrt/flock) : "the OS releases
      it if the process dies" -> apres une mort brutale, le tick suivant reprend la main.
      Le preflight CLI _guard_existing_gateway_process_conflict est bien court-circuite par
      HERMES_SUPERVISED_CHILD=1 (pose par le VBS), mais le verrou runtime, lui, ne l'est pas.

    Methode : on repart du XML EXPORTE de la tache et on insere le second declencheur, plutot
    que de reconstruire la tache a la main -> le principal, les settings et l'action restent
    identiques au bit pres. Idempotent : si le declencheur PT15M existe deja, on ne fait rien.

    Usage :
      creer_tache_gateway.ps1                      # DryRun : affiche le diff prevu, n'ecrit rien
      creer_tache_gateway.ps1 -Apply               # applique
      creer_tache_gateway.ps1 -Apply -TaskName 'Hermes_Gateway_watch'
#>
param(
    [switch]$Apply,
    [string]$TaskName = 'Hermes_Gateway',
    [int]$IntervalMinutes = 15,
    [string]$StartBoundary = '00:05:00',
    [string]$TemplateTask,
    [string]$VbsPath,
    [switch]$Disabled
)

$ErrorActionPreference = 'Stop'
$interval = "PT${IntervalMinutes}M"

function Export-TaskXmlSafe([string]$name) {
    $xml = Export-ScheduledTask -TaskName $name
    if (-not $xml) { throw "Export-ScheduledTask a renvoye vide pour '$name'" }
    return $xml
}

# ------------------------------------------------------------------ branche CREATION
# La tache n'existe pas encore : on clone une tache gateway du parc (principal S4U + SID
# identiques) et on remplace nom, action (VBS cible) et intervalle. Rien n'est invente.
$tacheExistante = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if (-not $tacheExistante) {
    Write-Output "=== $TaskName : CREATION depuis le modele ==="
    if (-not $TemplateTask) { throw "tache '$TaskName' inexistante : -TemplateTask est obligatoire pour la creer" }
    if (-not $VbsPath) { throw "tache '$TaskName' inexistante : -VbsPath est obligatoire pour la creer" }
    if (-not (Test-Path $VbsPath)) { throw "VBS introuvable : $VbsPath" }
    if (-not (Get-ScheduledTask -TaskName $TemplateTask -ErrorAction SilentlyContinue)) { throw "modele '$TemplateTask' introuvable" }

    $xml = Export-ScheduledTask -TaskName $TemplateTask
    $xml = $xml -replace [regex]::Escape("<URI>\$TemplateTask</URI>"), "<URI>\$TaskName</URI>"
    $blocAction = [regex]::Match($xml, '(?s)<Exec>.*?</Exec>').Value
    if (-not $blocAction) { throw 'bloc <Exec> introuvable dans le modele' }
    $nouvelleAction = "  <Exec>`r`n    <Command>wscript.exe</Command>`r`n    <Arguments>//B //Nologo `"$VbsPath`"</Arguments>`r`n  </Exec>"
    $xml = $xml.Replace($blocAction, $nouvelleAction)
    if ($xml -notmatch "<Interval>$interval</Interval>") {
        $sb = (Get-Date).ToString('yyyy-MM-dd') + 'T00:05:00'
        $blocTrigger = "      <TimeTrigger>`r`n        <StartBoundary>$sb</StartBoundary>`r`n        <Repetition>`r`n          <Interval>$interval</Interval>`r`n        </Repetition>`r`n      </TimeTrigger>`r`n    </Triggers>"
        $xml = $xml -replace '(?s)(\s*)</Triggers>', ("`r`n" + $blocTrigger)
    }

    Write-Output "  modele            : $TemplateTask"
    Write-Output "  VBS               : $VbsPath"
    ($xml -split "`n" | Select-String -Pattern 'URI|Command|Arguments|Interval|StartBoundary|MultipleInstancesPolicy|StartWhenAvailable|UserId|LogonType').Line | ForEach-Object { Write-Output ("    " + $_.Trim()) }
    $controles = @{
        'une seule action'   = ([regex]::Matches($xml, '<Exec>')).Count -eq 1
        'intervalle attendu' = $xml -match "<Interval>$interval</Interval>"
        'VBS bien cible'     = $xml -match [regex]::Escape($VbsPath)
        'MultipleInstances'  = $xml -match 'IgnoreNew'
        'StartWhenAvailable' = $xml -match '<StartWhenAvailable>true</StartWhenAvailable>'
        'LogonTrigger'       = $xml -match '<LogonTrigger>'
    }
    foreach ($k in $controles.Keys) { Write-Output ("  controle {0,-20} : {1}" -f $k, $(if ($controles[$k]) { 'OK' } else { 'ECHEC' })) }
    if ($controles.Values -contains $false) { throw 'un controle a echoue : aucune ecriture' }

    if (-not $Apply) { Write-Output "  MODE DRYRUN : aucune ecriture. Relancer avec -Apply."; exit 0 }

    $backupDir = Join-Path $env:USERPROFILE 'Desktop\hermes_install\backups\taches'
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    Set-Content -Path (Join-Path $backupDir "$TaskName.defini_depuis_$TemplateTask.$(Get-Date -Format 'yyyyMMdd_HHmmss').xml") -Value $xml -Encoding UTF8
    Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force | Out-Null
    if ($Disabled) { Disable-ScheduledTask -TaskName $TaskName | Out-Null }
    $t = Get-ScheduledTask -TaskName $TaskName
    $i = $t | Get-ScheduledTaskInfo
    Write-Output "  ecriture          : OK | etat=$($t.State) | next=$($i.NextRunTime)"
    Write-Output "  declencheurs      : $((($t.Triggers | ForEach-Object { $_.CimClass.CimClassName -replace 'MSFT_Task','' }) -join ' + '))"
    Write-Output "  resultat          : SUCCES"
    exit 0
}

Write-Output "=== $TaskName ==="
$current = Export-TaskXmlSafe $TaskName

# Etat courant
$state = (Get-ScheduledTask -TaskName $TaskName).State
Write-Output "  etat actuel        : $state"

# Idempotence : le declencheur PT15M existe-t-il deja ?
$dejaPtr = ($current -match "<Repetition>" -and $current -match "<Interval>$interval</Interval>")
if ($dejaPtr) {
    Write-Output "  repetition $interval : DEJA PRESENTE -> rien a faire"
    Write-Output "  (idempotent : aucune ecriture)"
    exit 0
}

# Construction du nouveau declencheur
$heures = ($StartBoundary -split ':')[0]
$minutes = ($StartBoundary -split ':')[1]
$sb = (Get-Date).Date.AddHours([int]$heures).AddMinutes([int]$minutes)
$newTrigger = @"
    <TimeTrigger>
      <Repetition>
        <Interval>$interval</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>$($sb.ToString('yyyy-MM-ddTHH:mm:ss'))</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
"@

# Insertion juste avant la fermeture de <Triggers>
if ($current -notmatch '(?s)<Triggers>(.*?)</Triggers>') { throw "bloc <Triggers> introuvable dans le XML de $TaskName" }
$blocAvant = $Matches[0]
$triggerPropre = $newTrigger.TrimEnd("`r", "`n")
$blocApres = $blocAvant -replace '(?s)(\s*)</Triggers>', ("`r`n" + $triggerPropre + "`r`n  </Triggers>")
$nouveau = $current.Replace($blocAvant, $blocApres)

Write-Output "  --- bloc <Triggers> AVANT ---"
$blocAvant -split "`n" | ForEach-Object { Write-Output ("    " + $_) }
Write-Output "  --- bloc <Triggers> APRES (prevu) ---"
$blocApres -split "`n" | ForEach-Object { Write-Output ("    " + $_) }

# Controles de surete avant ecriture
$nAvant = ([regex]::Matches($current, '<(LogonTrigger|TimeTrigger|CalendarTrigger|BootTrigger)')).Count
$nApres = ([regex]::Matches($nouveau, '<(LogonTrigger|TimeTrigger|CalendarTrigger|BootTrigger)')).Count
Write-Output "  declencheurs       : $nAvant -> $nApres"
if ($nApres -ne $nAvant + 1) { throw "insertion incoherente ($nAvant -> $nApres) : abandon, aucune ecriture" }
if ($nouveau -notmatch '<Repetition>') { throw "le declencheur insere ne porte pas de <Repetition> : abandon" }
# Les settings critiques doivent etre intacts
foreach ($attendu in @('<StartWhenAvailable>true</StartWhenAvailable>', 'IgnoreNew')) {
    if ($current -match [regex]::Escape($attendu) -and $nouveau -notmatch [regex]::Escape($attendu)) {
        throw "un setting critique a disparu ($attendu) : abandon, aucune ecriture"
    }
}
Write-Output "  controles          : OK (1 declencheur ajoute, settings critiques conserves)"

if (-not $Apply) {
    Write-Output "  MODE DRYRUN : aucune ecriture. Relancer avec -Apply pour appliquer."
    exit 0
}

# Ecriture : sauvegarde du XML courant puis enregistrement
$backupDir = Join-Path $env:USERPROFILE 'Desktop\hermes_install\backups\taches'
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$backup = Join-Path $backupDir "$TaskName.avant_pt15m.$stamp.xml"
Set-Content -Path $backup -Value $current -Encoding UTF8
Write-Output "  backup XML         : $backup"

Register-ScheduledTask -TaskName $TaskName -Xml $nouveau -Force | Out-Null
Write-Output "  ecriture           : OK"

# Verification post-ecriture
$apres = Export-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTask -TaskName $TaskName | Get-ScheduledTaskInfo
$t = Get-ScheduledTask -TaskName $TaskName
Write-Output "  --- VERIFICATION ---"
Write-Output ("    etat             : " + $t.State)
Write-Output ("    declencheurs     : " + (($t.Triggers | ForEach-Object {
            $cls = $_.CimClass.CimClassName
            $rep = if ($_.Repetition -and $_.Repetition.Interval) { $_.Repetition.Interval } else { '-' }
            "$cls(rep=$rep)" }) -join ' + '))
Write-Output ("    StartWhenAvail   : " + $t.Settings.StartWhenAvailable)
Write-Output ("    MultipleInstances: " + $t.Settings.MultipleInstances)
Write-Output ("    NextRunTime      : " + $info.NextRunTime)
Write-Output ("    LastTaskResult   : " + $info.LastTaskResult)
if ($apres -notmatch "<Interval>$interval</Interval>") { throw "ECHEC : la repetition $interval n'est pas dans la tache apres ecriture" }
if ($apres -match '<LogonTrigger>') { Write-Output "    LogonTrigger     : conserve" } else { Write-Output "    ATTENTION : LogonTrigger absent apres ecriture" }
Write-Output "  resultat           : SUCCES"
