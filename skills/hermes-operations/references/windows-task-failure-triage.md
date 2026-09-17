# Triage d'une tâche planifiée Windows en échec (`LastTaskResult ≠ 0`)

## Règle de départ : un code retour n'est pas un diagnostic

`LastTaskResult` confond trois causes très différentes. Les séparer **avant** de proposer un
correctif, sinon on répare au hasard :

1. **Le script n'a jamais été chargé** — aucune écriture, pas même la première ligne de log.
2. **Abort volontaire du script** — un garde-fou a fait `exit 1` ; le script a écrit ses logs.
3. **Crash réel** — trace/traceback dans le log propre du script.

Le signal le plus rentable est **la présence ou l'absence du log que le script écrit dès ses
premières instructions**. Pas de log ⇒ cause 1 : chercher du côté du *lancement* (principal de la
tâche, politique d'exécution, chemin, compte), pas du script. Un `LastTaskResult = 1` accompagné
d'un dossier de logs vide n'est pas « pas de preuve », c'est **la preuve**.

## Cause 1 — politique d'exécution d'un compte système

Une tâche qui tourne sous un autre compte que l'opérateur n'hérite pas de sa politique.
`CurrentUser = RemoteSigned` ne dit **rien** de ce que voit `S-1-5-18` (SYSTEM). Avec
MachinePolicy / UserPolicy / LocalMachine à `Undefined`, un compte système retombe sur le défaut
machine (`Restricted`) : `powershell.exe -File script.ps1` refuse de charger le fichier, sort `1` et
n'écrit rien.

Correctif : ajouter `-ExecutionPolicy Bypass` **aux arguments de l'action de la tâche**. Ne pas
changer la politique machine pour un seul script.

```powershell
# principal + action de la tâche
Export-ScheduledTask -TaskName '<nom>' | Select-String -Pattern '<UserId>|<RunLevel>|<LogonType>|<Command>|<Arguments>'
# portees de politique (le sans -List renvoie la politique effective de l'utilisateur courant, pas celle de la tache)
Get-ExecutionPolicy -List
(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell' -Name ExecutionPolicy -ErrorAction SilentlyContinue).ExecutionPolicy
```

Lecture du principal : `S-1-5-18` = SYSTEM, un SID `S-1-5-21-…-1001` = l'utilisateur interactif.

## Cause 2 — abort volontaire (garde-fou)

Lire les `exit` du script avant de traiter un code non nul comme un échec. Un garde-fou qui refuse
d'agir produit le même code qu'un crash. Exécuter le script directement dans son mode non destructif
(beaucoup exposent `-DryRun` par défaut) montre la raison réelle en clair.

**Corollaire — un garde-fou en correspondance exacte bloque à vie.** Un test `-eq`/`-ne` sur un champ
rédigé à la main ne passe plus dès que le champ reçoit un qualificatif : comparer `"0 alertes"` avec
`-ne` à une cellule CSV contenant `"0 alertes (index neuf)"` est vrai pour toujours. Pour tout champ
de ce type, ancrer un motif (`-match '^0(\s|$)'`), jamais une égalité stricte.

## Cause 3 — vérifier que le run a réellement exécuté le script

`LastRunTime` et `LastTaskResult = 0` ne prouvent rien : un lanceur idempotent peut sortir en no-op
(port déjà occupé, verrou présent) et rendre `0` sans rien avoir fait. Le log propre du script est la
seule preuve ; le code retour n'est qu'un indice de lancement.

## Ne pas casser le reste en corrigeant

Réparer une tâche de nettoyage restée cassée peut déclencher l'action destructrice qu'elle n'a jamais
pu faire : des archives gardées par un correctif antérieur passent en quarantaine puis sont
supprimées. **Chiffrer la conséquence du correctif** (quels fichiers, quel délai, quelle preuve
d'audit) et la soumettre à validation avant d'appliquer — un correctif peut être plus dangereux que
la panne qu'il répare.
