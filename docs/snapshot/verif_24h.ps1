# verif_24h.ps1 - Rapport de verification a T+24h du chantier "mode observation".
#
# Compare l'etat MESURE MAINTENANT a la baseline T0 (snapshot\baseline_T0.json, produite par
# scripts\baseline_t0.py) et imprime un verdict. A lancer a la main, ~24 h apres le T0 :
#   powershell -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\hermes\scripts\verif_24h.ps1"
#
# Ce qu'il controle :
#   1. ecart horaire reel depuis le T0 de la baseline
#   2. SiYuan  : /api/notebook/lsNotebooks -> code 0 et MEME nombre de notebooks qu'au T0
#   3. RAG     : GET /sante -> 200 + status ok, fragments >= T0 (un index qui grossit est normal)
#   4. cron    : job veille (id de la baseline) encore arme, avec sa prochaine execution
#   5. healthcheck : tache planifiee armee + NOMBRE DE TICKS horaires traces dans les 24 h
#      (les lignes [battement] du journal) et disponibilite par profil sur ces ticks
#   6. gateways : PID vivant ET process "gateway run" pour chaque profil surveille
#   7. alertes : nombre d'alertes REELLEMENT envoyees sur 24 h (et morts detectees)
#   8. A2A     : 9900/9901 muets et 0 cle A2A_* (non-regression de la decision "A2A reste OFF")
#
# Sortie : resume a l'ecran + rapport horodate dans Desktop\hermes_install\snapshot\verif_24h_<date>.txt
# Code de sortie : 0 = tout vert, 1 = au moins un controle rouge.
#
# Usage :
#   verif_24h.ps1                                   # run normal (baseline T0 reelle)
#   verif_24h.ps1 -BaselinePath <chemin.json>       # comparer a une autre baseline (tests)
#   verif_24h.ps1 -NoReport                         # ne rien ecrire sur disque

param(
    [string]$BaselinePath = "$env:USERPROFILE\Desktop\hermes_install\snapshot\baseline_T0.json",
    [int]$FenetreHeures = 24,
    [switch]$NoReport
)

$ErrorActionPreference = 'Stop'
$HermesHome = Join-Path $env:LOCALAPPDATA 'hermes'
$LogPath = Join-Path $HermesHome 'logs\gateway-health.log'
$SnapshotDir = Join-Path $env:USERPROFILE 'Desktop\hermes_install\snapshot'
$Echecs = @()

function Titre($t) { Write-Host ""; Write-Host ("== " + $t) -ForegroundColor Cyan }
function Ligne($etat, $texte) {
    $couleur = switch ($etat) { 'OK' { 'Green' } 'ATTENTION' { 'Yellow' } default { 'Red' } }
    Write-Host ("  [{0,-9}] {1}" -f $etat, $texte) -ForegroundColor $couleur
    if ($etat -eq 'ECHEC') { $script:Echecs += $texte }
}

if (-not (Test-Path $BaselinePath)) { Write-Host ("baseline introuvable : " + $BaselinePath) -ForegroundColor Red; exit 1 }
$base = Get-Content -Raw -Path $BaselinePath -Encoding UTF8 | ConvertFrom-Json

$maintenant = Get-Date
$t0 = [datetime]::Parse($base.t0)
$ecoule = $maintenant - $t0
$depuis = $maintenant.AddHours(-$FenetreHeures)

Titre "Ecart horaire"
Ligne 'OK' ("T0 " + $t0.ToString('yyyy-MM-dd HH:mm:ss') + " -> maintenant " + $maintenant.ToString('yyyy-MM-dd HH:mm:ss') + " = " + [math]::Round($ecoule.TotalHours,1) + " h")
if ($ecoule.TotalHours -lt ($FenetreHeures - 2)) {
    Ligne 'ATTENTION' ("moins de " + $FenetreHeures + " h ecoulees : l'observation n'a pas encore la duree voulue, relire ce rapport plus tard")
}

# ---------------------------------------------------------------- 1. SiYuan
Titre "SiYuan (notebooks)"
$jetonSiYuan = $null
$envFile = Join-Path $HermesHome '.env'
if (Test-Path $envFile) {
    foreach ($l in (Get-Content $envFile -Encoding UTF8)) { if ($l -match '^\s*SIYUAN_TOKEN\s*=\s*(.+?)\s*$') { $jetonSiYuan = $Matches[1].Trim('"').Trim("'") } }
}
$nbSiYuan = -1
if (-not $jetonSiYuan) {
    Ligne 'ECHEC' 'jeton SiYuan introuvable dans le .env du profil (impossible de controler)'
} else {
    try {
        $r = Invoke-RestMethod -Uri 'http://127.0.0.1:6806/api/notebook/lsNotebooks' -Method Post `
             -Headers @{ Authorization = "Token $jetonSiYuan" } -ContentType 'application/json' -Body '{}' -TimeoutSec 10
        $nbSiYuan = @($r.data.notebooks).Count
        if ($r.code -eq 0 -and $nbSiYuan -eq $base.siyuan.notebooks) {
            Ligne 'OK' ("code=0, " + $nbSiYuan + " notebooks (identique au T0)")
        } elseif ($r.code -eq 0) {
            Ligne 'ATTENTION' ("code=0 mais " + $nbSiYuan + " notebooks au lieu de " + $base.siyuan.notebooks + " au T0")
        } else {
            Ligne 'ECHEC' ("code=" + $r.code + " (attendu 0)")
        }
    } catch {
        Ligne 'ECHEC' ("appel SiYuan en echec : " + $_.Exception.Message)
    }
}

# ---------------------------------------------------------------- 2. RAG
Titre "RAG (service 8200)"
try {
    $sante = Invoke-RestMethod -Uri 'http://127.0.0.1:8200/sante' -Method Get -TimeoutSec 10
    if ($sante.status -eq 'ok' -and [int]$sante.fragments -ge [int]$base.rag.fragments) {
        Ligne 'OK' ("/sante 200, status=ok, " + $sante.fragments + " fragments (T0 : " + $base.rag.fragments + ")")
    } else {
        Ligne 'ATTENTION' ("/sante repond mais status=" + $sante.status + " fragments=" + $sante.fragments + " (T0 : " + $base.rag.fragments + ")")
    }
} catch {
    Ligne 'ECHEC' ("/sante injoignable : " + $_.Exception.Message)
}

# ---------------------------------------------------------------- 3. cron veille
Titre "Cron veille-hebdo"
try {
    $cron = & hermes -p veille cron list 2>&1 | Out-String
    if ($cron -match [regex]::Escape($base.cron_veille.job_id)) {
        $actif = $cron -match '\[active\]'
        $prochain = ([regex]::Match($cron, 'Next run:\s+(\S+)')).Groups[1].Value
        if ($actif) { Ligne 'OK' ("job " + $base.cron_veille.job_id + " [active], prochaine execution " + $prochain) }
        else { Ligne 'ECHEC' ("job " + $base.cron_veille.job_id + " present mais NON actif") }
    } else {
        Ligne 'ECHEC' ("job " + $base.cron_veille.job_id + " introuvable dans 'hermes -p veille cron list'")
    }
} catch {
    Ligne 'ECHEC' ("hermes -p veille cron list en echec : " + $_.Exception.Message)
}

# ---------------------------------------------------------------- 4. healthcheck + ticks horaires
Titre ("Healthcheck : ticks horaires sur " + $FenetreHeures + " h")
# Battements indexes par HEURE : un doublon de la meme heure (bug corrige, ou test manuel)
# ne doit pas compter comme deux ticks d'observation.
$battements = @{}
$alertesEnvoyees = 0
$morts = 0
if (Test-Path $LogPath) {
    foreach ($l in (Get-Content $LogPath -Encoding UTF8)) {
        if ($l -match '^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})') {
            $ts = [datetime]::Parse($Matches[1])
            if ($ts -ge $depuis) {
                if ($l -match '\[battement\]') { $battements[$ts.ToString('yyyy-MM-ddTHH')] = $l }
                if ($l -match '\[alerte\] (\d+) alerte\(s\) envoyee\(s\)=True') { $alertesEnvoyees += [int]$Matches[1] }
                if ($l -match '\[.*\] MORT') { $morts++ }
            }
        }
    }
} else {
    Ligne 'ECHEC' ("journal introuvable : " + $LogPath)
}

$ticks = $battements.Count
$dispo = @{}
foreach ($nom in @('default', 'watch', 'veille')) { $dispo[$nom] = 0 }
foreach ($l in $battements.Values) {
    foreach ($nom in @($dispo.Keys)) {
        if ($l -match ("(^|\s)" + $nom + "=up")) { $dispo[$nom] = $dispo[$nom] + 1 }
    }
}
$attendu = [math]::Max(1, [math]::Floor($FenetreHeures))
if ($ticks -ge ($attendu - 1)) {
    Ligne 'OK' ($ticks.ToString() + " ticks horaires traces sur " + $FenetreHeures + " h (attendu ~" + $attendu + ")")
} else {
    Ligne 'ATTENTION' ($ticks.ToString() + " ticks horaires seulement sur " + $FenetreHeures + " h (attendu ~" + $attendu + ") : battement ajoute en cours de fenetre, ou tache en retard")
}
foreach ($nom in @('default', 'watch', 'veille')) {
    $pct = if ($ticks -gt 0) { [math]::Round(100 * $dispo[$nom] / $ticks) } else { 0 }
    $etat = if ($ticks -eq 0) { 'ATTENTION' } elseif ($pct -eq 100) { 'OK' } elseif ($pct -ge 90) { 'ATTENTION' } else { 'ECHEC' }
    Ligne $etat ($nom + " : " + $dispo[$nom] + "/" + $ticks + " ticks up (" + $pct + "%)")
}

# ---------------------------------------------------------------- 5. gateways vivants la, maintenant
Titre "Gateways (PID vivant + process 'gateway run')"
$upCount = 0
$profilsGw = @(
    @{ Nom = 'default'; State = (Join-Path $HermesHome 'gateway_state.json') },
    @{ Nom = 'watch';   State = (Join-Path $HermesHome 'profiles\watch\gateway_state.json') },
    @{ Nom = 'veille';  State = (Join-Path $HermesHome 'profiles\veille\gateway_state.json') }
)
foreach ($p in $profilsGw) {
    $pidGw = $null
    if (Test-Path $p.State) {
        try { $pidGw = [int]((Get-Content -Raw $p.State -Encoding UTF8 | ConvertFrom-Json).pid) } catch { }
    }
    $vivant = $false
    if ($pidGw) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pidGw" -ErrorAction SilentlyContinue
        if ($proc -and ($proc.CommandLine -match 'gateway\s+run')) { $vivant = $true }
    }
    if ($vivant) { $upCount++; Ligne 'OK' ($p.Nom + " vivant (pid " + $pidGw + ")") }
    else { Ligne 'ECHEC' ($p.Nom + " NON vivant (pid state=" + $pidGw + ")") }
}

Titre "Alertes sur la fenetre"
if ($alertesEnvoyees -eq 0 -and $morts -eq 0) { Ligne 'OK' "0 alerte envoyee, 0 mort detectee" }
elseif ($morts -eq 0) { Ligne 'ATTENTION' ($alertesEnvoyees.ToString() + " alerte(s) envoyee(s), 0 mort detectee") }
else { Ligne 'ATTENTION' ($alertesEnvoyees.ToString() + " alerte(s) envoyee(s), " + $morts + " ligne(s) de mort detectee(s)") }

# ---------------------------------------------------------------- 6. A2A reste OFF
Titre "Non-regression A2A (doit rester OFF)"
$ecouteA2A = @()
foreach ($port in @(9900, 9901)) {
    $res = (cmd /c ("netstat -ano | findstr :" + $port + " ")) 2>$null
    if ($res) { $ecouteA2A += $port }
}
if ($ecouteA2A.Count -eq 0) { Ligne 'OK' "9900 et 9901 muets" } else { Ligne 'ECHEC' ("port(s) A2A en ecoute : " + ($ecouteA2A -join ', ')) }
$nbCles = 0
foreach ($f in @((Join-Path $HermesHome '.env'), (Join-Path $HermesHome 'profiles\watch\.env'), (Join-Path $HermesHome 'profiles\veille\.env'))) {
    if (Test-Path $f) {
        foreach ($l in (Get-Content $f -Encoding UTF8)) { if ($l -match '^\s*A2A_') { $nbCles++ } }
    }
}
if ($nbCles -eq 0) { Ligne 'OK' "0 cle A2A_* dans les .env" } else { Ligne 'ECHEC' ($nbCles.ToString() + " cle(s) A2A_* posee(s) dans un .env alors qu'A2A doit rester OFF") }

# ---------------------------------------------------------------- rapport
$verdict = if ($Echecs.Count -eq 0) { 'VERT' } else { 'ROUGE (' + $Echecs.Count + ' echec(s))' }
$dernierTick = if ($ticks -gt 0) { ($battements.Values | Sort-Object | Select-Object -Last 1) } else { '' }
$mUp = [regex]::Match($dernierTick, '(\d+)/(\d+) gateways up')
$upDernier = if ($mUp.Success) { $mUp.Groups[1].Value + '/' + $mUp.Groups[2].Value } else { 'n/a' }
$cronEtat = if ($cron -match [regex]::Escape($base.cron_veille.job_id)) { 'arme' } else { 'ABSENT' }
$a2aEtat = if ($ecouteA2A.Count -eq 0 -and $nbCles -eq 0) { 'oui' } else { 'NON' }
Titre "Synthese"
$resume = "{0:0.0} h ecoulees | {1} gateways up au dernier tick ({2} ticks horaires traces) | {3} alerte(s) | cron veille {4} | A2A OFF : {5} | verdict {6}" -f `
    $ecoule.TotalHours, $upDernier, $ticks, $alertesEnvoyees, $cronEtat, $a2aEtat, $verdict
Write-Host ("  " + $resume) -ForegroundColor $(if ($Echecs.Count -eq 0) { 'Green' } else { 'Red' })

if (-not $NoReport) {
    if (-not (Test-Path $SnapshotDir)) { New-Item -ItemType Directory -Force -Path $SnapshotDir | Out-Null }
    $rapport = Join-Path $SnapshotDir ("verif_24h_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".txt")
    $contenu = @(
        ("Rapport verif_24h - " + $maintenant.ToString('yyyy-MM-dd HH:mm:ss')),
        ("baseline    : " + $BaselinePath + " (T0 " + $t0.ToString('yyyy-MM-dd HH:mm:ss') + ")"),
        ("ecart       : " + [math]::Round($ecoule.TotalHours,1) + " h"),
        ("ticks       : " + $ticks + " lignes [battement] sur " + $FenetreHeures + " h"),
        ("dispo       : " + (($dispo.Keys | ForEach-Object { $_ + "=" + $dispo[$_] + "/" + $ticks }) -join ' ')),
        ("gateways    : " + $upCount + "/3 vivants maintenant"),
        ("alertes     : " + $alertesEnvoyees + " envoyee(s), " + $morts + " mort(s) detectee(s)"),
        ("cron veille : " + $base.cron_veille.job_id + " " + $cronEtat),
        ("dernier tick: " + $upDernier + " gateways up"),
        ("A2A         : ports " + $(if ($ecouteA2A.Count -eq 0) { 'muets' } else { 'EN ECOUTE ' + ($ecouteA2A -join ',') }) + " ; cles A2A_* = " + $nbCles),
        ("verdict     : " + $verdict),
        ("echecs      : " + $(if ($Echecs.Count -eq 0) { 'aucun' } else { $Echecs -join ' | ' }))
    )
    Set-Content -Path $rapport -Value $contenu -Encoding UTF8
    Write-Host ("  rapport ecrit : " + $rapport)
}

if ($Echecs.Count -gt 0) { exit 1 }
exit 0
