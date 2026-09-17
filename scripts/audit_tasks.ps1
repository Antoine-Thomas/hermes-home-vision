
# Step 2: Identify tasks causing console flashes
Write-Host "--- STEP 2: Tasks that open a console ---"
Get-ScheduledTask | Where-Object { 
 $_.Actions.Execute -like "*cmd*" -or 
 $_.Actions.Execute -like "*powershell*" -or 
 $_.Actions.Execute -like "*wscript*" 
} | ForEach-Object { 
 Write-Host "`n=== $($_.TaskName) ==="
 Write-Host "Execute: $($_.Actions.Execute)"
 Write-Host "Arguments: $($_.Actions.Arguments)"
 Write-Host "State: $($_.State)"
}

# Step 3: Wazuh-related tasks
Write-Host "`n--- STEP 3: Wazuh/Security Tasks ---"
Get-ScheduledTask | Where-Object { 
 $_.TaskName -like "*wazuh*" -or 
 $_.TaskName -like "*security*" -or 
 $_.TaskName -like "*monitor*" 
} | Format-Table TaskName,State,TaskPath -AutoSize

# Step 5: Verify OmniRoute tasks
Write-Host "`n--- STEP 5: OmniRoute Tasks Verification ---"
Get-ScheduledTask -TaskName "OmniRoute*" | ForEach-Object { 
 Write-Host "`n=== $($_.TaskName) ==="
 Write-Host "Execute: $($_.Actions.Execute)"
 Write-Host "Arguments: $($_.Actions.Arguments)"
}

# Step 6: Processes with windows
Write-Host "`n--- STEP 6: Processes with Windows ---"
Get-Process | Where-Object { $_.MainWindowTitle -ne "" } | Format-Table Name,MainWindowTitle -AutoSize
