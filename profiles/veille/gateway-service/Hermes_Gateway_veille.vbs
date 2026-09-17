' Hermes Agent Gateway - Messaging Platform Integration
' Profil : veille  (miroir exact de Hermes_Gateway_watch.vbs, chemins et profil changes)
Option Explicit
Dim sh, env, existing_pp
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("PROCESS")
env.Item("HERMES_HOME") = "C:\Users\searc\AppData\Local\hermes\profiles\veille"
env.Item("PYTHONIOENCODING") = "utf-8"
env.Item("HERMES_GATEWAY_DETACHED") = "1"
env.Item("HERMES_SUPERVISED_CHILD") = "1"
env.Item("VIRTUAL_ENV") = "C:\Users\searc\AppData\Local\hermes\hermes-agent\venv"
existing_pp = env.Item("PYTHONPATH")
If Len(existing_pp) > 0 Then
  env.Item("PYTHONPATH") = "C:\Users\searc\AppData\Local\hermes\hermes-agent;" & existing_pp
Else
  env.Item("PYTHONPATH") = "C:\Users\searc\AppData\Local\hermes\hermes-agent"
End If
sh.CurrentDirectory = "C:\Users\searc\AppData\Local\hermes\profiles\veille"
sh.Run "C:\Users\searc\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe -m hermes_cli.main --profile veille gateway run", 0, False
