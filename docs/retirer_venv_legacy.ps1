# retire_venv_legacy.ps1 — met a la retraite le venv Hermes perime (.venv -> .venv.retired-0.20.5)
#
# A EXECUTER DEPUIS UN SHELL PROPRE (PowerShell hors session Hermes) :
# tant qu'une session CLI tourne dans .venv, Windows refuse le renommage
# (IOException "acces refuse") car ses processus ont des fichiers ouverts dedans.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\searc\AppData\Local\hermes\docs\retirer_venv_legacy.ps1"
#
# Reversible a tout moment : Rename-Item ".venv.retired-0.20.5" ".venv"
# Aucune suppression. Aucune synchro pip. Le venv de reference (venv) n'est pas touche.

$ErrorActionPreference = 'Continue'
$home_   = 'C:\Users\searc\AppData\Local\hermes'
$repo    = Join-Path $home_ 'hermes-agent'
$src     = Join-Path $repo '.venv'
$dst     = Join-Path $repo '.venv.retired-0.20.5'
$logf    = Join-Path $home_ 'docs\retirer_venv_legacy.log'

function Log([string]$m) {
    $line = ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m)
    Write-Output $line
    Add-Content -LiteralPath $logf -Value $line -Encoding UTF8
}

Log '=== mise a la retraite du venv perime ==='

# 1. Qui utilise encore .venv ?
$users = Get-CimInstance Win32_Process |
         Where-Object { $_.CommandLine -like '*hermes-agent\.venv*' -and $_.Name -ne 'powershell.exe' }
if ($users) {
    Log ('ABANDON : {0} processus utilisent encore .venv' -f @($users).Count)
    foreach ($p in $users) { Log ('   PID {0} {1} << {2}' -f $p.ProcessId, $p.Name, ($p.CommandLine -replace '\s+',' ')) }
    Log 'Ferme la session Hermes concernee, puis relance ce script.'
    exit 2
}
Log 'Aucun processus n''utilise .venv.'

# 2. Renommage
if ((Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath $src)) {
    Log 'Deja renomme (.venv.retired-0.20.5 existe). Etape verification seulement.'
} elseif (-not (Test-Path -LiteralPath $src)) {
    Log 'ABANDON : ni .venv ni .venv.retired-0.20.5 — rien a faire.'
    exit 3
} else {
    try {
        Rename-Item -LiteralPath $src -NewName '.venv.retired-0.20.5' -ErrorAction Stop
        Log 'RENOMMAGE OK : .venv -> .venv.retired-0.20.5'
    } catch {
        Log ('ECHEC DU RENOMMAGE : {0}' -f $_.Exception.Message)
        Log 'Un processus tient encore un fichier de .venv (ferme la session Hermes, ou redemarre).'
        exit 4
    }
}

# 3. Verifications
$py   = Join-Path $repo 'venv\Scripts\python.exe'
$shim = Join-Path $home_ 'bin\hermes.exe'

Log '--- venv rustine ---'
Log ('venv\Scripts\python.exe present : {0}' -f (Test-Path $py))

Log '--- hermes --version (via le PATH) ---'
& hermes --version 2>&1 | ForEach-Object { Log ('   ' + $_) }

Log '--- bin\hermes.exe --version (shim absolu) ---'
if (Test-Path $shim) { & $shim --version 2>&1 | ForEach-Object { Log ('   ' + $_) } } else { Log '   shim absent' }

Log '--- hermes doctor (extraits) ---'
& hermes doctor 2>&1 | Select-String -Pattern 'Version files consistent|Install directory|Required Packages|WARNING|ERROR' |
    ForEach-Object { Log ('   ' + $_.Line.Trim()) }

Log '--- hermes skills list ---'
$n = (& hermes skills list 2>&1 | Select-String -Pattern 'actif|active|^\s*[a-z0-9-]+\s' -AllMatches).Count
Log ('   lignes de skills list : {0}' -f $n)

Log '--- backend 9119 ---'
try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:9119/' -UseBasicParsing -TimeoutSec 8
    Log ('   HTTP {0}' -f $r.StatusCode)
} catch { Log ('   injoignable : ' + $_.Exception.Message) }

Log '=== termine. Rollback : Rename-Item .venv.retired-0.20.5 .venv ==='
Log 'Conservation conseillee 30 jours (jusqu''au ~2026-10-19) avant suppression.'
