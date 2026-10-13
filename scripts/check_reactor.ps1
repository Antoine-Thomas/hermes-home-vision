<#
.SYNOPSIS
    Vérifie la chaîne ANIMA Reactor 0.3 : bridge UP, ports libres, state file frais,
    plage Wazuh vide, Wazuh actif, gateway Hermes.
.DESCRIPTION
    Contrôle en lecture seule, aucune modification. Sortie : OK / KO par check.
    À lancer AVANT le démarrage du watcher (procédure docs/REACTOR_INSTALL.md §3).
#>

$ErrorActionPreference = "Continue"
$allOk = $true

function Report([string]$name, [bool]$ok, [string]$detail) {
    $status = if ($ok) { "OK" } else { "KO" }
    if (-not $ok) { $script:allOk = $false }
    Write-Host ("[{0}] {1} : {2}" -f $status, $name, $detail)
}

# --- 1. Ports 55551/55552/55553 libres (avant lancement) ---
$ports = netstat -ano | Select-String "55551|55552|55553"
if ($ports) {
    Report "Ports 55551-55553" $false "occupés - un silo fantôme bloque la chaîne"
} else {
    Report "Ports 55551-55553" $true "libres"
}

# --- 2. Plage Wazuh 54985-55084 vide (hors plage du réacteur) ---
$wazuhRange = netstat -ano | Select-String "5498[5-9]|5499[0-9]|55[0-9]{3}|550[0-7][0-9]|5508[0-4]"
if ($wazuhRange) {
    Report "Plage Wazuh 54985-55084" $false "port actif détecté - ne PAS confondre avec le réacteur"
} else {
    Report "Plage Wazuh 54985-55084" $true "vide"
}

# --- 3. Service Wazuh ---
$wazuh = Get-Service WazuhSvc -ErrorAction SilentlyContinue
if ($wazuh -and $wazuh.Status -eq "Running") {
    Report "WazuhSvc" $true "Running"
} else {
    Report "WazuhSvc" $false "absent ou non démarré"
}

# --- 4. State file frais (_maj < 15 min) ---
$statePath = "C:\Users\searc\AppData\Local\hermes\data\route_ia_fix\health_anima_state.json"
if (Test-Path $statePath) {
    try {
        $state = Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $maj = [datetime]::Parse($state._maj)
        $age = (Get-Date) - $maj
        if ($age.TotalMinutes -lt 15) {
            Report "State file fraîcheur" $true ("_maj {0} (age {1:N0} min)" -f $maj, $age.TotalMinutes)
        } else {
            Report "State file fraîcheur" $false ("_maj {0} = {1:N0} min, > 15 min - signaler, ne pas relancer la tâche" -f $maj, $age.TotalMinutes)
        }
    } catch {
        Report "State file JSON" $false "illisible: $($_.Exception.Message)"
    }
} else {
    Report "State file" $false "absent: $statePath"
}

# --- 5. Bridge /status ---
try {
    $resp = Invoke-WebRequest -Uri "http://127.0.0.1:55553/status" -TimeoutSec 5 -UseBasicParsing
    if ($resp.StatusCode -eq 200) {
        Report "Bridge /status" $true ("HTTP 200 : {0}" -f $resp.Content)
    } else {
        Report "Bridge /status" $false ("HTTP {0}" -f $resp.StatusCode)
    }
} catch {
    Report "Bridge /status" $false "non joignable - bridge non lancé (dotnet run -c Debug dans C:/mari-poc/bridge)"
}

# --- 6. Gateway Hermes ---
$gw = Get-Process -Name "hermes" -ErrorAction SilentlyContinue
if ($gw) {
    Report "Gateway Hermes" $true ("processus hermes présent (PID {0})" -f ($gw.Id -join ","))
} else {
    Report "Gateway Hermes" $false "aucun processus hermes - gateway peut être un service (ne pas redémarrer ici)"
}

# --- Synthèse ---
Write-Host ""
if ($allOk) {
    Write-Host "CHAINE REACTOR : TOUS LES CHECKS OK - lancement autorisé (docs/REACTOR_INSTALL.md §2)"
    exit 0
} else {
    Write-Host "CHAINE REACTOR : AU MOINS UN CHECK KO - STOP, ne pas lancer le watcher"
    exit 1
}