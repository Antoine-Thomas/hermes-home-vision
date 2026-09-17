# desactiver_a2a.ps1 - Desactive A2A proprement (retour au defaut fail-closed).
#
# Ce que fait le script, dans cet ordre :
#   1. sauvegarde de config.yaml (config.yaml.a2a-backup-<horodatage>)
#   2. hermes plugins disable a2a-platform
#   3. retrait de "- a2a" dans platform_toolsets.cli
#   4. hermes config unset platforms.a2a.enabled (retour au defaut : cle absente)
#   5. hermes config check
#   6. hermes gateway restart (+ profil watch s'il existe)
#   7. verification : plus rien en ecoute sur le port 9900
#
# Les jetons A2A_BEARER_TOKEN / A2A_PEER_TOKENS / A2A_HOST restent dans .env :
# ils sont inertes plugin desactive. Pour les retirer vraiment, editer
# %LOCALAPPDATA%\hermes\.env et supprimer ces lignes.
#
# Texte en ASCII pur (les accents cassent PowerShell 5.1 sans BOM).
#
# Modes :
#   -SelfTest    valide UNIQUEMENT l'insertion/retrait sur une COPIE de config.yaml
#   -Force       ne demande pas de confirmation
#   -SkipGateway ne redemarre pas les gateways
#   -ConfigPath  utilise un autre config.yaml (tests)

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SelfTest,
    [switch]$SkipGateway,
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"

$hermesDir = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "hermes" } else { Join-Path $env:USERPROFILE "AppData\Local\hermes" }
$profile2  = "watch"
if (-not $ConfigPath) { $ConfigPath = Join-Path $hermesDir "config.yaml" }

function Etape($n, $texte) { Write-Host ""; Write-Host (("[{0}] {1}") -f $n, $texte) -ForegroundColor Cyan }
function Ok($texte)        { Write-Host ("    OK   " + $texte) -ForegroundColor Green }
function Attention($texte) { Write-Host ("    ATTENTION " + $texte) -ForegroundColor Yellow }
function Fatal($texte)     { Write-Host ("    ECHEC " + $texte) -ForegroundColor Red; exit 1 }

function Edit-A2aToolset {
    param([string]$Path, [ValidateSet("add", "remove")][string]$Action = "remove")

    $texte = [System.IO.File]::ReadAllText($Path)
    $nl = if ($texte -match "`r`n") { "`r`n" } else { "`n" }
    $motif = "(?m)(?<tete>^platform_toolsets:[^\S\r\n]*\r?\n)(?: {2}(?!cli:)[^\r\n]*\r?\n)*(?<entete> {2}cli:\r?\n)(?<items>(?: {4}- [^\r\n]*\r?\n)+)"
    $m = [regex]::Match($texte, $motif)
    if (-not $m.Success) { throw ("bloc platform_toolsets.cli introuvable dans " + $Path) }

    $items = @($m.Groups["items"].Value -split "\r?\n" | Where-Object { $_ -match "^\s*- " })
    $indent = ($items[0] -replace "^(\s*).*$", '$1')
    $present = ($items | Where-Object { $_.Trim() -eq "- a2a" }).Count -gt 0

    if ($Action -eq "add" -and $present)  { return @{ Modifie = $false; Motif = "deja present" } }
    if ($Action -eq "remove" -and -not $present) { return @{ Modifie = $false; Motif = "deja absent" } }

    if ($Action -eq "add") {
        $nouvelles = @(); $insere = $false
        foreach ($l in $items) {
            $valeur = $l.Trim().Substring(2).Trim()
            if (-not $insere -and [string]::Compare($valeur, "a2a", [System.StringComparison]::OrdinalIgnoreCase) -gt 0) {
                $nouvelles += ($indent + "- a2a"); $insere = $true
            }
            $nouvelles += $l
        }
        if (-not $insere) { $nouvelles += ($indent + "- a2a") }
    } else {
        $nouvelles = @($items | Where-Object { $_.Trim() -ne "- a2a" })
    }

    $remplacement = $m.Groups["tete"].Value + $m.Groups["entete"].Value + ($nouvelles -join $nl) + $nl
    $nouveau = $texte.Substring(0, $m.Index) + $remplacement + $texte.Substring($m.Index + $m.Length)
    [System.IO.File]::WriteAllText($Path, $nouveau, (New-Object System.Text.UTF8Encoding($false)))
    return @{ Modifie = $true; Motif = ("{0} element(s) dans platform_toolsets.cli" -f $nouvelles.Count) }
}

if ($SelfTest) {
    Write-Host "== SelfTest : insertion/retrait YAML sur une copie, aucune desactivation =="
    $copie = Join-Path $env:TEMP ("a2a_selftest_off_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".yaml")
    Copy-Item $ConfigPath $copie -Force
    $r1 = Edit-A2aToolset -Path $copie -Action add
    Write-Host ("    add    : modifie={0} ({1})" -f $r1.Modifie, $r1.Motif)
    $r2 = Edit-A2aToolset -Path $copie -Action remove
    Write-Host ("    remove : modifie={0} ({1})" -f $r2.Modifie, $r2.Motif)
    $r3 = Edit-A2aToolset -Path $copie -Action remove
    Write-Host ("    remove x2 : modifie={0} ({1}) - idempotence" -f $r3.Modifie, $r3.Motif)
    $a = (Get-Content $ConfigPath -Raw) -replace "`r`n", "`n"
    $b = (Get-Content $copie -Raw) -replace "`r`n", "`n"
    Write-Host ("    copie identique a l'original apres add+remove : {0}" -f ($a -eq $b))
    $h1 = (Get-FileHash $ConfigPath -Algorithm MD5).Hash
    $h2 = (Get-FileHash $copie -Algorithm MD5).Hash
    Write-Host ("    md5 identiques (comparaison octet a octet) : {0}" -f ($h1 -eq $h2))
    if ($a -ne $b -or $h1 -ne $h2) { exit 1 }
    exit 0
}

Etape 0 "Prealable"
if (-not (Test-Path $ConfigPath)) { Fatal ("config.yaml introuvable : " + $ConfigPath) }
if (-not $Force) {
    $reponse = Read-Host "Desactiver A2A et redemarrer les gateways ? (oui/non)"
    if ($reponse -notmatch "^(o|oui|y|yes)$") { Write-Host "Abandon, rien modifie."; exit 0 }
}

Etape 1 "Sauvegarde de config.yaml"
$backup = Join-Path $hermesDir ("config.yaml.a2a-off-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
Copy-Item $ConfigPath $backup -Force
Ok ("sauvegarde : " + $backup)

Etape 2 "hermes plugins disable a2a-platform"
hermes plugins disable a2a-platform
if ($LASTEXITCODE -ne 0) { Fatal "hermes plugins disable a2a-platform a echoue" }
Ok "plugin a2a-platform desactive (verifier : hermes plugins list -> not enabled)"

Etape 3 "Retrait de '- a2a' de platform_toolsets.cli"
$r = Edit-A2aToolset -Path $ConfigPath -Action remove
if ($r.Modifie) { Ok ("platform_toolsets.cli mis a jour (" + $r.Motif + ")") } else { Ok ("rien a faire (" + $r.Motif + ")") }
$cli = hermes config get platform_toolsets.cli
if (($cli | Select-String -SimpleMatch "a2a") -ne $null) { Fatal "a2a encore present dans platform_toolsets.cli" }
Ok "verification hermes config get platform_toolsets.cli : plus d'a2a"

Etape 4 "Retrait de platforms.a2a.enabled"
hermes config unset platforms.a2a.enabled
if ($LASTEXITCODE -ne 0) { Attention "hermes config unset platforms.a2a.enabled a echoue : verifier a la main" }
Ok "plateforme entrante desactivee (verifier : hermes config get platforms)"

Etape 5 "hermes config check"
hermes config check
if ($LASTEXITCODE -ne 0) { Fatal "hermes config check a echoue" }
Ok "config valide"

Etape 6 "Redemarrage des gateways"
if ($SkipGateway) {
    Attention "-SkipGateway : redemarrage saute (le gateway en cours garde A2A en memoire)"
} else {
    hermes gateway restart
    Ok "gateway default redemarre"
    $statut = hermes gateway list 2>$null
    if (($statut | Select-String -SimpleMatch $profile2) -ne $null) {
        hermes -p $profile2 gateway restart
        Ok ("gateway du profil " + $profile2 + " redemarre")
    } else {
        Attention ("profil " + $profile2 + " absent : rien a redemarrer")
    }
    Start-Sleep -Seconds 8
}

Etape 7 "Verification du port 9900 (attendu : plus rien)"
$ecoute = (cmd /c "netstat -ano | findstr :9900") 2>$null
if ($ecoute) {
    Attention "le port 9900 ecoute encore : verifier 'hermes gateway status' et logs/gateway.log"
    $ecoute | ForEach-Object { Write-Host ("    " + $_) }
    exit 1
}
Ok "plus rien en ecoute sur 9900"
Write-Host ""
Write-Host "A2A est revenu au defaut fail-closed. Retour arriere si besoin :"
Write-Host ("    Copy-Item '{0}' '{1}' -Force" -f $backup, $ConfigPath)
