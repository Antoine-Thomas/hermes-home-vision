@echo off
REM OmniRoute auto-launch for Hermes (robust, no PowerShell Start-Process).
REM Uses omniroute's native --daemon (self-backgrounds + auto-restarts on crash).
REM Idempotent: if port 20128 is already open, do nothing.
REM Full path to the npm shim so it works from scheduled tasks (PATH-independent).
setlocal

netstat -an 2>nul | findstr /i "LISTENING" | findstr /r ":20128 " >nul
if %errorlevel%==0 (
  echo OmniRoute already running on :20128
  goto :eof
)

REM Detach via start so the launching process (schtask / bash) returns immediately.
start "" /min cmd /c ""C:\Users\searc\AppData\Roaming\npm\omniroute.cmd" serve --daemon --no-open"
echo OmniRoute launch requested.
endlocal
exit /b 0
