@echo off
REM Delayed gateway restart — kill the real gateway python process (which the VBS
REM spawns detached, so schtasks /end alone does NOT reach it), then re-run the
REM scheduled task so the new process picks up .env + patched adapter.py.
setlocal
timeout /t 15 /nobreak >nul
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*hermes_cli.main gateway run*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 5 /nobreak >nul
schtasks /run /tn "Hermes_Gateway"
endlocal
exit /b 0
