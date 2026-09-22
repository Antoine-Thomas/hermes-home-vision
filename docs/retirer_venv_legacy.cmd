@echo off
REM Double-clic : met a la retraite le venv Hermes perime (.venv -> .venv.retired-0.20.5)
REM A lancer APRES avoir ferme toute session Hermes (sinon Windows refuse le renommage).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0retirer_venv_legacy.ps1"
echo.
echo Journal : C:\Users\searc\AppData\Local\hermes\docs\retirer_venv_legacy.log
pause
