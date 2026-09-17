' NVIDIA NIM proxy auto-launch for Hermes — hidden window (no console flash)
Option Explicit
Dim sh, env, rc, py, script, logPath, fso
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set env = sh.Environment("PROCESS")
' Redirecting stdout to a file drops Python to the locale code page (cp1252) and the
' '[PROXY] x -> y' lines then raise UnicodeEncodeError, killing every request. Force UTF-8.
env.Item("PYTHONIOENCODING") = "utf-8"
py      = "C:\Users\searc\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe"
script  = "C:\Users\searc\AppData\Local\hermes\data\nvidia\nvidia-nim-proxy.py"
logPath = "C:\Users\searc\AppData\Local\hermes\data\nvidia\proxy.log"
' Idempotent: quit only if something is really LISTENING on 20200. A bare findstr on
' ":20200 " also matches client sockets left in TIME_WAIT after a restart, which made
' this launcher refuse to restart a dead proxy.
rc = sh.Run("cmd /c netstat -an | findstr "":20200 "" | findstr ""LISTENING"" >nul", 0, True)
If rc = 0 Then WScript.Quit 0
' Rotation simple : au-dela de 10 Mo, proxy.log devient proxy.log.1 (un seul historique).
If fso.FileExists(logPath) Then
  If fso.GetFile(logPath).Size > 10485760 Then
    If fso.FileExists(logPath & ".1") Then fso.DeleteFile logPath & ".1", True
    fso.MoveFile logPath, logPath & ".1"
  End If
End If
' Launch detached, hidden, unbuffered; stdout+stderr appended to proxy.log
sh.Run "cmd /c """"" & py & """ -u """ & script & """ >> """ & logPath & """ 2>&1""", 0, False
