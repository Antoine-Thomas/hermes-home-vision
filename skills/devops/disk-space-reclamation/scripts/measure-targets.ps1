<#
measure-targets.ps1 -- taille + mtime d'une liste de cibles, rapide (.NET)

Pourquoi : du -sb / du -sm (MSYS) ne rend pas la main en 420 s sur des cibles de
plusieurs Go (17 Go, 68 Go mesurees). L'enumeration .NET boucle sur les fichiers
et rend la meme mesure en minutes.

Usage :
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File measure-targets.ps1 -List C:/chemin/cibles.txt
  ... -List cibles.txt -Sort name|size|mtime

Entree : un chemin par ligne (fichier ou dossier). Lignes vides et lignes #ignorees.
Sortie : TSV  kind <TAB> bytes <TAB> mtime <TAB> path   + ligne TOTAL
         kind = FILE | DIR | MISSING   (tri par defaut : taille decroissante)

Notes :
- bytes = taille LOGIQUE (somme des Length des fichiers), pas les blocs alloues :
  comparable entre Windows et Linux. Convention rapport : 1 Go = 10^9 octets.
- mtime d'un dossier = derniere modification de son repertoire (signal d'activite),
  pas le max des enfants. Confirmer avec le mtime des sous-dossiers avant de
  conclure qu'une cible est morte.
- Une cible absente sort en MISSING : ne jamais sauter la ligne, sinon l'absence
  passe pour une absence d'information.
- Garder ce fichier en ASCII pur : PowerShell 5.1 lit l'UTF-8 sans BOM comme de l'ANSI.
#>
param(
    [Parameter(Mandatory = $true)][string]$List,
    [ValidateSet('size', 'name', 'mtime')][string]$Sort = 'size'
)
$ErrorActionPreference = 'SilentlyContinue'

function Get-DirBytes([string]$root) {
    $sum = [int64]0
    foreach ($f in [System.IO.Directory]::EnumerateFiles($root, '*', [System.IO.SearchOption]::AllDirectories)) {
        try { $sum += (New-Object System.IO.FileInfo $f).Length } catch { }
    }
    return $sum
}

if (-not (Test-Path -LiteralPath $List)) {
    Write-Error "liste introuvable : $List"
    exit 2
}

$rows = @()
foreach ($raw in [System.IO.File]::ReadAllLines($List)) {
    $p = $raw.Trim()
    if ($p -eq '' -or $p.StartsWith('#')) { continue }

    if (-not (Test-Path -LiteralPath $p)) {
        $rows += [pscustomobject]@{ kind = 'MISSING'; bytes = [int64]0; mtime = ''; path = $p }
        continue
    }

    $it = Get-Item -LiteralPath $p -Force
    if ($it.PSIsContainer) {
        $rows += [pscustomobject]@{ kind = 'DIR'; bytes = (Get-DirBytes $p); mtime = $it.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'); path = $p }
    }
    else {
        $rows += [pscustomobject]@{ kind = 'FILE'; bytes = $it.Length; mtime = $it.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'); path = $p }
    }
}

switch ($Sort) {
    'size'  { $rows = $rows | Sort-Object -Property bytes -Descending }
    'mtime' { $rows = $rows | Sort-Object -Property mtime -Descending }
    'name'  { $rows = $rows | Sort-Object -Property path }
}

$tot = [int64]0
foreach ($r in $rows) {
    $tot += $r.bytes
    "{0}`t{1}`t{2}`t{3}" -f $r.kind, $r.bytes, $r.mtime, $r.path
}
"TOTAL`t{0}`t`t{1} cibles" -f $tot, @($rows).Count
