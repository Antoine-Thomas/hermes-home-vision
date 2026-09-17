' OmniRoute auto-launch — hidden window (no console flash)
Option Explicit
Dim sh, rc
Set sh = CreateObject("WScript.Shell")
rc = sh.Run("cmd /c netstat -an | findstr /r "":20128 "" >nul", 0, True)
If rc = 0 Then WScript.Quit 0
sh.Run """C:\Users\searc\AppData\Roaming\npm\omniroute.cmd"" serve --daemon --no-open", 0, False
