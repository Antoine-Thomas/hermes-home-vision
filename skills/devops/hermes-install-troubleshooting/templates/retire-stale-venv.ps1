# retire-stale-venv.ps1 — put a superseded virtualenv out of service, reversibly.
#
# COPY AND ADAPT: set $Home_, $Repo and $VenvName. Nothing else needs editing.
#
# Why a script and not an inline rename: Windows refuses to rename a directory while any
# process holds files inside it (IOException / "access is denied"), and the agent's own
# session is usually one of those processes. So the agent repoints the launchers, then
# hands this to the user to run from a PLAIN PowerShell with every Hermes session closed.
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File <path>\retire-stale-venv.ps1
# Rollback: Rename-Item "<repo>\.venv.retired-<ver>" ".venv"

param(
    [string]$Home_    = (Join-Path $env:LOCALAPPDATA 'hermes'),
    [string]$Repo     = '',
    [string]$VenvName = '.venv',
    [string]$Retired  = '',
    [switch]$SkipVerify
)

$ErrorActionPreference = 'Continue'
if (-not $Repo)    { $Repo = Join-Path $Home_ 'hermes-agent' }
if (-not $Retired) { $Retired = $VenvName + '.retired' }
$src  = Join-Path $Repo $VenvName
$dst  = Join-Path $Repo $Retired
$logf = Join-Path $Home_ 'docs\retire-stale-venv.log'

function Log([string]$m) {
    $line = ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m)
    Write-Output $line
    if (Test-Path (Split-Path $logf)) { Add-Content -LiteralPath $logf -Value $line -Encoding UTF8 }
}

Log ('=== retrait de {0} ===' -f $src)

# 1. Refuse to touch it while anything has it open. -like is case-insensitive; the
#    trailing path separator keeps a sibling like '.venv.old' from matching '.venv'.
$needle = $VenvName.TrimEnd('\') + '\\'
$users  = Get-CimInstance Win32_Process |
          Where-Object { $_.Name -ne 'powershell.exe' -and $_.CommandLine -and $_.CommandLine -like ('*' + $needle + '*') }
if ($users) {
    Log ('ABANDON : {0} processus utilisent encore {1}' -f @($users).Count, $VenvName)
    foreach ($p in $users) { Log ('   PID {0} {1} << {2}' -f $p.ProcessId, $p.Name, ($p.CommandLine -replace '\s+',' ')) }
    Log 'Ferme la session Hermes concernee, puis relance.'
    exit 2
}
Log 'Aucun processus ne l''utilise.'

# 2. Reversible rename
if ((Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath $src)) {
    Log 'Deja renomme — verification seulement.'
} elseif (-not (Test-Path -LiteralPath $src)) {
    Log ('ABANDON : ni {0} ni {1} — rien a faire.' -f $VenvName, $Retired)
    exit 3
} else {
    try {
        Rename-Item -LiteralPath $src -NewName $Retired -ErrorAction Stop
        Log ('RENOMMAGE OK : {0} -> {1}' -f $VenvName, $Retired)
    } catch {
        Log ('ECHEC DU RENOMMAGE : {0}' -f $_.Exception.Message)
        Log 'Un processus tient encore un fichier dedans (ferme la session, ou redemarre).'
        exit 4
    }
}

# 3. Prove the surviving install still works
if (-not $SkipVerify) {
    $py   = Join-Path $Repo 'venv\Scripts\python.exe'
    $shim = Join-Path $Home_ 'bin\hermes.exe'
    Log ('venv\Scripts\python.exe present : {0}' -f (Test-Path $py))
    Log '--- hermes --version (PATH) ---'
    & hermes --version 2>&1 | ForEach-Object { Log ('   ' + $_) }
    Log '--- bin\hermes.exe --version (absolute shim) ---'
    if (Test-Path $shim) { & $shim --version 2>&1 | ForEach-Object { Log ('   ' + $_) } } else { Log '   shim absent' }
    Log '--- hermes doctor (extraits) ---'
    & hermes doctor 2>&1 | Select-String -Pattern 'Version files consistent|Install directory|Required Packages|WARNING|ERROR' |
        ForEach-Object { Log ('   ' + $_.Line.Trim()) }
    Log '--- hermes skills list ---'
    & hermes skills list 2>&1 | ForEach-Object { Log ('   ' + $_) }
}

Log ('=== termine. Rollback : Rename-Item "{0}" "{1}" ===' -f $dst, $VenvName)
Log 'Conserver ~30 jours avant suppression.'
