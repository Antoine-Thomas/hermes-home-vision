#=============================================================================
# Hermes Auto-Ticketing - PowerShell (Windows/ServiceNow/Jira)
# Lit scan_results.csv, mappe action_taken vers tickets
# Usage: .\auto_ticketing.ps1 -CSV scan_results.csv -TicketSystem snow -DryRun
#=============================================================================
param(
    [string]$CSV = ".\scan_results.csv",
    [string]$TicketSystem = "snow",
    [string]$WebhookUrl = $env:WEBHOOK_URL,
    [string]$Auth = $env:WEBHOOK_AUTH,
    [switch]$DryRun
)

$PriorityMap = @{
    "isolate-host"    = "P0"
    "forensics-image" = "P0"
    "revoke-keys"     = "P1"
    "rotate-passwords"= "P1"
    "monitor"         = "P2"
    "clean-up"        = "P2"
    "notify-owner"    = "P3"
}

$TypeMap = @{
    "isolate-host"    = "Incident"
    "forensics-image" = "Forensic Request"
    "revoke-keys"     = "Task"
    "rotate-passwords"= "Task"
    "monitor"         = "Investigation"
    "clean-up"        = "Remediation"
    "notify-owner"    = "Notification"
}

Write-Host "=== Hermes Auto-Ticketing (PowerShell) ===" -ForegroundColor Cyan
Write-Host "CSV: $CSV | System: $TicketSystem | DryRun: $DryRun"

if (-not (Test-Path $CSV)) { Write-Error "CSV not found: $CSV"; exit 1 }

$data = Import-Csv $CSV
$ticketCount = 0

foreach ($row in $data) {
    $hostname = $row.host
    $ip = $row.ip
    $actions = $row.action_taken -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
    
    foreach ($act in $actions) {
        $priority = if ($PriorityMap.ContainsKey($act)) { $PriorityMap[$act] } else { "P3" }
        $type = if ($TypeMap.ContainsKey($act)) { $TypeMap[$act] } else { "Task" }
        $summary = "$act : $hostname ($ip)"
        $desc = @"
Action: $act
Host: $hostname ($ip)
Date: $($row.date_scan) | OS: $($row.os) | Role: $($row.role)
Connections external: $($row.connections_external)
Alerts Wazuh: $($row.alerts_wazuh_recentes)
Recommendation: $($row.security_recommendation)
Evidence: /tmp/${hostname}_evidence.tar.gz.gpg
Notes: $($row.notes)
"@
        
        Write-Host "-> $act | Priority: $priority | Type: $type" -ForegroundColor Yellow
        
        $payload = $null
        $headers = @{"Content-Type" = "application/json"}
        if ($Auth) { $headers["Authorization"] = "Basic $Auth" }
        
        switch ($TicketSystem) {
            "jira" {
                $payload = @{
                    fields = @{
                        project = @{key = "SEC"}
                        summary = $summary
                        description = $desc
                        issuetype = @{name = $type}
                        priority = @{name = $priority}
                    }
                } | ConvertTo-Json -Depth 4
            }
            "snow" {
                $urgency = if ($priority -eq "P0") { 1 } elseif ($priority -eq "P1") { 2 } else { 3 }
                $payload = @{
                    short_description = $summary
                    description = $desc
                    urgency = $urgency
                    assignment_group = "SOC"
                } | ConvertTo-Json -Depth 3
            }
            "generic" {
                $payload = @{
                    action = $act
                    host = $hostname
                    ip = $ip
                    summary = $summary
                    description = $desc
                    priority = $priority
                    timestamp = (Get-Date -Format "o")
                } | ConvertTo-Json -Depth 3
            }
        }
        
        if ($DryRun) {
            Write-Host "[DRY-RUN] $summary" -ForegroundColor Green
        } else {
            try {
                $response = Invoke-RestMethod -Uri $WebhookUrl -Method POST -Headers $headers -Body $payload
                Write-Host "Ticket created: $($response.key ?? $response.result.number ?? $response)" -ForegroundColor Green
            } catch {
                Write-Error "Failed: $_"
            }
        }
        $ticketCount++
    }
}

Write-Host "=== Done: $ticketCount tickets processed ===" -ForegroundColor Cyan
