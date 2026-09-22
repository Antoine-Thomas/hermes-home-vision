# Audit « fenêtre console qui clignote » — 2026-09-20

Machine : OMATHS (Windows 11), utilisateur searc. Hermes v0.21.3.
Aucune tâche planifiée modifiée pendant cet audit (lecture seule + watchers).

## Méthode

1. `schtasks /query /fo CSV /v` (523 lignes) + dump structuré PowerShell
   (`Get-ScheduledTask` → 283 tâches uniques) : triggers, intervalles de répétition,
   état, Hidden, LogonType, actions.
2. Journal `Microsoft-Windows-TaskScheduler/Operational` (activé) : 2208 événements
   sur 3 h → 364 lancements ; événement 129 = process lancé (nom + PID).
3. Watchers temps réel (non intrusifs, lancés depuis Hermes) :
   - `watch_consoles.py` : EnumWindows toutes les 50 ms → toute fenêtre visible
     de classe ConsoleWindowClass / CASCADIA_HOSTING_WINDOW_CLASS / PseudoConsoleWindow.
   - `watch_procs_poll.ps1` : diff des PID toutes les 250 ms → toute création de
     process avec ligne de commande et parent.
   Artefacts : `%TEMP%\hermes-audit\` (tasks_struct.csv, tasksched_events.csv,
   console_watch.csv, proc_poll.csv, xml_before\*.xml).

## Preuve décisive (fenêtres visibles capturées sur 22 min)

```
20:11:49 WindowsTerminal.exe CASCADIA_HOSTING_WINDOW_CLASS "Terminal"
20:11:49 pwsh.exe            PseudoConsoleWindow
20:16:49 WindowsTerminal.exe CASCADIA_HOSTING_WINDOW_CLASS "Terminal"
20:16:49 pwsh.exe            PseudoConsoleWindow
20:21:49 WindowsTerminal.exe CASCADIA_HOSTING_WINDOW_CLASS "Terminal"
20:21:49 pwsh.exe            PseudoConsoleWindow
20:26:49 WindowsTerminal.exe CASCADIA_HOSTING_WINDOW_CLASS "Terminal"
20:26:49 pwsh.exe            PseudoConsoleWindow   (titre de l'onglet = chemin du pwsh du paquet MSIX)
```

4 occurrences consécutives à +5 min pile (`:49`), sur toute la durée d'observation
(20:07 → 20:29) : la cadence du flash est bien de 5 min, pas 15.

```

Corrélation (±1 s) avec les créations de process :

```
20:11:49.380 pwsh.exe pid=6172  parent=svchost  'pwsh.exe' -NoProfile -WindowStyle Hidden
                                               -File ...\surveillance\surveillance-launch.ps1
20:11:49.401 OpenConsole.exe    -Embedding      (hôte console de Windows Terminal)
20:11:49.411 WindowsTerminal.exe -Embedding
20:16:49.520 / 20:16:49.542 / 20:16:49.553  → même séquence
20:21:49.301 / 20:21:49.348 / 20:21:49.705  → même séquence
```

Le parent `svchost.exe` est le service Planificateur de tâches : le process vient
bien d'une tâche planifiée, et la ligne de commande est exactement celle de
`\SurveillanceBot`.

## Tableau d'identification

| Tâche | Commande | Intervalle | Utilité probable | Recommandation |
|---|---|---|---|---|
| **\SurveillanceBot** | `pwsh.exe -NoProfile -WindowStyle Hidden -File ...\surveillance\surveillance-launch.ps1` | PT5M + logon | ACTIF : relance le bot Telegram de surveillance (/watch, /photo, /video) s'il est mort. Déclencheur = `InteractiveToken` | **GARDER** — c'est la source du flash. Wrapper VBS (wscript, style 0) |
| \Hermes_Gateway_HealthCheck | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...\scripts\check_gateways.ps1` | PT5M + logon | ACTIF : détecteur de gateway mort (relève via `schtasks /Run`, alerte Telegram sur transition) | GARDER tel quel — aucune fenêtre visible observée (logon S4U + conhost) |
| \Hermes_Gateway | `wscript.exe //B //Nologo ...\gateway-service\Hermes_Gateway.vbs` | PT15M + logon | ACTIF : filet de sécurité PT15M du gateway default | GARDER tel quel (déjà invisible, prouvé) |
| \Hermes_Gateway_veille | `wscript.exe //B //Nologo ...\profiles\veille\gateway-service\Hermes_Gateway_veille.vbs` | PT15M + logon | ACTIF : idem pour le profil veille | GARDER tel quel (déjà invisible) |
| \Hermes_Gateway_watch | `wscript.exe //B //Nologo ...\profiles\watch\...` | PT15M | Désactivée (profil watch) | Ne pas toucher |
| \Hermes_NVIDIA_NIM_Proxy | `wscript.exe ...\data\nvidia\nvidia-nim-launch.vbs` | PT15M + logon | **ACTIF, pas un reliquat** : proxy NIM écoute `127.0.0.1:20200` (PID 11132), proxy.log écrit à 20:06, utilisé comme repli gratuit (`nvidia-stack`) | GARDER tel quel (déjà invisible) |
| \SecurityMonitoring-LogMonitor | `wscript.exe //B ...\scripts\hidden_SecurityMonitoring-LogMonitor.vbs` | PT2M | ACTIF (logs → Telegram) | GARDER (invisible) |
| \SecurityMonitoring-AlertBridge | `wscript.exe //B ...\hidden_SecurityMonitoring-AlertBridge.vbs` | PT5M | ACTIF | GARDER (invisible) |
| \SecurityMonitoring-PortMonitor | `wscript.exe //B ...\hidden_SecurityMonitoring-PortMonitor.vbs` | PT10M | ACTIF | GARDER (invisible) |
| \SecurityMonitoring-UpdateChecker | `wscript.exe //B ...\hidden_SecurityMonitoring-UpdateChecker.vbs` | quotidien 09:00 | ACTIF | GARDER (invisible) |
| \AudioGuardian-Watchdog | `wscript.exe ...\audio_guardian\guardian-watchdog.vbs` | PT5M (Hidden=True) | ACTIF | GARDER (invisible) |
| \OmniRoute-Watchdog | `wscript.exe //B ...\omniroute-launch.vbs` | PT5M | ACTIF | GARDER (invisible) |
| \cua-driver-serve | `powershell.exe -NoProfile -WindowStyle Hidden -NonInteractive -Command Start-Process ...` | au logon | ACTIF (driver computer_use) | GARDER — cadence = logon, hors sujet |
| \Hermes - Reindex RAG | `...\rag\venv\Scripts\python.exe ...\reindex_auto.py` | quotidien 03:00 | ACTIF | GARDER — flash possible à 03:00 (python.exe sans wrapper) |
| \SecurityAuditDeps | `pwsh.exe -NoProfile -NonInteractive ...` | quotidien 03:00 | ACTIF | GARDER — flash possible à 03:00 |
| \Hermes - check memory | `powershell -NoProfile ... check_memory.ps1` | quotidien 08:00 | ACTIF | GARDER |
| \Hermes - desaturer memoire | `...\venv\Scripts\python.exe ...\desaturer_memoire.py --auto` | hebdo dim. 04:00 | ACTIF | GARDER |
| \Hermes-PurgeReports | `powershell.exe -NoProfile -WindowStyle Hidden ...` | quotidien 02:00 | ACTIF (Hidden=True) | GARDER |
| \HermesGateway | `pwsh.exe -NoProfile -Command "hermes gateway start"` | logon | Désactivée | Ne pas toucher |
| \Microsoft\Windows\Hotpatch\Monitoring | `cmd.exe /d /c hpatchmonTask.cmd` | quotidien | Système Microsoft | **NE PAS TOUCHER** |
| \NVIDIA App SelfUpdate_{...} | `...\NVIDIA App\CEF\NVIDIA App.exe` | événementiel | Tiers NVIDIA (updater) | Hors sujet (aucune cadence 15 min) |
| \Adobe Acrobat Update Task, \AdobeGC*, \GoogleUpdater*, \GoogleUserPEH\*, \FluentCleaner, \CreateExplorerShellUnelevatedTask | divers | 1 h–6 h / variable | Tiers (Adobe, Google, Fluent) | Hors sujet |

## Corrélation Event Viewer

Seules trois familles se déclenchent à cadence infra-horaire côté scripts Hermes :

```
PT2M  \SecurityMonitoring-LogMonitor        (wscript //B)   → 0 fenêtre
PT5M  \SurveillanceBot                      (pwsh.exe)      → 3 fenêtres WT reproduites
PT5M  \Hermes_Gateway_HealthCheck           (powershell.exe)→ 0 fenêtre
PT5M  \AudioGuardian-Watchdog               (wscript)       → 0 fenêtre
PT5M  \OmniRoute-Watchdog                   (wscript)       → 0 fenêtre
PT5M  \SecurityMonitoring-AlertBridge       (wscript //B)   → 0 fenêtre
PT10M \SecurityMonitoring-PortMonitor       (wscript //B)   → 0 fenêtre
PT15M \Hermes_Gateway / _veille / _NVIDIA_NIM_Proxy (wscript) → 0 fenêtre
```

Aucun des trois déclenchements PT15M (20:14:02 NIM, 20:20:02 gateway) n'a produit
de fenêtre : l'hypothèse « tâche NVIDIA NIM toutes les 15 min » est écartée.

## Conclusion

La fenêtre qui clignote est **`\SurveillanceBot`** : la tâche lance `pwsh.exe`
(PowerShell 7, paquet WindowsApps) toutes les 5 minutes ; Windows 11 remet la
console de pwsh à **Windows Terminal** (`OpenConsole.exe -Embedding` +
`WindowsTerminal.exe -Embedding`), ce qui affiche brièvement une fenêtre
« Terminal » malgré `-WindowStyle Hidden`. Durée : le temps que
`surveillance-launch.ps1` détecte que le bot tourne déjà et sorte (~100 ms).

Cadence observée : **5 min** (20:11:49, 20:16:49, 20:21:49), pas 15 min.
Prochaines occurrences à vérifier : :xx:49.

`powershell.exe` (Windows PowerShell 5.1) et `python.exe` lancés par les autres
tâches obtiennent un `conhost.exe` classique masqué — aucune fenêtre visible.

## Cause racine exacte

`HKCU\Console\%%Startup` est **absent** et `HKCU\Console` n'a ni `DelegationConsole`
ni `DelegationTerminal` (donc « Laisser Windows décider », `ForceV2=1`).
Dans ce mode, Windows 11 remet la console des applications empaquetées MSIX à
Windows Terminal, et laisse les binaires Win32 classiques à `conhost.exe`.
`pwsh.exe` est fourni par le paquet MSIX `Microsoft.WindowsTerminal_1.24.11911.0`
→ d'où `OpenConsole.exe -Embedding` + `WindowsTerminal.exe -Embedding` (fenêtre)
tandis que `powershell.exe`, `python.exe`, `cmd.exe` obtiennent un `conhost.exe`
masqué. Ce n'est donc pas un réglage utilisateur à corriger, mais le choix de
binaire de la tâche.

## Correctif appliqué (option A validée → option B)

### A. Test à blanc, hors tâche (20:30 → 20:35)

Harnais non destructif : `Invoke-CimMethod Win32_Process Create` → parent = WmiPrvSE
(service, sans console), soit les mêmes conditions que le Planificateur.

| Tir | Voie utilisée | Résultat |
|---|---|---|
| Contrôle 1 | `schtasks /run /tn "\SurveillanceBot"` (action d'origine pwsh) | fenêtre Windows Terminal capturée à 20:33:35 → **contrôle positif OK** |
| Contrôle 2 | WMI → `pwsh.exe` direct | échec de création (ReturnValue=8 : WmiPrvSE ne résout pas le chemin MSIX) → non concluant |
| Test | WMI → `wscript.exe //B //Nologo test_vbs_pwsh.vbs` → `sh.Run ..., 0, False` | **aucune fenêtre** ; le marqueur VBS ET la preuve d'exécution écrite par pwsh lui-même (20:35:01) prouvent que pwsh 7 a tourné 8 s sous style 0 sans ouvrir de fenêtre |

Verdict A : **muet** → passage à l'option B.

### B. Correctif appliqué le 2026-09-20 à 20:35:43

Fichier créé : `C:\Users\searc\AppData\Local\hermes\scripts\hidden_SurveillanceBot.vbs`
(convention du dépôt, calquée sur `hidden_SecurityMonitoring-AlertBridge.vbs`) :

```vbs
Set sh = CreateObject("WScript.Shell")
sh.Run "pwsh.exe -NoProfile -WindowStyle Hidden -File C:\Users\searc\AppData\Local\hermes\data\surveillance\surveillance-launch.ps1", 0, False
```

Application : `schtasks /create /tn "\SurveillanceBot" /xml "<xml_after>" /f`
(diff de 2 lignes, `Triggers` / `Principals` / `Settings` identiques) :

```diff
     <Exec>
-      <Command>pwsh.exe</Command>
-      <Arguments>-NoProfile -WindowStyle Hidden -File "C:\...\surveillance\surveillance-launch.ps1"</Arguments>
+      <Command>wscript.exe</Command>
+      <Arguments>//B //Nologo "C:\...\hermes\scripts\hidden_SurveillanceBot.vbs"</Arguments>
     </Exec>
```

Inchangés et vérifiés après import : `UserId` (S-1-5-21-...-1001), `LogonType`
`InteractiveToken`, `<Interval>PT5M</Interval>`, `StartBoundary 2026-09-17T18:21:48+02:00`.

### Vérification mesurée (20:35:43 → 20:57:20)

- 6 déclenchements (tick manuel 20:35:58, puis 20:36:49, 20:41:49, 20:46:49,
  20:51:49, 20:56:49) : événements 107/129/200/201 tous OK,
  `LastTaskResult = 0`, `NextRunTime = 21:01:48`.
- Watcher de fenêtres (sondage 50 ms) sur toute la période : **0 fenêtre**
  (la seule fenêtre vue est celle de mon propre terminal Hermes).
- Watcher de process : chaîne `wscript.exe //B //Nologo ...hidden_SurveillanceBot.vbs`
  (parent `svchost`) → `pwsh.exe` (parent wscript) → `conhost.exe` masqué.
- Test de reprise réel : bot tué le 20:36:23 → relancé par le tick de 20:36:49
  (`pwsh` pid 18268, toujours vivant à 20:57), **sans aucune fenêtre**.

### Point d'honnêteté sur « alerte Telegram si le bot meurt »

Aucun chien de garde ne surveille le bot : `check_gateways.ps1` n'alerte que sur
les transitions d'état des *gateways*, et `log_monitor.py` / `port_monitor.py`
ne le suivent pas. Le seul signal Telegram est le message de démarrage du bot
lui-même (« 🤖 Bot de surveillance prêt. »), émis à chaque relance — donc présent
dans Telegram à 20:36:50. Une vraie alerte « bot mort » reste à ajouter.

### Note sur le masquage de tâche

`schtasks /change /tn "X" /hidden` **n'existe pas** (vérifié : /change
n'accepte ni /hidden ni équivalent). Le flag Hidden vit dans
`<Settings><Hidden>true</Hidden>` du XML → via `Set-ScheduledTask` (PowerShell)
ou export XML + `schtasks /create /f /xml`. De plus, « cacher » la tâche ne
supprime pas la fenêtre : c'est cosmétique (UI uniquement). Non appliqué ici
(changement volontairement limité à l'action).

## Rollback

- XML « avant » déjà sauvegardés : `%TEMP%\hermes-audit\xml_before\<Tache>.xml`
- Restauration exacte : `schtasks /create /tn "\<Tache>" /xml "<chemin>\<Tache>.xml" /f`
- Le wrapper VBS est un fichier neuf : suppression = retour à l'état actuel
  (l'action d'origine est dans l'XML avant).

## Alerte « bot SurveillanceBot mort » (ajoutee le 2026-09-20)

Besoin : aucun chien de garde ne surveillait le bot. Une mort n'aurait ete vue qu'au tick
suivant de la tache, sans aucun signal Telegram.

Methode : etendre `scripts\check_gateways.ps1` (deja lance toutes les 5 min par
`Hermes_Gateway_HealthCheck`) avec un second type de cible : les processus hors gateway.

- `$Processus` : `Cle='surveillance_bot'`, `Motif='surveillance\.ps1'`,
  `Tache='SurveillanceBot'`. Le motif cible le vrai bot
  (`pwsh -File ...\surveillance.ps1`), pas le wrapper wscript ephemere.
- Aucun relevage ici : le tick PT5M de `\SurveillanceBot` reste le seul relevage.
- Alerte sur TRANSITION uniquement, comme pour les gateways : `up -> down` = « MORT »,
  `down -> up` = « de nouveau VIVANT ». Etat stocke dans
  `logs\gateway-health.state.json`, cle `surveillance_bot`.
- `Send-Alerte` retourne desormais `ok message_id=<id> chat=<chat>` : le `message_id` est la
  preuve locale que Telegram a accepte l'alerte, et il est journalise.

### Test (kill reel du bot, 20/09/2026)

| Heure | Evenement | Resultat journalise |
|---|---|---|
| 21:19:45 | kill du bot (pid 18268) par `kill_bot.ps1` | `bot restant apres kill : 0` |
| 21:19:50 | healthcheck run1 | `[bot SurveillanceBot] ABSENT` + `[alerte] 1 alerte(s) -> ok message_id=71 chat=8956868107` |
| 21:19:53 | healthcheck run2 (bot toujours mort) | `[alerte] aucune transition d'etat, pas d'alerte` — pas de spam |
| 21:20:03 | tick AUTOMATIQUE de la tache (script modifie) | `[bot SurveillanceBot] ABSENT` + `aucune transition` — pas de 2e alerte |
| 21:21:49 | tick PT5M de `\SurveillanceBot` | bot relance : pid 8432, via le wrapper wscript, **sans fenetre** |
| 21:22:45 | healthcheck run3 | `[bot SurveillanceBot] OK pid=8432 vivant` + `[alerte] -> ok message_id=72` = « de nouveau VIVANT » |
| 21:25:03 | tick AUTOMATIQUE (bot vivant) | `OK pid=8432 vivant` + `aucune transition` |

Telegram : 2 messages seulement, emis par `@Hermesveille1_veille_bot` (bot veille essaye en
premier, cf. ordre des tokens) vers le chat 8956868107 — `message_id 71` (mort) puis `72`
(retour). La tache `Hermes_Gateway_HealthCheck` pointe sur le meme chemin de script : aucun
re-enregistrement n'a ete necessaire.

Diff : `docs\DIFF_check_gateways_alert_2026-09-20.diff` (+48 / -5 lignes).
Rollback : `scripts\check_gateways.ps1.reference_avant_alert` est la copie d'avant
modification — `Copy-Item <ce fichier> check_gateways.ps1 -Force`.
