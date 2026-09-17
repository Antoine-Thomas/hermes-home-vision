#=============================================================================
# Hermes Purge Reports - Scheduled cleanup script
# Deployed: C:\ProgramData\Hermes\purge_reports.ps1
# Schedule: Daily 02:00 via Hermes-PurgeReports task
#
# Historique:
#   2026-07-19  version initiale (DryRun par defaut)
#   2026-09-17  correctifs:
#               1) garde-fou alertes : extrait le premier entier de la chaine au
#                  lieu d'une egalite stricte. '0 alertes (index neuf)' n'est pas
#                  egal a '0 alertes' -> la purge etait bloquee a vie, en silence
#                  (la tache sortait en code 1 tous les jours depuis le 19/07).
#               2) preuves d'audit exclues de la purge (ni deplacees ni
#                  supprimees) par une liste explicite $ProtectedPatterns.
#=============================================================================
param(
    [int]$RetentionDays = 30,
    [string]$BasePath = "C:\ProgramData\Hermes",
    [string]$CsvPath = "$BasePath\scan_results.csv",
    [switch]$DryRun = $true
)

$ErrorActionPreference = "Stop"
$logFile = "$BasePath\logs\purge_$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

# Fichiers JAMAIS purges. Regle declarative : elle vaut pour toute archive future
# qui porterait ces motifs, pas seulement pour le fichier connu aujourd'hui.
$ProtectedPatterns = @('*hermes_evidence*', 'archive_sha256*')

function Write-Log {
    param([string]$Msg)
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts | $Msg" | Out-File $logFile -Append -Encoding utf8
    Write-Host "$ts | $Msg"
}

function Test-Protected {
    param([string]$Name)
    foreach ($p in $ProtectedPatterns) { if ($Name -like $p) { return $true } }
    return $false
}

Write-Log "=== Hermes Purge Reports - DryRun=$DryRun ==="
Write-Log "Protection preuves d'audit : $($ProtectedPatterns -join ', ')"

# 1. SAFETY CHECK: Read CSV and verify no critical actions pending
$safeToPurge = $true
if (Test-Path $CsvPath) {
    $csv = Import-Csv $CsvPath
    foreach ($row in $csv) {
        $actions = $row.action_taken -split ';'
        foreach ($act in $actions) {
            $act = $act.Trim()
            if ($act -in @('isolate-host','forensics-image','revoke-keys','rotate-passwords')) {
                Write-Log "BLOCKED: action '$act' found for host $($row.host) - refusing to purge"
                $safeToPurge = $false
            }
        }
        # Le champ est du texte libre ("0 alertes (index neuf)"). On extrait le premier
        # entier de la chaine ; toute valeur > 0 bloque la purge.
        $alerts = 0
        if ("$($row.alerts_wazuh_recentes)" -match '^\s*(\d+)') { $alerts = [int]$Matches[1] }
        if ($alerts -gt 0) {
            Write-Log "BLOCKED: $alerts alerte(s) Wazuh recente(s) pour $($row.host) - refusing to purge"
            $safeToPurge = $false
        }
    }
} else {
    Write-Log "WARNING: CSV not found at $CsvPath - skipping safety check"
}

if (-not $safeToPurge) {
    Write-Log "PURGE ABORTED: critical actions or alerts pending"
    exit 1
}

# 2. Find archives older than RetentionDays
$cutoff = (Get-Date).AddDays(-$RetentionDays)
$archivesDir = "$BasePath\archives"
$quarantineDir = "$BasePath\quarantine"

if (Test-Path $archivesDir) {
    $candidates = @(Get-ChildItem $archivesDir -File | Where-Object { $_.LastWriteTime -lt $cutoff })

    $protectedItems = @($candidates | Where-Object { Test-Protected $_.Name })
    foreach ($p in $protectedItems) {
        Write-Log "PROTECTED: $($p.Name) - preuve d'audit, ni deplacee ni supprimee"
    }

    $oldArchives = @($candidates | Where-Object { -not (Test-Protected $_.Name) })

    foreach ($archive in $oldArchives) {
        $quarantinePath = Join-Path $quarantineDir $archive.Name
        Write-Log "QUARANTINE: $($archive.Name) (age: $((Get-Date) - $archive.LastWriteTime).Days days)"

        if (-not $DryRun) {
            Move-Item $archive.FullName $quarantinePath -Force
            Write-Log "  -> Moved to $quarantinePath"
        }
    }

    # 3. Delete quarantined items older than 24h in quarantine
    $quarantineCutoff = (Get-Date).AddHours(-24)
    $staleQuarantine = @(Get-ChildItem $quarantineDir -File -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $quarantineCutoff -and -not (Test-Protected $_.Name) })

    foreach ($item in $staleQuarantine) {
        Write-Log "DELETE: $($item.Name) (quarantined >24h)"
        if (-not $DryRun) {
            Remove-Item $item.FullName -Force
        }
    }

    Write-Log "SUMMARY: $($oldArchives.Count) archives to quarantine, $($staleQuarantine.Count) to delete, $($protectedItems.Count) protected"
} else {
    Write-Log "No archives directory found"
}

Write-Log "=== Purge complete ==="
