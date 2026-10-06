---
name: windows-background-services
description: "Use when un service doit tourner sans fenetre sous Windows."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, services, taches-planifiees, headless, vbs]
    category: devops
---

# Services Windows en arriere-plan

Faire tourner un programme en permanence sous Windows (noyau de base de connaissances, backend
d'agent, serveur local, proxy) : demarrage a l'ouverture de session, **aucune fenetre**, survit a la
fermeture de la session qui l'a lance.

## When to Use

- Un service doit demarrer tout seul et ne rien afficher (une console qui traine dans la barre des
  taches est un defaut, pas un detail).
- Une tache planifiee existe deja mais la fenetre reste visible, ou le service meurt quand la
  session qui l'a lance se termine.
- On veut verifier qu'un service tourne VRAIMENT (et non que sa tache dit « Ready »).

Gabarits complets (`.vbs`, `.ps1`, controles) : `references/services-arriere-plan.md`.

## Regles

1. **Un `.cmd` ne cache rien.** `start /min` minimise, il ne cache pas ; et un `.vbs` qui se contente
   d'appeler ce `.cmd` ne masque que la console DU `.cmd`, pas celle qu'il cree ensuite pour la cible.
   Lancer la cible **directement** en mode cache : `sh.Run """<exe>"" <args>", 0, False`.
2. **Prouver l'invisibilite par la mesure.** Enumerer les fenetres du processus et tester
   `IsWindowVisible` (`EnumWindows` + `GetWindowThreadProcessId` via `Add-Type`). Un
   `MainWindowHandle` non nul ne prouve rien : une console cachee garde un handle.
3. **Fixer le dossier de travail** (`sh.CurrentDirectory` en VBS, `-WorkingDirectory` pour la tache) :
   beaucoup de programmes ecrivent leur journal dans leur dossier courant, et un journal parti
   ailleurs fait croire a une panne.
4. **Garde-fou de port** dans le lanceur : tester le port avant de demarrer, sinon une relance de la
   tache cree un second processus sur la meme ressource. `MultipleInstances IgnoreNew` double la
   protection.
5. **Ecrire un `.ps1` et l'appeler par `-File`** pour enregistrer la tache des qu'il y a des `$env:`
   ou des guillemets imbriques : en ligne a travers bash, les variables sont mangees et
   `Register-ScheduledTask` echoue. `.ps1` et `.vbs` en **ASCII pur** (PowerShell 5.1 lit l'UTF-8
   sans BOM comme de l'ANSI).
6. **`-ExecutionTimeLimit ([TimeSpan]::Zero)`** : sans lui, le planificateur arrete le service au
   bout de quelques jours — panne silencieuse, impossible a relier a la tache.
7. **Verifier par les faits** : `State=Ready` ne prouve rien. Controles = `LastTaskResult`, processus
   vivant, port en ecoute. Une commande `status` du programme peut ne rien voir (fichier de PID
   absent selon le mode de lancement) : le processus et le port sont la verite.
8. **Reprendre la forme de lancement deja utilisee** par les autres services de la machine
   (`%LOCALAPPDATA%\hermes\gateway-service\*.vbs` : `HERMES_HOME`, `VIRTUAL_ENV`, `PYTHONPATH`,
   `python.exe -m ...`) plutot que d'inventer un chemin de lanceur — le `.cmd` ou le binaire suppose
   peut ne pas exister.
9. **Un service deja installe ne se reinstalle pas a l'aveugle** : verifier l'existant d'abord, une
   reinstallation pouvant interrompre un service en production.

## Pitfalls

- Conclure « aucune fenetre » parce que le script utilise le mode 0 : mesure.
- Chercher un journal la ou le service ne l'ecrit plus apres un changement de mode de lancement.
- Croire une tache sur son etat : declencher pour de vrai (`Start-ScheduledTask`) et controler.

## Verification

```powershell
$i = Get-ScheduledTaskInfo -TaskName "<nom>"; $i.LastTaskResult; $i.LastRunTime
$p = Get-CimInstance Win32_Process -Filter "name='python.exe'" | Where-Object { $_.CommandLine -like '*<motif>*' }
Get-Process -Id $p.ProcessId | Select-Object Id, MainWindowHandle
netstat -ano | grep LISTENING | grep " <PID>$"
```
