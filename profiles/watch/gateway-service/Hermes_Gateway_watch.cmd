@echo off
rem Hermes Agent Gateway - Messaging Platform Integration
cd /d C:\Users\searc\AppData\Local\hermes\profiles\watch
set "HERMES_HOME=C:\Users\searc\AppData\Local\hermes\profiles\watch"
set "PYTHONIOENCODING=utf-8"
set "HERMES_GATEWAY_DETACHED=1"
set "HERMES_SUPERVISED_CHILD=1"
set "VIRTUAL_ENV=C:\Users\searc\AppData\Local\hermes\hermes-agent\venv"
set "PYTHONPATH=C:\Users\searc\AppData\Local\hermes\hermes-agent;%PYTHONPATH%"
C:\Users\searc\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe -m hermes_cli.main --profile watch gateway run
exit /b 0
