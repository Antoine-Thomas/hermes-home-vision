<#
bootstrap.ps1 - Restaure l'installation Hermes decrite par ce depot sur une machine vierge.

PRINCIPE
  - DryRun par defaut : RIEN n'est ecrit, tout est affiche. Ajouter -Apply pour executer.
  - Idempotent : chaque etape commence par lire l'etat existant et ne fait rien si c'est deja en place.
  - Ne supprime jamais rien, n'ecrase jamais un .env existant, ne touche aucune donnee utilisateur.
  - Journal : docs\snapshot\bootstrap_<horodatage>.log (ajoute au .gitignore de docs/).

ORDRE DES ETAPES
  1. prerequis (git, reseau)          5. taches planifiees (14 recreables, 6 hors depot)
  2. Hermes Agent (installeur)        6. services (SiYuan -> OmniRoute -> NIM -> RAG -> backend -> gateways)
  3. configuration du depot           7. verification (ports, profils, doctor)
  4. .env depuis les .env.example     8. resume et liste des actions manuelles

CE QUE CE SCRIPT NE PEUT PAS FAIRE (a la main, voir docs\scripts\restore-from-github.md)
  creer les bots Telegram, generer la cle OmniRoute, creer le jeton SiYuan, installer SiYuan,
  restaurer data\ (venvs, modeles, index RAG) ni les fichiers de C:\ProgramData\Hermes.

Exemples
  .\bootstrap.ps1 -RepoUrl https://github.com/<user>/hermes-home-vision.git
  .\bootstrap.ps1 -RepoUrl https://github.com/<user>/hermes-home-vision.git -Apply
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$RepoUrl,
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA 'hermes'),
    [string]$Branch = 'main',
    [switch]$Apply,
    [switch]$SkipHermesInstall,
    [switch]$SkipTasks,
    [switch]$SkipServices,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$mode = if ($Apply) { 'APPLY' } else { 'DRYRUN' }
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$script:Journal = @()
$script:Echecs = 0

function Ligne($niveau, $texte) {
    $couleur = switch ($niveau) { 'OK' { 'Green' } 'ATTENTION' { 'Yellow' } 'ECHEC' { 'Red' } 'ACTION' { 'Cyan' } default { 'Gray' } }
    Write-Host ("  [{0,-9}] {1}" -f $niveau, $texte) -ForegroundColor $couleur
    $script:Journal += ("[{0}] {1}" -f $niveau, $texte)
    if ($niveau -eq 'ECHEC') { $script:Echecs++ }
}
function Etape($n, $t) { Write-Host ""; Write-Host ("== " + $n + ". " + $t) -ForegroundColor Magenta; $script:Journal += ("" ); $script:Journal += ("== " + $n + ". " + $t) }
function Faire($description, [scriptblock]$action) {
    if ($Apply) {
        Ligne 'ACTION' $description
        try { & $action } catch { Ligne 'ECHEC' ($description + ' -> ' + $_.Exception.Message) }
    } else {
        Ligne 'ATTENTION' ('[dryrun] ' + $description)
    }
}
function Test-Port([int]$port, [int]$timeoutSecondes = 3) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $t = $c.BeginConnect('127.0.0.1', $port, $null, $null)
        $ok = $t.AsyncWaitHandle.WaitOne($timeoutSecondes * 1000)
        $c.Close()
        return $ok
    } catch { return $false }
}
function Attendre-Port([int]$port, [int]$maxSecondes = 60, [string]$quoi = '') {
    for ($i = 0; $i -lt $maxSecondes; $i += 3) {
        if (Test-Port $port) { return $true }
        Start-Sleep -Seconds 3
    }
    return $false
}
function GitExe {
    $g = Get-Command git -ErrorAction SilentlyContinue
    if ($g) { return $g.Source }
    $local = Join-Path $InstallDir 'git\cmd\git.exe'
    if (Test-Path $local) { return $local }
    return $null
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host (" bootstrap Hermes - mode " + $mode) -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Ligne 'INFO' ("depot cible   : " + $RepoUrl)
Ligne 'INFO' ("installation  : " + $InstallDir + "  (branche " + $Branch + ")")
if (-not $Apply) { Ligne 'INFO' 'aucune ecriture : relancer avec -Apply pour executer' }

# ------------------------------------------------------------------ 1. prerequis
Etape 1 'Prerequis'
Ligne 'OK' ("PowerShell " + $PSVersionTable.PSVersion.ToString())
$git = GitExe
if ($git) { Ligne 'OK' ("git : " + $git) } else { Ligne 'ATTENTION' 'git absent : l''installeur Hermes en fournit un (MinGit) - etape 2' }
function Test-Sortant([string]$hote = 'github.com', [int]$port = 443, [int]$timeoutSecondes = 4) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $t = $c.BeginConnect($hote, $port, $null, $null)
        $ok = $t.AsyncWaitHandle.WaitOne($timeoutSecondes * 1000)
        $c.Close()
        return $ok
    } catch { return $false }
}
if (Test-Sortant) { Ligne 'OK' 'reseau sortant joignable (github.com:443)' } else { Ligne 'ATTENTION' 'github.com:443 injoignable : le clone et l''installeur echoueront' }

# ------------------------------------------------------------------ 2. Hermes Agent
Etape 2 'Hermes Agent'
$agentDir = Join-Path $InstallDir 'hermes-agent'
if (Test-Path $agentDir) {
    Ligne 'OK' ('deja installe : ' + $agentDir + ' (etape sautee)')
} elseif ($SkipHermesInstall) {
    Ligne 'ATTENTION' '-SkipHermesInstall : installation laissee de cote (le reste du script suppose Hermes present)'
} else {
    Ligne 'ATTENTION' 'Hermes absent : installation par l''installeur officiel (uv, Python 3.11, Node, MinGit)'
    Faire 'iex (irm https://hermes-agent.nousresearch.com/install.ps1)' { iex (irm https://hermes-agent.nousresearch.com/install.ps1) }
}

# ------------------------------------------------------------------ 3. configuration du depot
Etape 3 'Configuration du depot'
if (-not $git -and -not (Test-Path $configPath)) {
    Ligne 'ECHEC' 'git introuvable et configuration absente : installer Hermes (etape 2) ou git avant de continuer'
}
$configPath = Join-Path $InstallDir 'config.yaml'
if (Test-Path $configPath) {
    if ($Force) {
        Ligne 'ATTENTION' ('config.yaml deja present : -Force demande, la copie de reference va etre reecrite (sauvegarde creee avant)')
        Faire ('sauvegarde + mise en place de la reference git') {
            Copy-Item $configPath ($configPath + '.avant-bootstrap-' + $ts) -Force
            & $git -C $InstallDir checkout -f $Branch -- config.yaml
        }
    } else {
        Ligne 'OK' 'config.yaml deja present : etape sautee (utiliser -Force pour reprendre la reference du depot)'
    }
} else {
    $gapres = 0
    if (Test-Path $InstallDir) { $gapres = @(Get-ChildItem -Force $InstallDir -ErrorAction SilentlyContinue).Count }
    if ($gapres -gt 0 -and -not (Test-Path (Join-Path $InstallDir '.git'))) {
        Ligne 'INFO' ($gapres.ToString() + ' entree(s) deja presentes : pose par git init + fetch + checkout, sans rien supprimer')
        Faire ('git init -b ' + $Branch) { & $git -C $InstallDir init -b $Branch }
        Faire ('git remote add origin ' + $RepoUrl) {
            & $git -C $InstallDir remote add origin $RepoUrl
            if ($LASTEXITCODE -ne 0) { & $git -C $InstallDir remote set-url origin $RepoUrl }
        }
        Faire ('git fetch --depth 1 origin ' + $Branch) { & $git -C $InstallDir fetch --depth 1 origin $Branch }
        Faire ('git checkout -f -b ' + $Branch + ' origin/' + $Branch) { & $git -C $InstallDir checkout -f -b $Branch ("origin/" + $Branch) }
    } elseif (Test-Path (Join-Path $InstallDir '.git')) {
        Ligne 'OK' 'depot git deja en place : ' + $InstallDir
        Faire 'git fetch + git checkout -f de la branche de reference' {
            & $git -C $InstallDir fetch --depth 1 origin $Branch
            & $git -C $InstallDir checkout -f $Branch
        }
    } else {
        Ligne 'ATTENTION' 'dossier vide : clonage direct possible'
        Faire ('git clone --depth 1 -b ' + $Branch + ' ' + $RepoUrl + ' ' + $InstallDir) {
            & $git clone --depth 1 -b $Branch $RepoUrl $InstallDir
        }
    }
}

# ------------------------------------------------------------------ 4. .env
Etape 4 'Fichiers .env (modeles, jamais de valeur)'
$envPairs = @(
    @{ Modele = (Join-Path $InstallDir '.env.example');                    Cible = (Join-Path $InstallDir '.env') },
    @{ Modele = (Join-Path $InstallDir 'profiles\watch\.env.example');     Cible = (Join-Path $InstallDir 'profiles\watch\.env') },
    @{ Modele = (Join-Path $InstallDir 'profiles\veille\.env.example');    Cible = (Join-Path $InstallDir 'profiles\veille\.env') }
)
$aRemplir = @()
foreach ($p in $envPairs) {
    if (Test-Path $p.Cible) {
        Ligne 'OK' (($p.Cible -replace [regex]::Escape($InstallDir), '.') + ' deja present : conserve')
    } elseif (Test-Path $p.Modele) {
        Faire ('copie ' + ($p.Modele -replace [regex]::Escape($InstallDir), '.') + ' -> ' + ($p.Cible -replace [regex]::Escape($InstallDir), '.')) {
            Copy-Item $p.Modele $p.Cible -Force
        }
    } else {
        Ligne 'ATTENTION' ('modele absent : ' + $p.Modele + ' (le depot est-il completement pose ?)')
    }
    if (Test-Path $p.Cible) {
        foreach ($l in (Get-Content $p.Cible -Encoding UTF8)) {
            if ($l -match '^\s*([A-Z][A-Z0-9_]*)\s*=\s*$') { $aRemplir += ($Matches[1] + '  (' + ($p.Cible -replace [regex]::Escape($InstallDir), '.') + ')') }
        }
    }
}
$optionnelles = @('WHATSAPP_CLOUD_PHONE_NUMBER_ID','WHATSAPP_CLOUD_ACCESS_TOKEN','WHATSAPP_MODE','WHATSAPP_ALLOWED_USERS','BROWSERBASE_PROXIES','BROWSERBASE_ADVANCED_STEALTH','WEB_TOOLS_DEBUG','VISION_TOOLS_DEBUG','MOA_TOOLS_DEBUG','IMAGE_TOOLS_DEBUG','TERMINAL_MODAL_IMAGE','EMAIL_POLL_INTERVAL')
$aRemplirCritiques = @($aRemplir | Where-Object { ($_ -split ' ')[0] -notin $optionnelles })
$aListerOptionnelles = @($aRemplir | Where-Object { ($_ -split ' ')[0] -in $optionnelles })
if ($aRemplirCritiques.Count -gt 0) {
    Ligne 'ATTENTION' ($aRemplirCritiques.Count.ToString() + ' variable(s) INDISPENSABLE(S) a remplir a la main :')
    $aRemplirCritiques | ForEach-Object { Write-Host ('        ! ' + $_) }
} else {
    Ligne 'OK' 'aucune variable indispensable vide'
}
if ($aListerOptionnelles.Count -gt 0) {
    Ligne 'INFO' ($aListerOptionnelles.Count.ToString() + ' variable(s) optionnelle(s) vide(s) (WhatsApp, debug, navigateur) : sans consequence si les services ne sont pas utilises')
}

# ------------------------------------------------------------------ 5. taches planifiees
Etape 5 'Taches planifiees'
$scriptTaches = Join-Path $InstallDir 'scripts'
# (a) taches dont le depot fournit le generateur : deleguees a ces scripts, source de verite
if ($SkipTasks) {
    Ligne 'ATTENTION' '-SkipTasks : etape sautee'
} else {
    $generateurs = @(
        @{ Nom = 'Hermes_Gateway';        Cmd = "$scriptTaches\creer_tache_gateway.ps1"; Arg = @('-TaskName', 'Hermes_Gateway', '-Apply') },
        @{ Nom = 'Hermes_Gateway_watch';  Cmd = "$scriptTaches\creer_tache_gateway.ps1"; Arg = @('-TaskName', 'Hermes_Gateway_watch', '-Apply') },
        @{ Nom = 'Hermes_Gateway_veille'; Cmd = "$scriptTaches\creer_tache_gateway.ps1"; Arg = @('-TaskName', 'Hermes_Gateway_veille', '-Apply') },
        @{ Nom = 'Hermes_Gateway_HealthCheck'; Cmd = "$scriptTaches\check_gateways.ps1"; Arg = @('-InstallTask', '-Apply') }
    )
    foreach ($g in $generateurs) {
        $existe = Get-ScheduledTask -TaskName $g.Nom -ErrorAction SilentlyContinue
        if ($existe) { Ligne 'OK' ($g.Nom + ' : deja presente') ; continue }
        if (Test-Path $g.Cmd) {
            Faire ('creer ' + $g.Nom + ' via ' + (Split-Path $g.Cmd -Leaf)) { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $g.Cmd @($g.Arg) }
        } else {
            Ligne 'ECHEC' ($g.Nom + ' : generateur absent (' + $g.Cmd + ')')
        }
    }

    # (b) taches recreables directement : action pointee sur un fichier VERSIONNE du depot
    $recreables = @(
        @{ Nom = 'Hermes - serve backend';        Exe = 'wscript.exe'; Arg = ('//B //Nologo "' + $InstallDir + '\gateway-service\Hermes_Serve.vbs"'); Fichier = "$InstallDir\gateway-service\Hermes_Serve.vbs"; Type = 'Logon' },
        @{ Nom = 'Hermes - check memory';         Exe = 'powershell.exe'; Arg = ('-NoProfile -ExecutionPolicy Bypass -File "' + $InstallDir + '\scripts\check_memory.ps1"'); Fichier = "$InstallDir\scripts\check_memory.ps1"; Type = 'Daily'; Heure = '08:00' },
        @{ Nom = 'Hermes - desaturer memoire';    Exe = 'python.exe'; Arg = ('"' + $InstallDir + '\scripts\desaturer_memoire.py" --auto'); Fichier = "$InstallDir\scripts\desaturer_memoire.py"; Type = 'Weekly'; Heure = '04:00' },
        @{ Nom = 'SecurityMonitoring-AlertBridge';   Exe = 'wscript.exe'; Arg = ('//B "' + $InstallDir + '\scripts\hidden_SecurityMonitoring-AlertBridge.vbs"');   Fichier = "$InstallDir\scripts\hidden_SecurityMonitoring-AlertBridge.vbs";   Type = 'Repete'; Intervalle = 'PT5M' },
        @{ Nom = 'SecurityMonitoring-LogMonitor';    Exe = 'wscript.exe'; Arg = ('//B "' + $InstallDir + '\scripts\hidden_SecurityMonitoring-LogMonitor.vbs"');    Fichier = "$InstallDir\scripts\hidden_SecurityMonitoring-LogMonitor.vbs";    Type = 'Repete'; Intervalle = 'PT2M' },
        @{ Nom = 'SecurityMonitoring-PortMonitor';   Exe = 'wscript.exe'; Arg = ('//B "' + $InstallDir + '\scripts\hidden_SecurityMonitoring-PortMonitor.vbs"');   Fichier = "$InstallDir\scripts\hidden_SecurityMonitoring-PortMonitor.vbs";   Type = 'Repete'; Intervalle = 'PT10M' },
        @{ Nom = 'SecurityMonitoring-UpdateChecker'; Exe = 'wscript.exe'; Arg = ('//B "' + $InstallDir + '\scripts\hidden_SecurityMonitoring-UpdateChecker.vbs"'); Fichier = "$InstallDir\scripts\hidden_SecurityMonitoring-UpdateChecker.vbs"; Type = 'Daily'; Heure = '09:00' },
        @{ Nom = 'OmniRouteServer';        Exe = 'wscript.exe'; Arg = ('//B "' + $InstallDir + '\omniroute-launch.vbs"'); Fichier = "$InstallDir\omniroute-launch.vbs"; Type = 'Repete'; Intervalle = 'PT15M' },
        @{ Nom = 'OmniRoute-AutoLaunch';   Exe = 'wscript.exe'; Arg = ('//B "' + $InstallDir + '\omniroute-launch.vbs"'); Fichier = "$InstallDir\omniroute-launch.vbs"; Type = 'Logon' },
        @{ Nom = 'OmniRoute-Watchdog';     Exe = 'wscript.exe'; Arg = ('//B "' + $InstallDir + '\omniroute-launch.vbs"'); Fichier = "$InstallDir\omniroute-launch.vbs"; Type = 'Repete'; Intervalle = 'PT5M' }
    )
    foreach ($t in $recreables) {
        if (Get-ScheduledTask -TaskName $t.Nom -ErrorAction SilentlyContinue) { Ligne 'OK' ($t.Nom + ' : deja presente') ; continue }
        if (-not (Test-Path $t.Fichier)) { Ligne 'ECHEC' ($t.Nom + ' : fichier cible absent du depot (' + $t.Fichier + ')') ; continue }
        Faire ('creer ' + $t.Nom + ' (' + $t.Type + ')') {
            $action = New-ScheduledTaskAction -Execute $t.Exe -Argument $t.Arg
            if ($t.Type -eq 'Daily') {
                $trigger = New-ScheduledTaskTrigger -Daily -At $t.Heure
            } elseif ($t.Type -eq 'Weekly') {
                $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At $t.Heure
            } elseif ($t.Type -eq 'Repete') {
                $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes ([int]($t.Intervalle -replace 'PT|M', '')))
            } else {
                $trigger = New-ScheduledTaskTrigger -AtLogOn
            }
            $set = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable
            Register-ScheduledTask -TaskName $t.Nom -Action $action -Trigger $trigger -Settings $set -Force | Out-Null
        }
    }

    # (c) taches dont le fichier cible n'est PAS dans le depot : a recreer a la main
    Write-Host ""
    Ligne 'ATTENTION' 'taches NON recreables automatiquement (fichier cible hors depot) :'
    $horsDepot = @(
        @{ Nom = 'Hermes - Reindex RAG';      Cible = "$InstallDir\data\rag\reindex_auto.py";                        Note = 'data/ n''est pas versionne (index, venvs)' },
        @{ Nom = 'Hermes_NVIDIA_NIM_Proxy';   Cible = "$InstallDir\data\nvidia\nvidia-nim-launch.vbs";              Note = 'data/ n''est pas versionne' },
        @{ Nom = 'SiYuan - noyau second cerveau'; Cible = (Join-Path $env:USERPROFILE 'SiYuan\demarrer_siyuan_silencieux.vbs'); Note = 'application externe' },
        @{ Nom = 'Hermes-PurgeReports';       Cible = 'C:\ProgramData\Hermes\purge_reports.ps1';                    Note = 'hors du home Hermes' },
        @{ Nom = 'AudioGuardian-Watchdog';    Cible = "$InstallDir\data\surveillance\audio_guardian\guardian-watchdog.vbs"; Note = 'data/ n''est pas versionne' },
        @{ Nom = 'cua-driver-serve';          Cible = (Join-Path $env:LOCALAPPDATA 'Programs\Cua\cua-driver\bin\cua-driver.exe'); Note = 'logiciel tiers' }
    )
    foreach ($h in $horsDepot) {
        $present = Test-Path $h.Cible
        Write-Host ("        - " + $h.Nom + "  [" + $(if ($present) { 'cible presente' } else { 'cible ABSENTE' }) + "]")
        Write-Host ("            attendu : " + $h.Cible + "  (" + $h.Note + ")")
    }
    Write-Host ""
    Ligne 'INFO' 'vestige HermesGateway (desactive sur la machine d''origine) : volontairement NON recree'
}

# ------------------------------------------------------------------ 6. services
Etape 6 'Services (ordre : SiYuan, OmniRoute, NIM, RAG, backend, gateways)'
if ($SkipServices) {
    Ligne 'ATTENTION' '-SkipServices : etape sautee'
} else {
    $svc = @(
        @{ Nom = 'SiYuan';     Port = 6806;  Tache = 'SiYuan - noyau second cerveau';  Note = 'application externe' },
        @{ Nom = 'OmniRoute';  Port = 20128; Tache = 'OmniRouteServer';                Note = 'routeur LLM' },
        @{ Nom = 'Proxy NIM';  Port = 20200; Tache = 'Hermes_NVIDIA_NIM_Proxy';        Note = 'proxy local' },
        @{ Nom = 'Backend';    Port = 9119;  Tache = 'Hermes - serve backend';         Note = 'API Hermes' }
    )
    foreach ($s in $svc) {
        if (Test-Port $s.Port 2) { Ligne 'OK' ($s.Nom + ' deja en ecoute sur ' + $s.Port) ; continue }
        $tache = Get-ScheduledTask -TaskName $s.Tache -ErrorAction SilentlyContinue
        if ($tache) {
            Faire ('demarrer ' + $s.Nom + ' via la tache ' + $s.Tache) { Start-ScheduledTask -TaskName $s.Tache }
            if ($Apply) {
                if (Attendre-Port $s.Port 90) { Ligne 'OK' ($s.Nom + ' en ecoute sur ' + $s.Port) }
                else { Ligne 'ATTENTION' ($s.Nom + ' toujours muet sur ' + $s.Port + ' (lire son journal)') }
            }
        } else {
            Ligne 'ATTENTION' ($s.Nom + ' : tache absente, demarrage manuel requis (' + $s.Note + ')')
        }
    }
    # RAG : aucun lanceur n'existe dans le parc (cf. ARCHITECTURE_HERMES.md SS7.9)
    if (Test-Port 8200 2) {
        Ligne 'OK' 'RAG deja en ecoute sur 8200'
    } else {
        $ragScript = Join-Path $InstallDir 'data\rag\serveur_rag.py'
        if (Test-Path $ragScript) {
            Faire 'demarrer le serveur RAG (aucune tache ne le gere dans le parc)' {
                Start-Process -FilePath 'python.exe' -ArgumentList ('"' + $ragScript + '"') -WorkingDirectory (Split-Path $ragScript) -WindowStyle Hidden
            }
            if ($Apply) {
                if (Attendre-Port 8200 60) { Ligne 'OK' 'RAG en ecoute sur 8200' } else { Ligne 'ATTENTION' 'RAG muet sur 8200' }
            }
        } else {
            Ligne 'ATTENTION' ('RAG : ' + $ragScript + ' absent (data/ non versionne) - a restaurer a la main')
        }
    }
    foreach ($gw in @('Hermes_Gateway', 'Hermes_Gateway_watch', 'Hermes_Gateway_veille')) {
        $tache = Get-ScheduledTask -TaskName $gw -ErrorAction SilentlyContinue
        if ($tache) { Faire ('demarrer le gateway ' + $gw) { Start-ScheduledTask -TaskName $gw } }
        else { Ligne 'ATTENTION' ($gw + ' : tache absente (etape 5)') }
    }
}

# ------------------------------------------------------------------ 7. verification
Etape 7 'Verification'
$hermes = 'hermes'
$portsOk = 0
foreach ($p in @(6806, 8200, 9119, 20128, 20200)) {
    if (Test-Port $p 2) { Ligne 'OK' ('port ' + $p + ' en ecoute') ; $portsOk++ } else { Ligne 'ATTENTION' ('port ' + $p + ' muet') }
}
Ligne 'INFO' ($portsOk.ToString() + '/5 services en ecoute')
if ($Apply) {
    try { & $hermes profile list } catch { Ligne 'ATTENTION' 'hermes profile list indisponible' }
    try { & $hermes doctor } catch { Ligne 'ATTENTION' 'hermes doctor indisponible' }
    $verif = Join-Path $InstallDir 'scripts\verif_24h.ps1'
    $baseline = Join-Path $InstallDir 'docs\snapshot\baseline_T0.json'
    if ((Test-Path $verif) -and (Test-Path $baseline)) {
        Ligne 'INFO' 'verif_24h.ps1 contre la baseline T0 du depot (a regenerer si la machine differe)'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verif
    } elseif (Test-Path $verif) {
        Ligne 'ATTENTION' ('baseline absente (' + $baseline + ') : regenerer avec docs\scripts\baseline_t0.py')
    }
} else {
    Ligne 'ATTENTION' '[dryrun] verification des profils, de doctor et de verif_24h.ps1 non executee'
}

# ------------------------------------------------------------------ 8. resume
Etape 8 'Resume'
Write-Host ""
Write-Host ("  mode : " + $mode + "   echecs : " + $script:Echecs) -ForegroundColor $(if ($script:Echecs -eq 0) { 'Green' } else { 'Red' })
Write-Host ""
Write-Host '  A FAIRE A LA MAIN (le script ne peut pas les creer) :'
Write-Host '    1. bots Telegram : un bot par profil (BotFather), jeton dans chaque .env'
Write-Host '    2. cle OmniRoute : /api/keys du dashboard, une cle par profil (watch, veille) + la cle du poste'
Write-Host '    3. jeton SiYuan : Reglages -> A propos -> API token, dans .env et profiles\veille\.env'
Write-Host '    4. installer SiYuan (application externe) et ses 6 notebooks'
Write-Host '    5. restaurer data\ : venvs, modeles, index RAG (non versionne)'
Write-Host '    6. recreer les taches hors depot (liste ci-dessus, etape 5c)'
Write-Host '    7. nouvelles cles par machine : ne jamais reutiliser celles de la machine d''origine'
Write-Host ""
Write-Host '  Detail de la procedure : docs\scripts\restore-from-github.md'
Write-Host ''

if ($Apply) {
    $logDir = Join-Path $InstallDir 'docs\snapshot'
    if (Test-Path $logDir) {
        $logPath = Join-Path $logDir ('bootstrap_' + $ts + '.log')
        $script:Journal | Set-Content -Path $logPath -Encoding UTF8
        Write-Host ('  journal : ' + $logPath) -ForegroundColor Gray
    }
}
if ($script:Echecs -gt 0) { exit 1 }
exit 0
