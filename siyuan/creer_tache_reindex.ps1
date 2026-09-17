# Cree la tache planifiee « Hermes - Reindex RAG » : reindexation quotidienne a 03h00.
# Tache UTILISATEUR (pas systeme), sans privilege eleve. Le script lui-meme ne fait rien
# si le noyau SiYuan ne repond pas sur 6806, et retire toujours son verrou.
$nom     = "Hermes - Reindex RAG"
$python  = "C:\Users\searc\AppData\Local\hermes\data\rag\venv\Scripts\python.exe"
$script  = "C:\Users\searc\AppData\Local\hermes\data\rag\reindex_auto.py"
$dossier = "C:\Users\searc\AppData\Local\hermes\data\rag"

$action   = New-ScheduledTaskAction -Execute $python -Argument "`"$script`"" -WorkingDirectory $dossier
$trigger  = New-ScheduledTaskTrigger -Daily -At "03:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
                                          -DontStopIfGoingOnBatteries `
                                          -StartWhenAvailable `
                                          -MultipleInstances IgnoreNew `
                                          -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
                                          -WakeToRun

Register-ScheduledTask -TaskName $nom -Action $action -Trigger $trigger `
                       -Settings $settings `
                       -Description "Reindexe le RAG local (SiYuan + skills + scripts v4 + WordPress) chaque nuit a 03h00. Ne fait rien si SiYuan est arrete. Journal : reindex.log" `
                       -Force | Out-Null

$t = Get-ScheduledTask -TaskName $nom
"Tache creee  : {0}" -f $t.TaskName
"Etat         : {0}" -f $t.State
"Utilisateur  : {0}" -f $t.Principal.UserId
"Declencheur  : {0}" -f $t.Triggers[0].CimClass.CimClassName
"Action       : {0} {1}" -f $t.Actions[0].Execute, $t.Actions[0].Arguments
"Prochain run : {0}" -f (Get-ScheduledTaskInfo -TaskName $nom).NextRunTime
