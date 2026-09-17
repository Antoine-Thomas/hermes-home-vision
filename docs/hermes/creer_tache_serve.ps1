# Cree la tache planifiee « Hermes - serve backend » : backend Hermes headless a l'ouverture de session.
# Meme mecanisme silencieux que Hermes_Gateway : un lanceur .vbs en mode cache.
$nom     = "Hermes - serve backend"
$vbs     = "C:\Users\searc\AppData\Local\hermes\gateway-service\Hermes_Serve.vbs"
$dossier = "C:\Users\searc\AppData\Local\hermes"

$action   = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "//B //Nologo `"$vbs`"" -WorkingDirectory $dossier
$trigger  = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
                                         -DontStopIfGoingOnBatteries `
                                         -StartWhenAvailable `
                                         -MultipleInstances IgnoreNew `
                                         -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $nom -Action $action -Trigger $trigger `
                       -Settings $settings `
                       -Description "Backend Hermes headless (serve) pour le second cerveau : aucune fenetre, demarrage a l'ouverture de session." `
                       -Force | Out-Null

$t = Get-ScheduledTask -TaskName $nom
"Tache creee  : {0}" -f $t.TaskName
"Etat         : {0}" -f $t.State
"Action       : {0} {1}" -f $t.Actions[0].Execute, $t.Actions[0].Arguments
"Declencheur  : {0}" -f $t.Triggers[0].CimClass.CimClassName
