' Lance le noyau SiYuan en arriere-plan, sans AUCUNE fenetre visible.
' Utilise par la tache planifiee « SiYuan - noyau second cerveau » :
'   wscript.exe "C:\Users\searc\SiYuan\demarrer_siyuan_silencieux.vbs"
'
' Pourquoi ce script ne se contente pas d'appeler demarrer_siyuan.cmd (qui reste inchange) :
' le .cmd lance le noyau avec  start /min , ce qui CREE une console (minimisee mais visible :
' mesure du 15/09 -> ConsoleWindowClass visible=True). Le mode 0 de Run masque la console du
' .cmd, pas celle que le .cmd cree ensuite. On lance donc le noyau directement en mode cache,
' en reprenant la meme verification de port et les memes arguments que le .cmd.

Option Explicit

Dim shell, noyau, espace, journal, deja, exec
Set shell = CreateObject("WScript.Shell")

' 1) Le noyau tourne-t-il deja ? (verification du port 6806, elle aussi cachee)
journal = shell.ExpandEnvironmentStrings("%TEMP%") & "\siyuan_port.txt"
shell.Run "cmd /c netstat -ano | findstr "":6806"" | findstr ""LISTENING"" > """ & journal & """", 0, True
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

' 2) Lancement du noyau : mode 0 = fenetre cachee
noyau = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Programs\SiYuan\resources\kernel\SiYuan-Kernel.exe"
espace = "C:\Users\searc\SiYuan\hermes-projects"
shell.Run """" & noyau & """ serve --workspace=""" & espace & """ --port=6806 --lang=fr_FR", 0, False
