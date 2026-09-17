# activer_a2a.ps1 - Active A2A (Agent-to-Agent) cote Hermes.
#
# A EXECUTER UNIQUEMENT le jour ou un 2e agent Hermes est operationnel et joignable :
# sans pair, activer A2A ouvre un port d'ecoute pour rien (fail-closed par defaut,
# mais un service qui ecoute est un service qu'il faut surveiller).
#
# Ce que fait le script, dans cet ordre :
#   1. sauvegarde de config.yaml (config.yaml.a2a-backup-<horodatage>)
#   2. hermes plugins enable a2a-platform
#   3. ajout de "- a2a" dans platform_toolsets.cli (insertion textuelle ciblee ;
#      NE PAS utiliser « hermes config set platform_toolsets.cli a2a », qui remplace
#      toute la liste par un scalaire, ni un aller-retour YAML complet, qui reformate
#      tout le fichier)
#   4. hermes config set platforms.a2a.enabled true (cle RACINE : c'est celle que lit
#      le gate des outils A2A ; « gateway.platforms.a2a » n'est pas lue)
#   5. hermes config check
#   6. hermes gateway restart (+ profil watch s'il existe)
#   7. verification du port 9900 en ecoute sur 127.0.0.1
#   8. rappel des 5 outils A2A exposes
#
# Securite : sans A2A_BEARER_TOKEN ni A2A_PEER_TOKENS, le serveur reste lie a
# 127.0.0.1 (aucun acces distant). Pour exposer A2A a un pair distant il faut un
# jeton ET A2A_HOST=0.0.0.0 : le script ne fait jamais ce dernier pas a ta place,
# il te dit quoi poser dans %LOCALAPPDATA%\hermes\.env.
#
# Texte en ASCII pur (les accents cassent PowerShell 5.1 sans BOM).
#
# Modes :
#   -SelfTest   valide UNIQUEMENT l'insertion YAML sur une COPIE de config.yaml
#               (n'active rien, ne touche ni aux plugins ni aux gateways)
#   -Force      ne demande pas de confirmation (presence du 2e agent)
#   -SkipGateway ne redemarre pas les gateways (apres un test de config)
#   -ConfigPath utilise un autre config.yaml (tests)

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$SelfTest,
    [switch]$SkipGateway,
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"

$hermesDir = if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "hermes" } else { Join-Path $env:USERPROFILE "AppData\Local\hermes" }
$envFile   = Join-Path $hermesDir ".env"
$profile2  = "watch"    # 2e profil Hermes a redemarrer s'il existe
if (-not $ConfigPath) { $ConfigPath = Join-Path $hermesDir "config.yaml" }

function Etape($n, $texte) { Write-Host ""; Write-Host (("[{0}] {1}") -f $n, $texte) -ForegroundColor Cyan }
function Ok($texte)        { Write-Host ("    OK   " + $texte) -ForegroundColor Green }
function Attention($texte) { Write-Host ("    ATTENTION " + $texte) -ForegroundColor Yellow }
function Fatal($texte)     { Write-Host ("    ECHEC " + $texte) -ForegroundColor Red; exit 1 }

# --- insertion / retrait de "- a2a" dans platform_toolsets.cli --------------
# Insertion textuelle ciblee : on ne reformate rien d'autre que ce bloc.
function Edit-A2aToolset {
    param([string]$Path, [ValidateSet("add", "remove")][string]$Action = "add")

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

# --- auto-test : insertion/retrait sur une COPIE ----------------------------
if ($SelfTest) {
    Write-Host "== SelfTest : insertion YAML sur une copie, aucune activation =="
    $copie = Join-Path $env:TEMP ("a2a_selftest_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".yaml")
    Copy-Item $ConfigPath $copie -Force
    $r1 = Edit-A2aToolset -Path $copie -Action add
    Write-Host ("    add    : modifie={0} ({1})" -f $r1.Modifie, $r1.Motif)
    $r2 = Edit-A2aToolset -Path $copie -Action add
    Write-Host ("    add x2 : modifie={0} ({1}) - idempotence" -f $r2.Modifie, $r2.Motif)
    $r3 = Edit-A2aToolset -Path $copie -Action remove
    Write-Host ("    remove : modifie={0} ({1})" -f $r3.Modifie, $r3.Motif)
    $a = (Get-Content $ConfigPath -Raw) -replace "`r`n", "`n"
    $b = (Get-Content $copie -Raw) -replace "`r`n", "`n"
    Write-Host ("    copie identique a l'original apres add+remove : {0}" -f ($a -eq $b))
    $h1 = (Get-FileHash $ConfigPath -Algorithm MD5).Hash
    $h2 = (Get-FileHash $copie -Algorithm MD5).Hash
    Write-Host ("    md5 identiques (comparaison octet a octet) : {0}" -f ($h1 -eq $h2))
    Write-Host ("    copie conservee pour inspection : " + $copie)
    if ($a -ne $b -or $h1 -ne $h2) { exit 1 }
    exit 0
}

# --- etat des lieux --------------------------------------------------------
Etape 0 "Prealable"
if (-not (Test-Path $ConfigPath)) { Fatal ("config.yaml introuvable : " + $ConfigPath) }
Ok ("config : " + $ConfigPath)

$jeton = $false
if (Test-Path $envFile) {
    $contenuEnv = Get-Content $envFile -Raw
    $jeton = ($contenuEnv -match "A2A_BEARER_TOKEN=\S") -or ($contenuEnv -match "A2A_PEER_TOKENS=\S")
}
if (-not $jeton) {
    Attention "aucun A2A_BEARER_TOKEN / A2A_PEER_TOKENS dans .env : le serveur restera lie a 127.0.0.1 (aucun pair distant possible)."
    Attention "pour autoriser un pair distant : poser un jeton dans .env ET A2A_HOST=0.0.0.0 (jamais fait par ce script)."
} else {
    Ok "jeton A2A present dans .env (acces distant possible si A2A_HOST est renseigne)"
}

$enEcoute = (cmd /c "netstat -ano | findstr :9900") 2>$null
if ($enEcoute) { Attention "le port 9900 est deja en ecoute : A2A est peut-etre deja actif." }

if (-not $Force) {
    $reponse = Read-Host "Un 2e agent Hermes est-il operationnel et joignable ? (oui/non)"
    if ($reponse -notmatch "^(o|oui|y|yes)$") { Write-Host "Abandon : sans 2e agent, A2A n'apporte rien."; exit 0 }
}

# --- 1. sauvegarde ---------------------------------------------------------
Etape 1 "Sauvegarde de config.yaml"
$backup = Join-Path $hermesDir ("config.yaml.a2a-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
Copy-Item $ConfigPath $backup -Force
Ok ("sauvegarde : " + $backup)

# --- 2. plugin -------------------------------------------------------------
Etape 2 "hermes plugins enable a2a-platform"
hermes plugins enable a2a-platform
if ($LASTEXITCODE -ne 0) { Fatal "hermes plugins enable a2a-platform a echoue" }
Ok "plugin a2a-platform active (verifier : hermes plugins list)"

# --- 3. toolset ------------------------------------------------------------
Etape 3 "Ajout de '- a2a' dans platform_toolsets.cli"
$r = Edit-A2aToolset -Path $ConfigPath -Action add
if ($r.Modifie) { Ok ("platform_toolsets.cli mis a jour (" + $r.Motif + ")") } else { Ok ("rien a faire (" + $r.Motif + ")") }
$cli = hermes config get platform_toolsets.cli
if (($cli | Select-String -SimpleMatch "a2a") -eq $null) { Fatal "a2a absent de platform_toolsets.cli apres modification" }
Ok "verification hermes config get platform_toolsets.cli : a2a present"

# --- 4. plateforme entrante ------------------------------------------------
Etape 4 "Activation de la plateforme entrante (platforms.a2a.enabled)"
hermes config set platforms.a2a.enabled true
if ($LASTEXITCODE -ne 0) { Fatal "hermes config set platforms.a2a.enabled true a echoue" }
$actif = hermes config get platforms.a2a.enabled
if (($actif | Select-String -SimpleMatch "true") -eq $null) { Fatal "platforms.a2a.enabled n'est pas true" }
Ok "platforms.a2a.enabled = true (cle racine ; 'gateway.platforms.a2a.enabled' n'est pas la cle lue par les outils A2A)"

# --- 5. config check -------------------------------------------------------
Etape 5 "hermes config check"
hermes config check
if ($LASTEXITCODE -ne 0) { Fatal "hermes config check a echoue" }
Ok "config valide"

# --- 6. gateways -----------------------------------------------------------
Etape 6 "Redemarrage des gateways"
if ($SkipGateway) {
    Attention "-SkipGateway : redemarrage saute (A2A ne sera pas charge par le gateway en cours)"
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

# --- 7. port --------------------------------------------------------------
Etape 7 "Verification du port 9900 (attendu : 127.0.0.1 uniquement sans jeton)"
$ecoute = (cmd /c "netstat -ano | findstr :9900") 2>$null
if ($ecoute) { $ecoute | ForEach-Object { Write-Host ("    " + $_) } } else { Attention "rien en ecoute sur 9900 : relancer 'hermes gateway status' et lire logs/gateway.log" }

# --- 8. outils A2A --------------------------------------------------------
Etape 8 "Les 5 outils A2A exposes (outbound)"
foreach ($outil in @(
    "a2a_discover(url)                          - lire l'Agent Card d'un pair",
    "a2a_call(agent, message, context_id?)      - envoyer une tache a un pair",
    "a2a_list()                                 - pairs configures, conversations, metriques",
    "a2a_history(context_id)                    - relire une conversation A2A",
    "a2a_orchestrate(capability, message, mode?) - diffuser a tous les pairs (all/first/best)")) {
    Write-Host ("    " + $outil)
}
Write-Host ""
Write-Host "Rappels : pairs a declarer sous 'a2a_agents:' dans config.yaml (url + auth bearer)."
Write-Host "          Agent Card servi sur http://127.0.0.1:9900/.well-known/agent-card.json"
Write-Host "          Audit : hermes\a2a_audit.jsonl | Desactivation : scripts\desactiver_a2a.ps1"
Write-Host ("          Retour arriere : Copy-Item '{0}' '{1}' -Force" -f $backup, $ConfigPath)
