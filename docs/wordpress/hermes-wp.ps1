<#
    hermes-wp.ps1 - enveloppe lisible autour de WP-CLI pour les sites WordPress locaux.

    Utilisation :
        hermes-wp info                 version de WordPress, URL, theme, nombre d'extensions
        hermes-wp plugins              extensions actives + mises a jour disponibles
        hermes-wp backup               export de la base dans hermes-backups/
        hermes-wp deploy               deploiement : verifie les prerequis (aucune action destructive)
        hermes-wp <commande wp>        tout le reste passe tel quel a wp.bat
        hermes-wp aide                 cette aide

    Detection du site : le dossier courant, puis chaque dossier parent, jusqu'a trouver
    wp-config.php (racine WordPress classique) ou app\public\wp-config.php (Local by Flywheel).
    La commande est ensuite lancee depuis ce dossier.

    Le chemin de WP-CLI est ABSOLU (C:\wp-cli\wp.bat) : un fichier vide nomme `wp` dans
    C:\Windows\System32 masque le wp.bat du PATH, ce raccourci n'en depend donc pas.

    Aucune commande destructive n'est lancee sans --oui : backup ecrit un fichier, deploy ne fait
    que verifier et afficher.

    STATUT : prepare, a tester quand un site Local existera (aucun site present le 15/09/2026).
#>
[CmdletBinding()]
param(
    [switch]$NoColor,
    [switch]$Oui,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$WP = 'C:\wp-cli\wp.bat'
$Couleur = -not $NoColor -and -not $env:NO_COLOR

function Dire($texte, $couleur = 'Gray') {
    if ($Couleur) { Write-Host $texte -ForegroundColor $couleur } else { Write-Host $texte }
}

function Titre($texte) { Dire ''; Dire ('=== ' + $texte) 'Cyan' }

function Trouver-Site {
    $d = (Get-Location).Path
    while ($d) {
        if (Test-Path (Join-Path $d 'wp-config.php')) { return $d }
        $local = Join-Path $d 'app\public'
        if (Test-Path (Join-Path $local 'wp-config.php')) { return $local }
        $parent = Split-Path $d -Parent
        if (-not $parent -or $parent -eq $d) { return $null }
        $d = $parent
    }
    return $null
}

function Nom-Site($chemin) {
    # Local range les sites dans <racine>\<nom-du-site>\app\public : on remonte pour le nom
    $p = $chemin
    if ($p -match '\\app\\public$') { $p = Split-Path (Split-Path $p -Parent) -Parent }
    return Split-Path $p -Leaf
}

function Lancer-Wp($dossier, [string[]]$commande) {
    Push-Location $dossier
    try {
        & $WP @commande 2>&1 | ForEach-Object { $_ }
        return $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

function Aide {
    Titre 'hermes-wp - raccourcis'
    @'
  hermes-wp info        version, URL, theme, extensions actives, taille de la base
  hermes-wp plugins     extensions installees, actives, et mises a jour disponibles
  hermes-wp backup      export SQL dans <site>\hermes-backups\ (fichiers : voir le skill)
  hermes-wp deploy      verifie les prerequis de deploiement (n'agit pas)
  hermes-wp <commande>  toute commande WP-CLI : hermes-wp plugin list --status=active

  Options : -NoColor (sortie sans couleur) | -Oui (autoriser une action qui ecrit)
'@ | Write-Host
    Titre 'Detection'
    $s = Trouver-Site
    if ($s) {
        Dire ("  site courant : " + (Nom-Site $s)) 'Green'
        Dire ("  dossier      : " + $s) 'DarkGray'
    } else {
        Dire '  aucun site detecte depuis ce dossier' 'Yellow'
        Dire '  (lancer depuis la racine du site, ou depuis app\public)' 'DarkGray'
    }
}

if (-not (Test-Path $WP)) {
    Dire ("WP-CLI introuvable : " + $WP) 'Red'
    exit 1
}

if (-not $Args -or $Args.Count -eq 0) { Aide; exit 0 }

$commande = $Args[0].ToLower()
$reste = @()
if ($Args.Count -gt 1) { $reste = $Args[1..($Args.Count - 1)] }

switch ($commande) {
    { $_ -in 'aide', 'help', '-h', '--help', '-aide' } { Aide; exit 0 }
}

$site = Trouver-Site

if (-not $site) {
    Dire 'Aucun site WordPress detecte depuis ce dossier.' 'Yellow'
    Dire 'Se placer dans la racine du site (celle qui contient wp-config.php) puis relancer.' 'DarkGray'
    if ($commande -in 'info', 'plugins', 'backup', 'deploy') { exit 2 }
}

switch ($commande) {
    'info' {
        Titre ('Site : ' + (Nom-Site $site))
        Dire ("  dossier      : " + $site) 'DarkGray'
        $version = Lancer-Wp $site @('core', 'version')
        Dire ("  WordPress    : " + ($version | Select-Object -Last 1)) 'White'
        $url = Lancer-Wp $site @('option', 'get', 'siteurl')
        Dire ("  URL          : " + ($url | Select-Object -Last 1)) 'White'
        $theme = Lancer-Wp $site @('theme', 'list', '--status=active', '--field=name')
        Dire ("  theme actif  : " + ($theme | Select-Object -Last 1)) 'White'
        $actifs = Lancer-Wp $site @('plugin', 'list', '--status=active', '--format=count')
        $total = Lancer-Wp $site @('plugin', 'list', '--format=count')
        Dire ("  extensions   : " + ($actifs | Select-Object -Last 1) + " actives sur " + ($total | Select-Object -Last 1)) 'White'
        $taille = Lancer-Wp $site @('db', 'size', '--format=mb')
        Dire ("  base         : " + ($taille | Select-Object -Last 1) + " Mo") 'White'
        $php = Lancer-Wp $site @('eval', 'echo PHP_VERSION;')
        Dire ("  PHP          : " + ($php | Select-Object -Last 1)) 'White'
        exit 0
    }
    'plugins' {
        Titre ('Extensions - ' + (Nom-Site $site))
        Lancer-Wp $site @('plugin', 'list', '--fields=name,status,version,update,auto_update') | Out-Null
        Titre 'Mises a jour disponibles'
        Lancer-Wp $site @('plugin', 'list', '--update=available', '--fields=name,version,update_version')
        exit 0
    }
    'backup' {
        Titre ('Sauvegarde de la base - ' + (Nom-Site $site))
        $dossier = Join-Path $site 'hermes-backups'
        if (-not (Test-Path $dossier)) { New-Item -ItemType Directory -Path $dossier | Out-Null }
        $fichier = Join-Path $dossier ('base-' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.sql')
        if (-not $Oui) {
            Dire ("  ecrirait : " + $fichier) 'Yellow'
            Dire '  relancer avec -Oui pour executer (aucun fichier ecrit pour l''instant)' 'DarkGray'
            exit 0
        }
        Lancer-Wp $site @('db', 'export', $fichier) | Out-Null
        if (Test-Path $fichier) {
            $mo = [math]::Round((Get-Item $fichier).Length / 1MB, 1)
            Dire ("  export ecrit : " + $fichier + " (" + $mo + " Mo)") 'Green'
        } else {
            Dire '  echec de l''export' 'Red'
        }
        Dire '  les FICHIERS ne sont pas sauvegardes : voir le skill wordpress-backup-restore' 'DarkGray'
        exit 0
    }
    'deploy' {
        Titre 'Deploiement - verification des prerequis'
        Dire ("  site source : " + (Nom-Site $site) + "  (" + $site + ")") 'White'
        $ok = $true
        foreach ($outil in 'ssh', 'rsync') {
            $present = Get-Command $outil -ErrorAction SilentlyContinue
            if ($present) { Dire ("  " + $outil.PadRight(6) + " : present") 'Green' }
            else { Dire ("  " + $outil.PadRight(6) + " : absent") 'Yellow'; $ok = $false }
        }
        $config = Join-Path (Split-Path $WP -Parent) 'hermes-wp-sites.json'
        if (Test-Path $config) { Dire ("  cibles     : " + $config) 'Green' }
        else {
            Dire '  cibles     : aucune cible declaree' 'Yellow'
            Dire ("    creer " + $config + ' avec, par exemple :') 'DarkGray'
            Dire '    { "mon-site": { "hote": "user@srv", "chemin": "/var/www/site" } }' 'DarkGray'
            $ok = $false
        }
        Dire '  aucune action effectuee : le deploiement reel passe par le skill wordpress-deployment' 'DarkGray'
        if (-not $ok) { exit 3 }
        exit 0
    }
    default {
        Lancer-Wp $site @Args | Out-Null
        exit $LASTEXITCODE
    }
}
