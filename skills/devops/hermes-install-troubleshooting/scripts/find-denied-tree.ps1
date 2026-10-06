<#
  find-denied-tree.ps1 -- objets d'une arborescence qu'un jeton NON ELEVE ne peut pas lire.

  Pourquoi : une DACL PROTEGEE ne contenant que
  OWNER RIGHTS (S-1-3-4) + SYSTEM + Administrateurs ne donne AUCUN droit a l'utilisateur quand le
  proprietaire de l'objet est BUILTIN\Administrateurs -> WinError 5 a l'execution non elevee, alors
  que la meme commande elevee reussit (l'ACE OWNER RIGHTS profite au proprietaire de l'objet).

  Ne JAMAIS compter BUILTIN\Administrateurs (S-1-5-32-544) comme utilisable : dans un jeton filtre
  (non eleve) il est monte "refus uniquement".

  Usage:
    powershell -NoProfile -ExecutionPolicy Bypass -File find-denied-tree.ps1 -Root "C:\Users\x\AppData\Local\hermes"
    ... -Root <dir> -MaxDepth 3 -OutFile "$env:TEMP\denied.txt"

  Lecture : une ligne par objet 'DIR|FILE <chemin> DENI non-eleve owner=... protected=...',
  l'agregation par zone, et la ligne de controle TOTAL_ANOMALIES=N (0 = rien a reparer).
  Faux positif attendu : un fichier nomme 'nul' (artefact d'une redirection bash) rend "ACL ILLISIBLE".
#>
param(
  [Parameter(Mandatory = $true)][string]$Root,
  [int]$MaxDepth = 6,
  [string]$OutFile = '',
  [string[]]$Skip = @('cache','backups','data','.git','node_modules','.venv','venv','site-packages','__pycache__','logs')
)
$ErrorActionPreference = 'SilentlyContinue'
if (-not (Test-Path -LiteralPath $Root)) { Write-Output "RACINE INTROUVABLE: $Root"; exit 2 }

$uid = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$uSid = $uid.User.Value
$usableSids = @($uSid, 'S-1-5-32-545', 'S-1-1-0', 'S-1-5-11', 'S-1-5-4', 'S-1-2-1', 'S-1-5-32-546')
$lines = New-Object System.Collections.Generic.List[string]
$zones = @{}

function Test-Usable {
  param([System.IO.FileSystemInfo]$Item)
  $acl = $null
  try { $acl = Get-Acl -LiteralPath $Item.FullName } catch { return "ACL ILLISIBLE ($($_.Exception.Message))" }
  $usable = $false
  $hasOwnerRights = $false
  foreach ($ace in $acl.Access) {
    if ($ace.AccessControlType -ne 'Allow') { continue }
    $sid = ''
    try { $sid = $ace.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value } catch { $sid = '' }
    if ($sid -eq 'S-1-3-4') { $hasOwnerRights = $true; continue }
    if ($usableSids -contains $sid) { $usable = $true }
  }
  if ($hasOwnerRights -and ($acl.Owner -eq $uid.Name)) { $usable = $true }
  if ($usable) { return '' }
  return ("DENI non-eleve | owner={0} | protected={1}" -f $acl.Owner, $acl.AreAccessRulesProtected)
}

function Walk {
  param([string]$Dir, [int]$Depth)
  if ($Depth -gt $MaxDepth) { return }
  foreach ($it in (Get-ChildItem -LiteralPath $Dir -Force)) {
    if ($it.PSIsContainer -and ($Skip -contains $it.Name)) { continue }
    $why = Test-Usable -Item $it
    if ($why -ne '') {
      $kind = 'FILE'
      if ($it.PSIsContainer) { $kind = 'DIR' }
      $lines.Add(("{0}`t{1}`t{2}" -f $kind, $it.FullName, $why))
      $rel = $it.FullName.Substring($Root.Length).TrimStart('\')
      $parts = $rel.Split('\')
      $key = $parts[0]
      if ($parts.Length -gt 1) { $key = $parts[0] + '\' + $parts[1] }
      if (-not $zones.ContainsKey($key)) { $zones[$key] = 0 }
      $zones[$key] = $zones[$key] + 1
    }
    if ($it.PSIsContainer) { Walk -Dir $it.FullName -Depth ($Depth + 1) }
  }
}

Walk -Dir $Root -Depth 1

$out = New-Object System.Collections.Generic.List[string]
$out.Add("==== OBJETS SANS DROIT POUR UN JETON NON ELEVE (racine: $Root) ====")
foreach ($l in $lines) { $out.Add($l) }
$out.Add('')
$out.Add('==== AGREGATION PAR ZONE ====')
foreach ($k in ($zones.Keys | Sort-Object)) { $out.Add(("{0,6}  {1}" -f $zones[$k], $k)) }
$out.Add(("TOTAL_ANOMALIES={0}" -f $lines.Count))
foreach ($l in $out) { Write-Output $l }
if ($OutFile -ne '') { $out | Set-Content -LiteralPath $OutFile -Encoding UTF8 }
exit 0
