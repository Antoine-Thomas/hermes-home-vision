<#
verify-copy-tree.ps1 -- verifie qu'une copie d'arborescence est fidele (phase B "deplacer vers <volume>")

Usage :
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File verify-copy-tree.ps1 -Src C:\c -Dst D:\backup_x
  ... -StripPrefix "Users\<user>\Desktop\<backup>\" -SampleCount 10 -MaxSampleMB 100 -BigCount 3

Entree : deux racines existantes. Sortie : compte et octets des deux cotes, diff d'ensembles sur la cle
"chemin relatif + taille" (attendu 0 et 0), SHA256 echantillonnes un par sous-arbre, controle partiel des
plus gros fichiers. Exit 0 = identique, 3 = ecart detecte.

- La cle inclut la TAILLE : un fichier tronque remonte comme ecart, pas seulement un fichier absent.
- -StripPrefix retire le prefixe commun avant de grouper, sinon une arborescence nestee sous un seul root
  ne produit qu'un groupe et l'echantillon ne couvre rien.
- SHA256 complet uniquement sous -MaxSampleMB ; au-dela, controle partiel (debut + fin 32 Mo) annonce
  comme partiel.
- Garder ce fichier en ASCII pur : PowerShell 5.1 lit l'UTF-8 sans BOM comme de l'ANSI.
#>
param(
    [Parameter(Mandatory = $true)][string]$Src,
    [Parameter(Mandatory = $true)][string]$Dst,
    [string]$StripPrefix = '',
    [int]$SampleCount = 10,
    [int]$MaxSampleMB = 100,
    [int]$BigCount = 3
)
$ErrorActionPreference = 'SilentlyContinue'

foreach ($r in @($Src, $Dst)) {
    if (-not (Test-Path -LiteralPath $r)) { Write-Output ("RACINE ABSENTE : " + $r); exit 2 }
}

function Dump-Tree([string]$root, [string]$out) {
    $sw = New-Object System.IO.StreamWriter($out, $false, (New-Object System.Text.UTF8Encoding($false)))
    $n = 0; $b = [int64]0
    foreach ($f in [System.IO.Directory]::EnumerateFiles($root, '*', [System.IO.SearchOption]::AllDirectories)) {
        try {
            $fi = New-Object System.IO.FileInfo $f
            $sw.WriteLine($f.Substring($root.Length + 1) + "`t" + $fi.Length)
            $n++; $b += $fi.Length
        } catch { }
    }
    $sw.Close()
    return [pscustomobject]@{ n = $n; b = $b }
}

function Get-PartialHash([string]$path, [int]$block = 33554432) {
    $fs = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    $buf = New-Object byte[] $block
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $n1 = $fs.Read($buf, 0, $block)
    $sha.TransformBlock($buf, 0, $n1, $buf, 0) | Out-Null
    $fs.Seek([Math]::Max(0, $fs.Length - $block), [System.IO.SeekOrigin]::Begin) | Out-Null
    $n2 = $fs.Read($buf, 0, $block)
    $sha.TransformFinalBlock($buf, 0, $n2) | Out-Null
    $h = [BitConverter]::ToString($sha.Hash).Replace('-', '')
    $fs.Close()
    return $h
}

$work = if ($env:TEMP) { $env:TEMP } else { '.' }
$srcList = Join-Path $work 'verify_src.tsv'
$dstList = Join-Path $work 'verify_dst.tsv'

$rs = Dump-Tree $Src $srcList
Write-Output ("SOURCE      : " + $rs.n + " fichiers | " + $rs.b + " octets")
$rd = Dump-Tree $Dst $dstList
Write-Output ("DESTINATION : " + $rd.n + " fichiers | " + $rd.b + " octets")
Write-Output ("ECART       : " + ($rd.n - $rs.n) + " fichiers | " + ($rd.b - $rs.b) + " octets")

$sl = [System.IO.File]::ReadAllLines($srcList)
$dl = [System.IO.File]::ReadAllLines($dstList)
$diff = Compare-Object -ReferenceObject $sl -DifferenceObject $dl
$onlySrc = @($diff | Where-Object { $_.SideIndicator -eq '<=' } | ForEach-Object { $_.InputObject })
$onlyDst = @($diff | Where-Object { $_.SideIndicator -eq '=>' } | ForEach-Object { $_.InputObject })
Write-Output ("ENSEMBLE    : uniq_source=" + $onlySrc.Count + " | uniq_dest=" + $onlyDst.Count)
$onlySrc | Select-Object -First 20 | ForEach-Object { Write-Output ("  ABSENT EN DEST : " + $_) }
$onlyDst | Select-Object -First 20 | ForEach-Object { Write-Output ("  EN PLUS EN DEST: " + $_) }

$all = New-Object System.Collections.ArrayList
$groups = @{}
foreach ($l in $sl) {
    $p = $l -split "`t"
    if ($p.Count -lt 2) { continue }
    $len = [int64]$p[1]
    [void]$all.Add([pscustomobject]@{ rel = $p[0]; len = $len })
    $r2 = if ($StripPrefix -ne '' -and $p[0].StartsWith($StripPrefix)) { $p[0].Substring($StripPrefix.Length) } else { $p[0] }
    $parts = $r2 -split '\\'
    $key = if ($parts.Count -ge 2) { ($parts[0..1] -join '\') } else { '(_racine)' }
    if (-not $groups.ContainsKey($key)) { $groups[$key] = @() }
    $groups[$key] += [pscustomobject]@{ rel = $p[0]; len = $len }
}

Get-Random -SetSeed 20260929 | Out-Null
$maxB = [int64]$MaxSampleMB * 1048576
Write-Output ("--- SHA256 ECHANTILLONNES (<= " + $MaxSampleMB + " Mo, 1 par sous-arbre) ---")
$ok = 0; $ko = 0
foreach ($g in ($groups.GetEnumerator() | Sort-Object -Property { ($_.Value | Measure-Object -Property len -Sum).Sum } -Descending | Select-Object -First $SampleCount)) {
    $cands = @($g.Value | Where-Object { $_.len -ge 1048576 -and $_.len -le $maxB })
    if ($cands.Count -eq 0) { continue }
    $c = $cands | Get-Random
    $hs = (Get-FileHash -LiteralPath (Join-Path $Src $c.rel) -Algorithm SHA256).Hash
    $hd = (Get-FileHash -LiteralPath (Join-Path $Dst $c.rel) -Algorithm SHA256).Hash
    if ($hs -eq $hd) { $ok++; $v = 'IDENTIQUE' } else { $ko++; $v = 'DIFFERENT' }
    Write-Output ([math]::Round($c.len / 1e6, 1).ToString() + " Mo | " + $g.Name + " | " + $hs.Substring(0, 16) + " | " + $v)
}
Write-Output ("ECHANTILLON : identiques=" + $ok + " differents=" + $ko)

if ($BigCount -gt 0) {
    Write-Output ("--- " + $BigCount + " PLUS GROS FICHIERS : controle PARTIEL (debut + fin 32 Mo, pas un SHA256) ---")
    foreach ($b in ($all | Sort-Object -Property len -Descending | Select-Object -First $BigCount)) {
        $hs = Get-PartialHash (Join-Path $Src $b.rel)
        $hd = Get-PartialHash (Join-Path $Dst $b.rel)
        $v = if ($hs -eq $hd) { 'IDENTIQUE' } else { 'DIFFERENT' }
        Write-Output ([math]::Round($b.len / 1e9, 2).ToString() + " Go | " + $b.rel + " | partiel " + $hs.Substring(0, 16) + " | " + $v)
    }
}

$faults = $onlySrc.Count + $onlyDst.Count + $ko + ($rd.n - $rs.n) + ($rd.b - $rs.b)
if ($faults -eq 0) { Write-Output 'VERDICT : COPIE FIDELE (0 ecart)'; exit 0 }
Write-Output ('VERDICT : ECART DETECTE -- ne pas supprimer la source'); exit 3
