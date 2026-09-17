# Cree la tache planifiee qui demarre le noyau SiYuan a l'ouverture de session.
# Tache UTILISATEUR (pas systeme), sans privilege eleve.
$nom      = "SiYuan - noyau second cerveau"
$script   = "C:\Users\searc\SiYuan\demarrer_siyuan.cmd"
$dossier  = "C:\Users\searc\SiYuan"

$action   = New-ScheduledTaskAction -Execute $script -WorkingDirectory $dossier
$trigger  = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
                                          -DontStopIfGoingOnBatteries `
                                          -StartWhenAvailable `
                                          -MultipleInstances IgnoreNew `
                                          -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $nom -Action $action -Trigger $trigger `
                       -Settings $settings `
                       -Description "Demarre le noyau SiYuan (second cerveau de Hermes) a l'ouverture de session." `
                       -Force | Out-Null

$t = Get-ScheduledTask -TaskName $nom
"Tache creee : {0}" -f $t.TaskName
"Etat        : {0}" -f $t.State
"Utilisateur : {0}" -f $t.Principal.UserId
"Declencheur : {0}" -f $t.Triggers[0].CimClass.CimClassName
"Action      : {0}" -f $t.Actions[0].Execute
