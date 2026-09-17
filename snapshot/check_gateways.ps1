# check_gateways.ps1 - surveillance active des gateways Hermes (source de verite du healthcheck)
#
# Complement de la repetition PT15M des taches planifiees :
#   - la repetition PT15M est un filet silencieux : elle releve en <=15 min, sans visibilite
#   - ce script detecte en <=5 min, releve explicitement, alerte et journalise
#
# Fonctionnement :
#   1. pour chaque profil surveille : lire gateway_state.json, tester que le PID est VIVANT
#      *et* que c'est bien un process gateway (commande contenant "gateway run") -> un PID
#      recycle ne compte pas comme vivant
#   2. PID mort sur un profil cense tourner -> relever via `schtasks /Run /TN <tache>`
#      (voie canonique : jamais `hermes gateway start`, dont l'enfant meurt avec le shell
#       porteur - piege Job Object #91675), puis second controle a T+30s
#   3. alerter sur Telegram sur TRANSITION d'etat uniquement (mort / releve / echec de relevage).
#      Alerter a chaque tick spammerait 12 fois par heure tant qu'un gateway reste down.
#   4. journal horodate logs/gateway-health.log, rotation a 10 Mo
#
# Profils surveilles :
#   - default : toujours
#   - watch   : toujours
#   - veille  : seulement si sa tache existe, est ACTIVE, et que son .env porte
#               TELEGRAM_BOT_TOKEN (sinon on relancerait un gateway sans plateforme pour rien)
#
# Alertes : bot VEILLE en priorite, bot DEFAULT en second. Le bot default est actuellement
# refuse par Telegram (403 "bot was blocked by the user"), d'ou cet ordre.
#
# Usage :
#   check_gateways.ps1                 # execution de surveillance (ce que lance la tache)
#   check_gateways.ps1 -DryRun         # constate et journalise, ne releve rien, n'alerte pas
#   check_gateways.ps1 -InstallTask    # montre la tache PT5M prevue (aucune ecriture)
#   check_gateways.ps1 -InstallTask -Apply

param(
    [switch]$DryRun,
    [switch]$InstallTask,
    [switch]$Apply,
    [int]$IntervalMinutes = 5,
    [int]$ConfirmDelaySeconds = 30,
    [int]$LogMaxMB = 10
)

$ErrorActionPreference = 'Stop'
$HermesHome = Join-Path $env:LOCALAPPDATA 'hermes'
$LogPath = Join-Path $HermesHome 'logs\gateway-health.log'
$StatePath = Join-Path $HermesHome 'logs\gateway-health.state.json'
$AlertChat = '8956868107'
$TaskName = 'Hermes_Gateway_HealthCheck'

$Profils = @(
    [pscustomobject]@{ Nom = 'default'; StateFile = (Join-Path $HermesHome 'gateway_state.json');                         Tache = 'Hermes_Gateway';       Toujours = $true },
    [pscustomobject]@{ Nom = 'watch';   StateFile = (Join-Path $HermesHome 'profiles\watch\gateway_state.json');        Tache = 'Hermes_Gateway_watch'; Toujours = $true },
    [pscustomobject]@{ Nom = 'veille';  StateFile = (Join-Path $HermesHome 'profiles\veille\gateway_state.json');       Tache = 'Hermes_Gateway_veille'; Toujours = $false }
)

function Write-Log([string]$message) {
    $line = "{0} {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $message
    try {
        if (Test-Path $LogPath) {
            $taille = (Get-Item $LogPath).Length
            if ($taille -gt ($LogMaxMB * 1MB)) {
                Move-Item -Path $LogPath -Destination "$LogPath.1" -Force
                $line = "{0} [rotation] journal > {1} Mo, bascule vers gateway-health.log.1`r`n{0} {2}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $LogMaxMB, $message
            }
        }
        Add-Content -Path $LogPath -Value $line -Encoding UTF8
    } catch { }
    Write-Output $line
}

function Get-PidDepuisState([string]$chemin) {
    if (-not (Test-Path $chemin)) { return $null }
    try {
        $json = Get-Content -Raw -Path $chemin -Encoding UTF8 | ConvertFrom-Json
        if ($json.pid) { return [int]$json.pid }
    } catch { }
    return $null
}

function Test-GatewayVivant([int]$processId) {
    if (-not $processId) { return $false }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
    if (-not $proc) { return $false }
    # un PID recycle sur un autre programme ne doit pas etre pris pour un gateway vivant
    if ($proc.CommandLine -and $proc.CommandLine -notmatch 'gateway\s+run') { return $false }
    return $true
}

function Get-TokenTelegram([string]$envPath) {
    if (-not (Test-Path $envPath)) { return $null }
    foreach ($ligne in (Get-Content -Path $envPath -Encoding UTF8)) {
        if ($ligne -match '^\s*TELEGRAM_BOT_TOKEN\s*=\s*(.+?)\s*$') { return $Matches[1].Trim('"').Trim("'") }
    }
    return $null
}

function Send-Alerte([string]$texte) {
    $candidats = @(
        (Get-TokenTelegram (Join-Path $HermesHome 'profiles\veille\.env')),
        (Get-TokenTelegram (Join-Path $HermesHome '.env'))
    ) | Where-Object { $_ }
    foreach ($token in $candidats) {
        try {
            Invoke-RestMethod -Uri ("https://api.telegram.org/bot{0}/sendMessage" -f $token) -Method Post `
                -Body @{ chat_id = $AlertChat; text = $texte; disable_web_page_preview = 'true' } `
                -TimeoutSec 20 | Out-Null
            return $true
        } catch {
            continue
        }
    }
    return $false
}

function Get-EtatPrecedent {
    if (-not (Test-Path $StatePath)) { return @{} }
    try { return (Get-Content -Raw $StatePath -Encoding UTF8 | ConvertFrom-Json) } catch { return @{} }
}

# ---------------------------------------------------------------- installation de la tache
if ($InstallTask) {
    $vbs = Join-Path $HermesHome 'hermes-agent'
    if (-not (Get-Command powershell.exe -ErrorAction SilentlyContinue)) { throw 'powershell.exe introuvable' }
    $script = $PSCommandPath
    $template = 'Hermes_Gateway_watch'
    if (-not (Get-ScheduledTask -TaskName $template -ErrorAction SilentlyContinue)) { throw "tache modele '$template' introuvable" }

    $xml = Export-ScheduledTask -TaskName $template
    $xml = $xml -replace '<URI>\\Hermes_Gateway_watch</URI>', "<URI>\$TaskName</URI>"
    $xml = $xml -replace '<Description>[^<]*</Description>', '<Description>Hermes Gateway healthcheck PT5M - detection et relevage des gateways morts</Description>'
    # action : powershell sur ce script, au lieu du wscript du gateway
    $nouvelleAction = @"
  <Exec>
    <Command>powershell.exe</Command>
    <Arguments>-NoProfile -ExecutionPolicy Bypass -File "$script"</Arguments>
  </Exec>
"@
    $blocAction = [regex]::Match($xml, '(?s)<Exec>.*?</Exec>').Value
    if (-not $blocAction) { throw 'bloc <Exec> introuvable dans le modele' }
    $xml = $xml.Replace($blocAction, $nouvelleAction.TrimEnd())
    # periode : PT5M au lieu de PT15M
    $xml = $xml -replace '<Interval>PT15M</Interval>', "<Interval>PT$($IntervalMinutes)M</Interval>"

    Write-Output "=== tache '$TaskName' (prevu) ==="
    ($xml -split "`n" | Select-String -Pattern 'Command|Arguments|Interval|StartBoundary|MultipleInstances|StartWhenAvailable|UserId|LogonType').Line | ForEach-Object { Write-Output ("  " + $_.Trim()) }
    $controles = @{
        'une seule action'      = ([regex]::Matches($xml, '<Exec>')).Count -eq 1
        'intervalle PT5M'       = $xml -match "<Interval>PT$($IntervalMinutes)M</Interval>"
        'script bien cible'     = $xml -match [regex]::Escape($script)
        'MultipleInstances'     = $xml -match 'IgnoreNew'
        'StartWhenAvailable'    = $xml -match '<StartWhenAvailable>true</StartWhenAvailable>'
    }
    foreach ($k in $controles.Keys) {
        Write-Output ("  controle {0,-20} : {1}" -f $k, $(if ($controles[$k]) { 'OK' } else { 'ECHEC' }))
    }
    if ($controles.Values -contains $false) { throw 'un controle a echoue : aucune ecriture' }

    if (-not $Apply) {
        Write-Output "  MODE DRYRUN : aucune ecriture. Relancer avec -Apply."
        exit 0
    }
    $backupDir = Join-Path $env:USERPROFILE 'Desktop\hermes_install\backups\taches'
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Export-ScheduledTask -TaskName $TaskName | Set-Content -Path (Join-Path $backupDir "$TaskName.avant_install.$(Get-Date -Format 'yyyyMMdd_HHmmss').xml") -Encoding UTF8
    }
    Register-ScheduledTask -TaskName $TaskName -Xml $xml -Force | Out-Null
    $t = Get-ScheduledTask -TaskName $TaskName
    $i = $t | Get-ScheduledTaskInfo
    Write-Output "  ecriture : OK | etat=$($t.State) next=$($i.NextRunTime)"
    Write-Output "  declencheurs : $((($t.Triggers | ForEach-Object { $_.CimClass.CimClassName -replace 'MSFT_Task','' }) -join ' + '))"
    exit 0
}

# ---------------------------------------------------------------- execution de surveillance
$deja = Get-EtatPrecedent
$nouvelEtat = @{}
$alertes = @()
$surveillesNoms = @()

foreach ($p in $Profils) {
    $surveille = $p.Toujours
    $raisonNonSurveille = ''
    if (-not $surveille) {
        $tacheObj = Get-ScheduledTask -TaskName $p.Tache -ErrorAction SilentlyContinue
        $token = Get-TokenTelegram (Join-Path $HermesHome ("profiles\{0}\.env" -f $p.Nom))
        if (-not $tacheObj) { $raisonNonSurveille = 'pas de tache planifiee' }
        elseif ($tacheObj.State -eq 'Disabled') { $raisonNonSurveille = 'tache desactivee' }
        elseif (-not $token) { $raisonNonSurveille = 'pas de TELEGRAM_BOT_TOKEN' }
        else { $surveille = $true }
    }

    $gwPid = Get-PidDepuisState $p.StateFile
    $vivant = Test-GatewayVivant $gwPid
    $etat = if ($vivant) { 'up' } else { 'down' }
    $nouvelEtat[$p.Nom] = $etat

    if (-not $surveille) {
        Write-Log ("[{0}] non surveille ({1}) | pid={2} etat_pid={3}" -f $p.Nom, $raisonNonSurveille, $gwPid, $etat)
        continue
    }
    $surveillesNoms += $p.Nom

    if ($vivant) {
        Write-Log ("[{0}] OK pid={1} vivant" -f $p.Nom, $gwPid)
        if ($deja.($p.Nom) -eq 'down') {
            $alertes += "[$($p.Nom)] gateway de nouveau VIVANT (pid $gwPid)"
        }
        continue
    }

    Write-Log ("[{0}] MORT pid={1} (state file {2})" -f $p.Nom, $gwPid, $p.StateFile)
    if ($deja.($p.Nom) -ne 'down') {
        $alertes += "[$($p.Nom)] gateway MORT detecte (dernier pid $gwPid)"
    }

    if ($DryRun) {
        Write-Log ("[{0}] DryRun : relevage non tente" -f $p.Nom)
        continue
    }

    # relevage par la voie canonique
    $tacheObj = Get-ScheduledTask -TaskName $p.Tache -ErrorAction SilentlyContinue
    if (-not $tacheObj) {
        Write-Log ("[{0}] pas de tache '{1}' : relevage impossible, alerte envoyee" -f $p.Nom, $p.Tache)
        $alertes += "[$($p.Nom)] gateway mort, AUCUNE tache '$($p.Tache)' pour le relever"
        continue
    }
    try {
        Start-ScheduledTask -TaskName $p.Tache
        Write-Log ("[{0}] relevage lance : Start-ScheduledTask '{1}'" -f $p.Nom, $p.Tache)
    } catch {
        Write-Log ("[{0}] ECHEC du relevage : {1}" -f $p.Nom, $_.Exception.Message)
        $alertes += "[$($p.Nom)] relevage ECHOUE ($($_.Exception.Message))"
        continue
    }

    Start-Sleep -Seconds $ConfirmDelaySeconds
    $pid2 = Get-PidDepuisState $p.StateFile
    if (Test-GatewayVivant $pid2) {
        Write-Log ("[{0}] RELEVE OK a T+{1}s : pid={2}" -f $p.Nom, $ConfirmDelaySeconds, $pid2)
        $nouvelEtat[$p.Nom] = 'up'
        $alertes += "[$($p.Nom)] gateway RELEVE (pid $pid2) en moins de $ConfirmDelaySeconds s"
    } else {
        Write-Log ("[{0}] ECHEC : toujours mort a T+{1}s (pid state={2})" -f $p.Nom, $ConfirmDelaySeconds, $pid2)
        $alertes += "[$($p.Nom)] gateway TOUJOURS MORT apres relevage (T+$ConfirmDelaySeconds s) - intervention requise"
    }
}

# ---------------------------------------------------------------- battement horaire
# Un log horaire MEME quand tout va bien : c'est lui qui donne l'historique de disponibilite
# sur 24 h (une ligne par heure, lisible et parsable par scripts\verif_24h.ps1). Les lignes
# par tick existent deja plus haut ; ce battement est le resume compact, ecrit une seule fois
# par heure (premier tick qui suit le changement d'heure).
$heureCourante = Get-Date -Format 'yyyy-MM-ddTHH'
$dernierBattement = $deja.'_battement_heure'
if ($dernierBattement -ne $heureCourante) {
    $noms = @($surveillesNoms | Select-Object -Unique)
    $up = @($noms | Where-Object { $nouvelEtat[$_] -eq 'up' })
    $detail = ($noms | ForEach-Object { "{0}={1}" -f $_, $nouvelEtat[$_] }) -join ' '
    Write-Log ("[battement] {0}h : {1}/{2} gateways up, {3} alerte(s) | {4}" -f $heureCourante, $up.Count, $noms.Count, $alertes.Count, $detail)
    $nouvelEtat['_battement_heure'] = $heureCourante
    $nouvelEtat['_battement_le'] = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
} else {
    # L'etat est REEcrit a chaque tick : sans ce report, l'horodatage du dernier battement
    # disparait au tick suivant et la meme heure est re-journalisee (constate en test).
    if ($dernierBattement) { $nouvelEtat['_battement_heure'] = $dernierBattement }
    if ($deja.'_battement_le') { $nouvelEtat['_battement_le'] = $deja.'_battement_le' }
}

try { $nouvelEtat | ConvertTo-Json | Set-Content -Path $StatePath -Encoding UTF8 } catch { }

if ($alertes.Count -gt 0 -and -not $DryRun) {
    $texte = "🔔 Gates: healthcheck Hermes $(Get-Date -Format 'dd/MM HH:mm')`n" + ($alertes -join "`n")
    $ok = Send-Alerte $texte
    Write-Log ("[alerte] {0} alerte(s) envoyee(s)={1}" -f $alertes.Count, $ok)
} else {
    Write-Log ("[alerte] aucune transition d'etat, pas d'alerte")
}
