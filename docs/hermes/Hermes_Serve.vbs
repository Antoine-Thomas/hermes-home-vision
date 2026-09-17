' Hermes Agent - backend headless (« serve ») pour le second cerveau.
' Tache planifiee « Hermes - serve backend », a l'ouverture de session.
' Meme mecanisme que Hermes_Gateway.vbs : mode 0 = aucune fenetre visible.
Option Explicit
Dim sh, env, existing_pp
Set sh = CreateObject("WScript.Shell")
Set env = sh.Environment("PROCESS")
env.Item("HERMES_HOME") = "C:\Users\searc\AppData\Local\hermes"
env.Item("PYTHONIOENCODING") = "utf-8"
env.Item("HERMES_SUPERVISED_CHILD") = "1"
env.Item("VIRTUAL_ENV") = "C:\Users\searc\AppData\Local\hermes\hermes-agent\.venv"
existing_pp = env.Item("PYTHONPATH")
If Len(existing_pp) > 0 Then
  env.Item("PYTHONPATH") = "C:\Users\searc\AppData\Local\hermes\hermes-agent;" & existing_pp
Else
  env.Item("PYTHONPATH") = "C:\Users\searc\AppData\Local\hermes\hermes-agent"
End If
sh.CurrentDirectory = "C:\Users\searc\AppData\Local\hermes"
sh.Run "C:\Users\searc\AppData\Local\hermes\hermes-agent\.venv\Scripts\python.exe -m hermes_cli.main serve", 0, False
