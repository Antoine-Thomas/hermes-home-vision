# Console Flash Prevention (Windows Tasks)

When scheduled tasks run command-line tools (`.cmd`, `.py`, `.bat`) on Windows, they frequently trigger a visible console window (a "flash").

## Technique
To prevent this, use a VBScript wrapper or PowerShell `-WindowStyle Hidden` instead of direct execution.

### VBScript Wrapper (Recommended)
This approach is the most robust and invisible:
1. Create a `.vbs` file with this content:
   ```vbscript
   Set sh = CreateObject("WScript.Shell")
   ' Replace the path below with the target command and arguments
   sh.Run "C:\Path\To\Python.exe C:\Path\To\Script.py", 0, False
   ```
2. Update the scheduled task action to execute this script via `wscript.exe //B`.

### PowerShell Hidden Flag
If using PowerShell:
```powershell
powershell -NoProfile -WindowStyle Hidden -File "C:\Path\To\Script.ps1"
```
Do not use `cmd /c` as it inherently shows a window.
