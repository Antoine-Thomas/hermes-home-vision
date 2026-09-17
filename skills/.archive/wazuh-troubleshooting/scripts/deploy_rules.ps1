#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Deploy a custom Wazuh rules file into a single-node Docker manager, with
  validation and automatic rollback.

.DESCRIPTION
  Safe-by-construction deploy. Each guard exists because its absence caused a
  real incident (see references/custom-rules-windows-eventchannel.md):

    - destination name DERIVED from the source basename
      A hardcoded destination silently overwrites an unrelated rule file the
      first time the script is reused for a different rule set.
    - XML well-formedness checked on the host
      Catches the "XML comment cannot contain '--'" class of error before any
      container is touched.
    - ID collision check against every other file in /var/ossec/etc/rules/
      Wazuh does not warn on duplicate rule ids; the later definition just wins.
    - config validated with `wazuh-analysisd -t`, keyed on EXIT CODE
      `wazuh-logtest` has no -t flag. Grepping stderr for "error" produces false
      rollbacks of valid deployments.
    - timestamped .bak + restore on failure, so the manager is never left blind.

.PARAMETER RulesFile
  Path to the .xml rules file. Defaults to the first *_rules.xml next to this script.

.PARAMETER Container
  Manager container name. Default: single-node-wazuh.manager-1

.EXAMPLE
  .\deploy_rules.ps1 -RulesFile .\my_rules.xml
#>
[CmdletBinding()]
param(
    [string]$RulesFile = '',
    [string]$Container = 'single-node-wazuh.manager-1'
)

$ErrorActionPreference = 'Stop'

function Info ([string]$m) { Write-Host "  $m" }
function Ok   ([string]$m) { Write-Host "  [ok] $m"  -ForegroundColor Green }
function Warn ([string]$m) { Write-Host "  [!] $m"   -ForegroundColor Yellow }
function Die  ([string]$m) { Write-Host "  [X] $m"   -ForegroundColor Red; exit 1 }

if (-not $RulesFile) {
    $cand = Get-ChildItem -Path $PSScriptRoot -Filter '*_rules.xml' -ErrorAction SilentlyContinue |
            Select-Object -First 1
    if ($cand) { $RulesFile = $cand.FullName }
}
if (-not $RulesFile -or -not (Test-Path $RulesFile)) { Die "rules file not found: $RulesFile" }

# Destination derived from SOURCE basename - never hardcode it.
$leaf = Split-Path -Leaf $RulesFile
$dest = "/var/ossec/etc/rules/$leaf"

Write-Host "`n===== WAZUH CUSTOM RULES DEPLOY =====" -ForegroundColor Magenta
Info "source      : $RulesFile"
Info "destination : ${Container}:$dest"

# --- 0. container up? -----------------------------------------------------
$running = docker ps --filter "name=$Container" --format "{{.Names}}" 2>$null
if ($running -notcontains $Container) { Die "container $Container is not running" }
Ok "container running"

# --- 1. XML well-formedness (host side) -----------------------------------
try {
    [xml]$null = Get-Content -Raw -Encoding UTF8 $RulesFile
    Ok "XML well-formed"
} catch {
    Die "invalid XML: $($_.Exception.Message)"
}

# --- 2. rule id collisions ------------------------------------------------
$ids = [regex]::Matches((Get-Content -Raw $RulesFile), 'rule\s+id="(\d+)"') |
       ForEach-Object { $_.Groups[1].Value }
Info "rules in file: $($ids.Count) (IDs $($ids -join ', '))"

$collisions = @()
$others = docker exec $Container sh -c "ls /var/ossec/etc/rules/*.xml 2>/dev/null" 2>$null
foreach ($f in $others) {
    if (-not $f) { continue }
    if ((Split-Path -Leaf $f) -eq $leaf) { continue }   # our own previous copy
    $content = docker exec $Container sh -c "cat '$f'" 2>$null
    foreach ($id in $ids) {
        if ($content -match "rule\s+id=`"$id`"") { $collisions += "$id already defined in $f" }
    }
}
if ($collisions.Count -gt 0) {
    $collisions | ForEach-Object { Warn "    $_" }
    Die "ID collision - change the IDs (Wazuh will NOT warn, the later one wins)"
}
Ok "no ID collision"

# --- 3. backup ------------------------------------------------------------
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$existed = docker exec $Container sh -c "test -f '$dest' && echo yes || echo no" 2>$null
if ($existed -match 'yes') {
    docker exec $Container sh -c "cp '$dest' '$dest.bak.$stamp'" | Out-Null
    Ok "backup: $dest.bak.$stamp"
}

# --- 4. copy --------------------------------------------------------------
docker cp "$RulesFile" "${Container}:$dest"
if ($LASTEXITCODE -ne 0) { Die "docker cp failed ($LASTEXITCODE)" }
docker exec $Container sh -c "chown wazuh:wazuh '$dest' 2>/dev/null; chmod 660 '$dest'" | Out-Null
Ok "file copied"

# --- 5. validate BEFORE restart, on exit code ----------------------------
Info "validating (wazuh-analysisd -t)..."
$out  = (docker exec $Container /var/ossec/bin/wazuh-analysisd -t 2>&1 | Out-String)
$code = $LASTEXITCODE
if ($code -ne 0) {
    ($out -split "`n" | Where-Object { $_.Trim() } | Select-Object -First 15) |
        ForEach-Object { Warn "    $_" }
    docker exec $Container sh -c "rm -f '$dest'" | Out-Null
    if ($existed -match 'yes') {
        docker exec $Container sh -c "cp '$dest.bak.$stamp' '$dest'" | Out-Null
        Warn "previous version restored"
    }
    Die "rules rejected by Wazuh - nothing applied"
}
Ok "rules accepted"

# --- 6. reload ------------------------------------------------------------
Info "restarting manager..."
docker exec $Container /var/ossec/bin/wazuh-control restart | Out-Null
Start-Sleep -Seconds 8

$status = docker exec $Container /var/ossec/bin/wazuh-control status 2>$null | Out-String
if ($status -match 'wazuh-analysisd is running') {
    Ok "analysisd running - rules loaded"
} else {
    Warn "logs: docker exec $Container tail -30 /var/ossec/logs/ossec.log"
    Die "analysisd is NOT running - rules are invalid"
}

Write-Host ""
Ok "deploy complete"
Info "test a rule: docker exec $Container /var/ossec/bin/wazuh-logtest"
Info "for eventchannel/<field> rules, verify end-to-end via alerts.json instead"
