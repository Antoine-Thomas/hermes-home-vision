<!-- Extrait de hermes-operations/SKILL.md, lignes 219-286 (compression A.3 du 2026-10-06) — contenu verbatim. -->

### Créer une tâche planifiée Hermes (Windows)

Reprendre le principal d'une tâche existante au lieu d'en inventer un :
`Export-ScheduledTask -TaskName 'Hermes - check memory'` montre la convention du parc (SID de
l'utilisateur courant + `<LogonType>InteractiveToken</LogonType>`).

```powershell
$action   = New-ScheduledTaskAction -Execute $python -Argument ('"' + $script + '" --auto') -WorkingDirectory (Split-Path $script)
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 4:00am
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName '<nom>' -Action $action -Trigger $trigger -Settings $settings -Force
```

- Pointer l'action sur le python du venv Hermes en **chemin absolu**, jamais un `python` nu : le
  contexte de la tâche n'a pas le PATH de la session interactive.
- `-StartWhenAvailable` : un déclenchement manqué (PC éteint la nuit) se rattrape au démarrage suivant.
- Garder la création dans un script ré-exécutable à côté du script cible
  (`scripts/creer_tache_<nom>.ps1`) — c'est ce qui rend la tâche reproductible après un incident.
- Tester avec `Start-ScheduledTask -TaskName '<nom>'`, puis lire `Get-ScheduledTaskInfo`
  (`LastRunTime`, `LastTaskResult`) **et** le log propre du script : un code retour suffit à déclarer
  victoire alors que le script n'a rien écrit.
- Une tâche `Disabled` alors que `hermes doctor` voit le service tourner (cas du profil watch) ne
  remontera pas seule après un redémarrage : le signaler plutôt que le corriger sans demande.
- **Une tâche planifiée ne ressuscite pas un process mort.** Un déclencheur `LogonTrigger` seul n'a
  pas de prochaine exécution (`NextRunTime` vide) : le service lancé ne revient qu'au prochain logon,
  sans aucun signal entre-temps. Pour tout service long-running (proxy, sidecar), ajouter
  `-StartWhenAvailable` **et** une répétition, le launcher restant idempotent (« si le port écoute,
  sortir ») :
  ```powershell
  $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15)
  ```
  avec `-MultipleInstances IgnoreNew` pour ne pas empiler les instances.
- **Greffer la répétition sur un déclencheur `LogonTrigger` existant la laisse INERTE jusqu'au prochain
  logon.** `Set-ScheduledTask -Trigger` accepte la modification, le XML affiche bien
  `<Repetition><Interval>PT15M</Interval>`, et pourtant `NextRunTime` reste vide : la fenêtre de
  répétition ne s'arme qu'au déclenchement du logon. Deux conséquences : (a) vérifier l'effet sur
  `Get-ScheduledTaskInfo … NextRunTime`, jamais sur le XML ; (b) pour une couverture armée tout de
  suite, ajouter un **second** déclencheur `New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1)`
  portant la même répétition, et garder le logon pour la reprise après redémarrage.
- **Un script qui touche a l'installation se livre en SPEC d'abord, en code ensuite.** Ecrire
  `bootstrap.ps1` (installation, taches planifiees, demarrage de services) sans validation prealable se
  fait refuser : presenter l'ordre des etapes, le perimetre exact de chaque action, ce que le script ne
  peut pas faire (secrets, installs hors depot) et les questions ouvertes, puis attendre. Convention
  du parc pour tout script qui modifie quelque chose : **`-DryRun` par defaut, `-Apply` pour executer**,
  idempotence, journal horodate, et `-SelfTest` quand il reecrit un fichier de config. **Le test
  `-DryRun` doit prouver l'ABSENCE d'effet**, pas seulement afficher une sortie plausible : relever le
  md5 d'un fichier sensible (`config.yaml`) et `git status --short` avant/apres, plus le code de sortie
  (0 avec 0 echec). Un `-DryRun` qui ecrit son journal dans le depot le salit : poser le motif du
  journal au `.gitignore`. **Et un controle de prerequis doit viser un vrai ecouteur** : tester la
  connectivite sortante sur `127.0.0.1:443` ne peut qu'echouer (rien n'ecoute en local) et fait
  annoncer une panne reseau inexistante a chaque execution — viser un hote distant (`github.com:443`).
- **Le durcissement est un script, pas une commande.** Livrer le `.ps1` rejouable qui prend le backup
  XML (`Export-ScheduledTask | Out-File -Encoding UTF8`), modifie puis se vérifie lui-même, et
  l'exécuter depuis là : c'est le seul moyen de revenir à l'état cible après incident, et ça rend la
  définition auditable en clair (au lieu du `schtasks /Query` en UTF-16).
- **Tâche dont `LastTaskResult ≠ 0`** : trois causes à séparer avant de proposer un correctif —
  script jamais chargé (aucun log), abort volontaire (`exit 1` dans un garde-fou du script), crash
  réel. La présence du log que le script écrit dès ses premières lignes tranche à elle seule.
  Recette complète : `references/windows-task-failure-triage.md`.
- **Rediriger la sortie d'un sidecar lancé masqué** (`wscript`/`pythonw`, `SW_HIDE`) vers un fichier
  de log. stdout sur fenêtre cachée est perdu : une panne sans log est une panne invisible, et
  `LastTaskResult = 0` ne dit rien de la santé du process lancé.
- **Vérifier ce que la tâche a réellement fait**, pas seulement qu'elle a tourné : confronter
  `LastRunTime` aux événements de session (`Get-WinEvent -FilterHashtable @{LogName='System';
  Id=7001} -MaxEvents 8`). Un `LastRunTime` égal à l'heure du dernier logon signifie « déclencheur de
  logon », pas « planification récurrente » — deux situations qui appellent des conclusions opposées
  sur la cause de la panne.

