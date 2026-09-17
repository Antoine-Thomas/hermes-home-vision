' AudioGuardian-Watchdog — check/relaunch guardian.py in silent mode (no console)
' Launch via wscript.exe (no window), replaces old pwsh launcher that flashed.
Option Explicit
Dim sh, workDir, python, scriptPath, running, col, proc

Set sh = CreateObject("WScript.Shell")
workDir = "C:\Users\searc\AppData\Local\hermes\data\surveillance\audio_guardian"
python  = workDir & "\venv311\Scripts\python.exe"
scriptPath = workDir & "\guardian.py"

' 1) Check if guardian.py is already running (via python.exe command line)
Set col = GetObject("winmgmts:\\.\root\cimv2").ExecQuery( _
  "SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='python.exe'")
running = False
For Each proc In col
  If InStr(1, proc.CommandLine, "guardian.py", vbTextCompare) > 0 Then
    running = True
    Exit For
  End If
Next

If running Then
  WScript.Quit(0)   ' already active -> silent exit
End If

' 2) Launch guardian silently (2nd arg 0 = no window)
sh.CurrentDirectory = workDir
sh.Run python & " " & scriptPath, 0, False
WScript.Quit(0)
