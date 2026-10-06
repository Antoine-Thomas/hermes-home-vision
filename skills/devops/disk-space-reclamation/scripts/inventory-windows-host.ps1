# inventory-windows-host.ps1 - inventaire LECTURE SEULE d'un hote Windows avant un nettoyage.
# Mesure: volumes (octets exacts), tailles des cibles, top processus (WS + prive), cumul par famille,
#         RAM/CIM (standby inclus), VRAM nvidia-smi, age des fichiers dans les Temp.
# Ne supprime RIEN et n'ecrit que dans -Out. Chaque lot part dans un fichier TSV/TXT relu ensuite.
#
# Usage:
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File inventory-windows-host.ps1
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File inventory-windows-host.ps1 -Out C:/tmp/inv -TargetsFile C:/tmp/cibles.txt
#
# -TargetsFile: un chemin par ligne (les lignes vides et commencant par # sont ignorees).

param(
  [string]$Out = (Join-Path $env:TEMP 'hermes_host_inventory'),
  [string]$TargetsFile = ''
)
$ErrorActionPreference = 'Continue'
if (-not (Test-Path -LiteralPath $Out)) { New-Item -ItemType Directory -Path $Out -Force | Out-Null }

function W($name, $lines) { $lines | Out-File -LiteralPath (Join-Path $Out $name) -Encoding utf8 }

$defaultTargets = @(
  'C:\Windows\Temp',
  (Join-Path $env:LOCALAPPDATA 'Temp'),
  'C:\Windows\SoftwareDistribution\Download',
  'C:\Windows\Prefetch',
  'C:\Windows\Logs',
  'C:\Windows\LiveKernelReports',
  'C:\ProgramData\Microsoft\Windows\WER',
  (Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\INetCache'),
  (Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Explorer'),
  (Join-Path $env:LOCALAPPDATA 'CrashDumps'),
  'C:\$Recycle.Bin',
  'D:\$RECYCLE.BIN'
)
$targets = $defaultTargets
if ($TargetsFile -ne '' -and (Test-Path -LiteralPath $TargetsFile)) {
  $targets = @(Get-Content -LiteralPath $TargetsFile | Where-Object { $_.Trim() -ne '' -and -not $_.Trim().StartsWith('#') })
}

# --- lot 0 : contexte ---
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
W 'lot0_contexte.txt' @(
  "date_local=$((Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'))",
  "host=$env:COMPUTERNAME user=$env:USERNAME",
  "elevated=$isAdmin  (une cible systeme se mesure/lit sans elevation, mais se nettoie eleve)",
  "powershell=$($PSVersionTable.PSVersion.ToString())"
)

# --- lot 1 : volumes, octets exacts (df -h arrondit au GiB) ---
$lines = @('FORMAT: Drive | Label | FS | Size_bytes | Free_bytes | Free_pct')
foreach ($d in (Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 3 } | Sort-Object DeviceID)) {
  $pct = if ($d.Size -gt 0) { [math]::Round(100 * $d.FreeSpace / $d.Size, 2) } else { 0 }
  $lines += ('{0} | {1} | {2} | {3} | {4} | {5}%' -f $d.DeviceID, $d.VolumeName, $d.FileSystem, $d.Size, $d.FreeSpace, $pct)
}
W 'lot1_volumes.txt' $lines

# --- lot 2 : tailles des cibles (une ligne MISSING, jamais une ligne sautee) ---
$rows = @('FORMAT: path | kind | bytes | files | dirs | access_errors | mtime_dir | mtime_max_child')
foreach ($t in $targets) {
  if (-not (Test-Path -LiteralPath $t)) { $rows += ('{0} | MISSING | 0 | 0 | 0 | 0 | - | -' -f $t); continue }
  $item = Get-Item -LiteralPath $t -Force
  if (-not $item.PSIsContainer) {
    $rows += ('{0} | FILE | {1} | 1 | 0 | 0 | {2} | {2}' -f $t, $item.Length, $item.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')); continue
  }
  $errs = @()
  $files = Get-ChildItem -LiteralPath $t -Recurse -Force -File -ErrorAction SilentlyContinue -ErrorVariable +errs
  $dirs = Get-ChildItem -LiteralPath $t -Recurse -Force -Directory -ErrorAction SilentlyContinue -ErrorVariable +errs
  $sum = 0; $maxT = $null
  foreach ($f in $files) { $sum += $f.Length; if ($maxT -eq $null -or $f.LastWriteTime -gt $maxT) { $maxT = $f.LastWriteTime } }
  $mt = if ($maxT) { $maxT.ToString('yyyy-MM-dd HH:mm:ss') } else { '-' }
  $rows += ('{0} | DIR | {1} | {2} | {3} | {4} | {5} | {6}' -f $t, $sum, $files.Count, $dirs.Count, $errs.Count, $item.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'), $mt)
}
W 'lot2_cibles.tsv' $rows

# --- lot 3 : age des fichiers dans les Temp (plafond reellement supprimable) ---
$rows = @('FORMAT: cible | fichiers | bytes | >7j_fichiers | >7j_bytes | >30j_fichiers | >30j_bytes | plus_ancien | plus_recent')
foreach ($t in $targets) {
  if (-not (Test-Path -LiteralPath $t)) { continue }
  $it = Get-Item -LiteralPath $t -Force
  if (-not $it.PSIsContainer) { continue }
  $files = Get-ChildItem -LiteralPath $t -Recurse -Force -File -ErrorAction SilentlyContinue
  $d7 = (Get-Date).AddDays(-7); $d30 = (Get-Date).AddDays(-30)
  $f7 = @($files | Where-Object { $_.LastWriteTime -lt $d7 }); $f30 = @($files | Where-Object { $_.LastWriteTime -lt $d30 })
  $s7 = ($f7 | Measure-Object Length -Sum).Sum; if (-not $s7) { $s7 = 0 }
  $s30 = ($f30 | Measure-Object Length -Sum).Sum; if (-not $s30) { $s30 = 0 }
  $old = ($files | Measure-Object -Property LastWriteTime -Minimum).Minimum
  $new = ($files | Measure-Object -Property LastWriteTime -Maximum).Maximum
  $rows += ('{0} | {1} | {2} | {3} | {4} | {5} | {6} | {7} | {8}' -f $t, $files.Count, (($files | Measure-Object Length -Sum).Sum),
    $f7.Count, $s7, $f30.Count, $s30, $(if ($old) { $old.ToString('yyyy-MM-dd') } else { '-' }), $(if ($new) { $new.ToString('yyyy-MM-dd HH:mm') } else { '-' }))
}
W 'lot3_age_cibles.tsv' $rows

# --- lot 4 : top 10 par WS ET par memoire privee (les deux, sinon le plus gros consommateur echappe) ---
$rows = @('FORMAT: rang | name | pid | WS_MB | Private_MB | CPU_s | start | path')
$r = 0
foreach ($p in (Get-Process -ErrorAction SilentlyContinue | Sort-Object WS -Descending | Select-Object -First 10)) {
  $r++
  $st = try { $p.StartTime.ToString('yyyy-MM-dd HH:mm:ss') } catch { 'n/a' }
  $pa = try { $p.Path } catch { 'n/a' }
  $cpu = if ($p.CPU) { [math]::Round($p.CPU, 1) } else { 0 }
  $rows += ('{0} | {1} | {2} | {3} | {4} | {5} | {6} | {7}' -f $r, $p.ProcessName, $p.Id, [math]::Round($p.WS / 1MB, 1), [math]::Round($p.PrivateMemorySize64 / 1MB, 1), $cpu, $st, $pa)
}
W 'lot4_top10_ws.tsv' $rows

$rows = @('FORMAT: rang | name | pid | Private_MB | WS_MB | handles | threads')
$r = 0
foreach ($p in (Get-Process -ErrorAction SilentlyContinue | Sort-Object PrivateMemorySize64 -Descending | Select-Object -First 10)) {
  $r++
  $rows += ('{0} | {1} | {2} | {3} | {4} | {5} | {6}' -f $r, $p.ProcessName, $p.Id, [math]::Round($p.PrivateMemorySize64 / 1MB, 1), [math]::Round($p.WS / 1MB, 1), $p.HandleCount, $p.Threads.Count)
}
W 'lot4_top10_prive.tsv' $rows

# --- lot 5 : cumul par famille. Lecture SEULE du nom de processus: jamais CommandLine (elle porte des
# secrets, et un filtrage par sous-chaine y ramene des faux positifs du type 'rag' dans 'storage').
$all = Get-CimInstance Win32_Process | Select-Object Name, ProcessId, WorkingSetSize, ExecutablePath
$rows = @('FORMAT: famille | procs | WS_total_MB | WS_max_MB | exemple_de_chemin')
foreach ($g in ($all | Group-Object Name | Sort-Object { -($_.Group | Measure-Object WorkingSetSize -Sum).Sum })) {
  $s = ($g.Group | Measure-Object WorkingSetSize -Sum).Sum
  if ($s -lt 200MB) { continue }
  $mx = ($g.Group | Measure-Object WorkingSetSize -Maximum).Maximum
  $ex = ($g.Group | Where-Object { $_.ExecutablePath } | Select-Object -First 1).ExecutablePath
  $rows += ('{0} | {1} | {2} | {3} | {4}' -f $g.Name, $g.Count, [math]::Round($s / 1MB, 1), [math]::Round($mx / 1MB, 1), $ex)
}
W 'lot5_familles.tsv' $rows

# --- lot 6 : RAM via CIM (noms de proprietes stables; Get-Counter renvoie des noms LOCALISES) ---
$os = Get-CimInstance Win32_OperatingSystem
$lines = @(
  ('TotalVisible_KB={0} FreePhysical_KB={1}' -f $os.TotalVisibleMemorySize, $os.FreePhysicalMemory),
  ('TotalVisible_GB={0} FreePhysical_GB={1}' -f [math]::Round($os.TotalVisibleMemorySize / 1MB, 2), [math]::Round($os.FreePhysicalMemory / 1MB, 2))
)
try {
  $m = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory -ErrorAction Stop
  foreach ($f in @('AvailableBytes', 'CommittedBytes', 'CommitLimit', 'CacheBytes', 'FreeAndZeroPageListBytes', 'ModifiedPageListBytes', 'StandbyCacheCoreBytes', 'StandbyCacheNormalPriorityBytes', 'StandbyCacheReserveBytes', 'PoolNonpagedBytes', 'PoolPagedBytes', 'PagesPerSec')) {
    if ($m.$f -ne $null) { $lines += ('{0}={1}' -f $f, $m.$f) }
  }
  $st = 0
  foreach ($f in @('StandbyCacheCoreBytes', 'StandbyCacheNormalPriorityBytes', 'StandbyCacheReserveBytes')) { if ($m.$f) { $st += [int64]$m.$f } }
  $lines += ('Standby_TOTAL_GB={0}   (compte DANS AvailableBytes: le vider ne libere pas de RAM utilisable)' -f [math]::Round($st / 1GB, 2))
} catch { $lines += "Win32_PerfFormattedData_PerfOS_Memory INDISPONIBLE: $($_.Exception.Message)" }
$lines += ('sum_WS_tous_processus_GB={0}' -f [math]::Round((((Get-Process -ErrorAction SilentlyContinue) | Measure-Object WS -Sum).Sum) / 1GB, 2))
foreach ($pf in (Get-CimInstance Win32_PageFileUsage)) { $lines += ('pagefile {0} alloue_MB={1} usage_MB={2}' -f $pf.Name, $pf.AllocatedBaseSize, $pf.CurrentUsage) }
W 'lot6_ram.txt' $lines

# --- lot 7 : VRAM. Seul le total est fiable (le detail par processus est N/A en WDDM grand public) ---
$lines = @()
$nv = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
if ($nv) {
  $lines += "nvidia-smi=$($nv.Source)"
  $lines += '--- GPU (a rapporter) ---'
  $lines += (nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu --format=csv)
  $lines += '--- processus compute (used_memory souvent [N/A] sur pilote grand public) ---'
  $lines += (nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv)
} else {
  $lines += 'nvidia-smi absent du PATH'
  $lines += ((Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -match 'nvidia|cuda' } | Select-Object ProcessName, Id, @{n = 'WS_MB'; e = { [math]::Round($_.WS / 1MB, 1) }} | Format-Table -AutoSize | Out-String))
}
W 'lot7_gpu_vram.txt' $lines

Write-Output "OK inventaire (lecture seule) -> $Out"
