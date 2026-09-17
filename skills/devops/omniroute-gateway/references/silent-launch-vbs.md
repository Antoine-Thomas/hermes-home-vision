# Silent Launch via VBS

To prevent "flash" of the console window on Windows when launching OmniRoute via Task Scheduler:

1. Create `omniroute-launch.vbs`:
```vbscript
Option Explicit
Dim sh
Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c ""C:\Users\searc\AppData\Roaming\npm\omniroute.cmd"" serve --daemon --no-open", 0, False
```
2. In Task Scheduler, configure the action to:
   - Program: `wscript.exe`
   - Arguments: `//B C:\path\to\omniroute-launch.vbs`

This runs the command completely hidden.
