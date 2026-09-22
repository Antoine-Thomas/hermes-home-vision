---
name: windows-ops
description: "Operations Windows: GPU Docker WSL2, tuning, fenetres console qui flashaient (taches planifiees)."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [windows, docker, gpu, wsl2]
    category: devops
    created: "2026-09-10"
    umbrella_of: [docker-gpu-windows]
    notes: "windows-performance-tuning (protege, 42l) et windows-system-backup (hors devops, 37l) non inclus — notes seulement"
---

# Windows Ops

Operations Windows DevOps : GPU Docker et systeme.

## When to Use

- Lancer des conteneurs GPU sur Windows (Docker Desktop + WSL2)
- Besoin de `wsl --update`, `nvidia-smi`, runtime nvidia
- Une fenetre console apparait/clignote periodiquement (tache planifiee) — voir
  "Fenetre console qui flashe"

## Docker GPU — resume

- Prerequis WSL2, driver NVIDIA, Docker Desktop.
- Verification `docker run --gpus all nvidia/cuda nvidia-smi`.
- Pieges : WSL kernel, passthrough, toolkit.

Voir `references/docker-gpu-windows.md` (108l).

## Fenetre console qui flashe (tache planifiee)

### Diagnostic

Une fenetre console qui apparait brievement malgre `-WindowStyle Hidden` n'est PAS
un probleme de flag : c'est le **binaire** qui est en cause. Un exe MSIX (pwsh 7
`WindowsApps`, Windows Terminal) n'ouvre pas un conhost masque mais est remis par
MSIX au broker `WindowsTerminal.exe`, qui affiche une fenetre. Consequence : la
fenetre est visible meme avec `style 0`, `-WindowStyle Hidden`, ou
`CreateNoWindow`. Verifier le binaire de l'action, jamais le flag.
Signature observee : `WindowsTerminal.exe` classe `CASCADIA_HOSTING_WINDOW_CLASS`
+ `pwsh.exe` classe `PseudoConsoleWindow`, parent de l'action = `svchost.exe`
(Planificateur de taches).

### Confirmation (mesurer, pas supposer)

1. Watcher `EnumWindows` toutes les 50 ms (`IsWindowVisible` + exe + classe +
titre), ecrit un CSV : identifie la fenetre et son PID.
2. Diff de processus toutes les 250 ms : la chaine parent/enfant montre qui lance
   quoi (ex. `svchost` -> `wscript.exe` -> `pwsh.exe` -> `conhost.exe`).
3. Event Viewer `Microsoft-Windows-TaskScheduler/Operational` : **event 129**
(demarrage d'instance) et **200** (action lancee) ; le nom d'instance donne le
binaire reellement lance ; `Get-ScheduledTaskInfo` -> `LastTaskResult = 0`
confirme le succes. Filtrer en PowerShell puis `Out-File -Encoding utf8` : la
sortie de `schtasks` est en UTF-16 et `grep` la voit comme binaire.
4. Controle positif obligatoire avant de conclure : declencher l'action d'origine
(`schtasks /run /tn "X"`) et verifier que la fenetre est bien capturee ; sinon
l'absence de fenetre ne prouve rien.

Piege du harnais : `Invoke-CimMethod Win32_Process Create` ne resout pas les
chemins MSIX (`pwsh.exe` -> ReturnValue 8) ; utiliser `wscript.exe` (System32)
ou un chemin complet.

### Correctif

Wrapper VBS (un fichier, convention `hermes\scripts\hidden_<Tache>.vbs`) :

```vbs
Set sh = CreateObject("WScript.Shell")
sh.Run "pwsh.exe -NoProfile -WindowStyle Hidden -File C:\chemin\script.ps1", 0, False
```

puis action de la tache = `wscript.exe` avec arguments
`//B //Nologo "C:\...\hidden_<Tache>.vbs"`. `wscript.exe` est un exe System32
(pas de broker MSIX) et `sh.Run(..., 0, ...)` masque l'enfant : prouve muet sur
pwsh 7, cmd et python. Seul le bloc `<Exec>` change ; triggers, RunAs et
intervalle restent intacts.

Application : exporter `xml_before`, editer le `<Exec>`, ecrire en UTF-16 (avec BOM,
line endings `\r\n`) et `schtasks /create /tn "X" /xml <fichier> /f`.

### Piege a ne pas perdre de temps dessus

`schtasks /change /tn "X" /hidden` **n'existe pas** (`/change` n'accepte pas
`/hidden`). Le flag vit dans `<Settings><Hidden>true</Hidden>` (via
`Set-ScheduledTask` ou reimport XML) et il est purement **cosmetique** : il masque
la tache dans l'UI, pas la fenetre.

### Verification

Laisser tourner >= 15 min (watcher de fenetres continu) et confirmer : 0 fenetre,
un event 200 par tick, `LastTaskResult = 0`, process cible toujours vivant. Test
fort : tuer le process cible et verifier qu'un tick le relance **sans fenetre**.

### Surveillance de la cible

Masquer la fenetre ne suffit pas : la cible peut mourir sans bruit. Exemple en place :
`%LOCALAPPDATA%\hermes\scripts\check_gateways.ps1` (lance par `Hermes_Gateway_HealthCheck`,
PT5M) surveille aussi le process du bot de surveillance et alerte sur Telegram **sur
transition uniquement** (une alerte a la mort, une au retour, jamais une par tick).

### Rollback

```bash
schtasks /create /tn "X" /xml "C:\...\xml_before\X.xml" /f
```

puis supprimer le wrapper VBS. L'action d'origine revient (avec la fenetre).

## Skills lies non inclus

- `windows-performance-tuning` — protege (2026-09-03, 42l), reste independant
- `windows-system-backup` — hors devops (37l, `skills/windows-system-backup`), note seulement

## References

- `references/docker-gpu-windows.md` — procedure GPU Docker Windows
