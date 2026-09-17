# Restart the Hermes gateway: wait, kill the real gateway python process(es),
# then re-run the scheduled task so the new process loads .env + patched adapter.py.
Start-Sleep -Seconds 15
$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*hermes_cli.main gateway run*' }
foreach ($p in $procs) {
    try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop }
    catch { Write-Output ("kill failed for " + $p.ProcessId) }
}
Start-Sleep -Seconds 5
schtasks /run /tn "Hermes_Gateway"
