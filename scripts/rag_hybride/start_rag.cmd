@echo off
rem Lance le serveur RAG local sur 127.0.0.1:8200 (venv stable, pas le runtime ephemere).
rem - verifie d'abord que le port 8200 n'est pas deja occupe (sinon sortie propre)
rem - rotation simple du journal au-dela de ~5 Mo
cd /d "C:\Users\searc\AppData\Local\hermes\data\rag"

rem 1) Port deja en ecoute ? -> deja actif, on ne lance pas de second serveur.
netstat -ano | findstr ":8200" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 goto deja_actif

rem 2) Rotation du journal si > 5 Mo
powershell -NoProfile -Command "if ((Test-Path 'logs\serveur_rag.log') -and ((Get-Item 'logs\serveur_rag.log').Length -gt 5242880)) { Move-Item -Force 'logs\serveur_rag.log' 'logs\serveur_rag.log.1' }"

rem 3) Lancement en boucle : si le serveur meurt, il est relance apres 5 s.
:relance
venv\Scripts\python.exe serveur_rag.py >> logs\serveur_rag.log 2>&1
echo [%date% %time%] serveur termine (code %errorlevel%), relance dans 5s >> logs\serveur_rag.log
timeout /t 5 /nobreak >nul
goto relance

:deja_actif
echo [%date% %time%] deja actif - port 8200 occupe - sortie sans relancer >> logs\serveur_rag.log

:fin
