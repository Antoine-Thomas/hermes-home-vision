# Gabarits — service Windows en arriere-plan

## Lanceur `.vbs` (mode cache + garde-fou de port)

```vbscript
' ASCII pur : wscript/PowerShell lisent l'UTF-8 sans BOM comme de l'ANSI.
Option Explicit
Dim shell, journal, deja
Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "C:\chemin\du\service"

' 1) le service tourne-t-il deja ? (verification cachee)
journal = shell.ExpandEnvironmentStrings("%TEMP%") & "\service_port.txt"
shell.Run "cmd /c netstat -ano | findstr "":9119"" | findstr ""LISTENING"" > """ & journal & """", 0, True
deja = False
On Error Resume Next
Dim fso, f
Set fso = CreateObject("Scripting.FileSystemObject")
If fso.FileExists(journal) Then
    Set f = fso.OpenTextFile(journal, 1)
    If Not f.AtEndOfStream Then
        If Len(Trim(f.ReadAll)) > 0 Then deja = True
    End If
    f.Close
End If
On Error GoTo 0
If deja Then WScript.Quit 0

' 2) lancement DIRECT, fenetre cachee (jamais via un .cmd qui ferait start /min)
shell.Run """C:\chemin\du\service.exe"" serve --port=9119", 0, False
```

Pour un service Hermes, calquer sur `%LOCALAPPDATA%\hermes\gateway-service\*.vbs` : definir
`HERMES_HOME`, `PYTHONIOENCODING`, `VIRTUAL_ENV`, `PYTHONPATH`, fixer `CurrentDirectory`, puis
`python.exe -m hermes_cli.main <commande>` en mode 0.

## Enregistrement de la tache — depuis un `.ps1`

```powershell
$nom    = "Service - mon service"
$vbs    = "C:\chemin\du\service.vbs"
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B //Nologo `"$vbs`"" -WorkingDirectory "C:\chemin"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
                                         -DontStopIfGoingOnBatteries `
                                         -StartWhenAvailable `
                                         -MultipleInstances IgnoreNew `
                                         -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $nom -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
```

Appel : `powershell -NoProfile -ExecutionPolicy Bypass -File <script.ps1>` — pas de commande en ligne.

## Preuve de visibilite (enumeration des fenetres)

```powershell
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  public static List<string> Pour(int c) {
    var r = new List<string>();
    EnumWindows((h,l) => { uint p; GetWindowThreadProcessId(h, out p);
      if (p == (uint)c) { var k=new StringBuilder(256); GetClassName(h,k,256);
        r.Add(string.Format("classe={0} visible={1}", k, IsWindowVisible(h))); } return true; }, IntPtr.Zero);
    return r; } }
'@
[W]::Pour((Get-Process <nom>).Id)
```

`classe=ConsoleWindowClass visible=True` = console encore visible. `visible=False` = objectif atteint.

## Pieges constates

| Symptome | Cause | Correctif |
|---|---|---|
| La console reste visible malgre le `.vbs` | la cible est lancee via un `.cmd` qui fait `start /min` | lancer la cible directement en mode 0 |
| `Register-ScheduledTask : mappage de compte introuvable` | `$env:` mange par bash | passer par un `.ps1` appele en `-File` |
| Accents / tirets longs illisibles dans la sortie | `.ps1`/`.vbs` UTF-8 sans BOM lu comme ANSI | garder les scripts en ASCII |
| Le journal du service a disparu | service lance sans dossier de travail | `CurrentDirectory` / `-WorkingDirectory` |
| Deux services sur le meme port | pas de garde-fou de port | tester le port avant de lancer |
| La commande `status` ne voit pas le service | fichier de PID absent selon le mode de lancement | verifier processus + port |
