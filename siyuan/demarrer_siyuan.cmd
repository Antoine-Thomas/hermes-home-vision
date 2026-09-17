@echo off
rem ---------------------------------------------------------------------------
rem Demarre le noyau SiYuan (second cerveau de Hermes) sur le port 6806.
rem Le jeton d'API et le code d'autorisation sont deja dans
rem   C:\Users\searc\SiYuan\hermes-projects\conf\conf.json
rem donc rien de secret ne figure dans ce script.
rem Hermes lit ensuite SIYUAN_TOKEN et SIYUAN_URL depuis
rem   %LOCALAPPDATA%\hermes\.env
rem ---------------------------------------------------------------------------
set KERNEL=%LOCALAPPDATA%\Programs\SiYuan\resources\kernel\SiYuan-Kernel.exe
set WORKSPACE=C:\Users\searc\SiYuan\hermes-projects

netstat -ano | findstr ":6806" | findstr "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    echo SiYuan tourne deja sur le port 6806.
    exit /b 0
)

echo Demarrage du noyau SiYuan...
start "SiYuan Kernel" /min "%KERNEL%" serve --workspace="%WORKSPACE%" --port=6806 --lang=fr_FR
echo Noyau lance. Interface : http://127.0.0.1:6806
