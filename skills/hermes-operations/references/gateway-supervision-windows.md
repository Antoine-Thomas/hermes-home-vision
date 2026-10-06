<!-- Extrait de hermes-operations/SKILL.md, lignes 589-738 (compression A.3 du 2026-10-06) — contenu verbatim. -->

## Supervision du gateway sur Windows (le trou de surveillance)

**Un gateway orphelin sans répétition peut mourir silencieusement pendant des heures.** Toute tâche
gateway doit porter `StartWhenAvailable` + **répétition courte (PT15M)** + `MultipleInstances=IgnoreNew`.
Sans répétition, la tâche ne tire qu'au logon : si le processus meurt sans déconnexion de session
(aucun 7001/7002), rien ne le relève — un bot muet peut passer un jour entier sans alerte.

**La répétition est sûre : ne pas craindre les doublons.** `gateway/run.py::_start_gateway_claim_pid_file()`
est le verrou autoritatif — un second `gateway run` échoue au claim (`Another gateway instance (PID N)
started during our startup` / `Gateway runtime lock is already held by another instance`) et sort sans
double-run. Le verrou est un fichier OS (msvcrt/flock) : « the OS releases it if the process dies »,
donc après une mort brutale le tick suivant reprend la main. ⚠ Le préflight CLI
`_guard_existing_gateway_process_conflict` est **court-circuité** par `HERMES_SUPERVISED_CHILD=1` (posé
par le VBS) — raisonner sur le verrou runtime, pas sur ce préflight.

**Vérifier PT15M sur le VBS avant de l'armer** : `Hermes_Gateway.vbs` n'est PAS idempotent (aucun test
« 20200 écoute » contrairement au VBS du proxy NIM). C'est le verrou runtime qui protège, pas le VBS.

**Script source de vérité : `scripts/creer_tache_gateway.ps1`** (`-DryRun` par défaut, `-Apply`,
`-TaskName`). Il repart du XML exporté et insère le `<TimeTrigger>` — principal, settings et action
restent identiques au bit près. Idempotent : si `<Interval>PT15M</Interval>` est présent, il ne fait rien.

**Diagnostic d'une mort « sans trace »** : une terminaison dure (TerminateProcess / fermeture de Job
Object) ne laisse rien dans `gateway.log`, rien dans `gateway-exit-diag.log`, rien dans WER ni dans le
journal Application. **Activer le journal des tâches est le seul moyen de dater la prochaine
occurrence** :

```powershell
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true    # activer (reversible)
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:false   # commande inverse
```

Il est **désactivé par défaut** sur ce parc : sans lui, un arrêt de tâche à une heure précise reste
introuvable (c'est ce qui a empêché de trancher sur l'arrêt du 17/09 à 13:42). Lecture :
`Get-WinEvent -LogName 'Microsoft-Windows-TaskScheduler/Operational'` (id 100/200 = tâche lancée,
102/103 = fin, 129/201 = action lancée/terminée) ; filtrer sur `$_.Properties[0].Value -like 'Hermes_*'`.

Autre témoin exploitable après coup : `gateway-shutdown-watchdog.log`. Un arrêt « propre » peut
quand même tuer le process en dur — le drain se coince (threads de fond), et après 240 s le watchdog
force l'exit (bypass des hooks `atexit`, d'où l'absence de trace), avec un dump de tous les threads
qui désigne le point de blocage exact.

**Surveillance active : `scripts/check_gateways.ps1`** (source de vérité, sa tâche
`Hermes_Gateway_HealthCheck` PT5M est créée par `-InstallTask -Apply`). Il relève la couverture que
la répétition PT15M ne donne pas : détection en ≤5 min, relevage explicite, alerte et journal
`logs/gateway-health.log`. Il teste que le PID est vivant **et** qu'il s'agit bien d'un process
`gateway run` (un PID recyclé ne compte pas), relève par `Start-ScheduledTask` puis recontrôle à
T+30 s, et n'alerte que sur **transition** d'état.

L'alerte `[profil] relevage ECHOUE (La tâche est désactivée.)` = la tâche planifiée du gateway est
**Disabled**. Réactiver naïvement (`Enable-ScheduledTask` puis `Start-ScheduledTask`) peut
**aggraver** : si des instances résiduelles pollent déjà le même bot, le gateway re-crash en boucle
« MORT/RELEVE » (Telegram 409 polling conflict) à chaque tick PT5M. Avant de réactiver, tuer les
résidus (`Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'profile <profil>' }`
→ `Stop-Process -Force`), puis trancher : réactiver UNE instance propre, OU laisser désactivé et
patcher `check_gateways.ps1` pour **ignorer** les tâches `Disabled` (traitée comme « volontairement
arrêtée », pas « morte » — sinon le healthcheck alerte `relevage ECHOUE` à chaque tick).

**Piège : ignorer une tâche `Disabled` ne stoppe PAS l'alerte « MORT detecte ».** Le contrôle `Disabled → skip` arrive APRÈS la génération de l'alerte de transition `[profil] gateway MORT detecte` ; l'état précédent du profil étant `disabled` (pas `down`), le test `$deja -ne 'down'` reste vrai et l'alerte repart à **chaque tick** PT5M. Pour exclure définitivement un profil (bot retiré du parc), passer `Toujours = $false` dans la liste `$Profils` : le `continue` de non-surveillance s'exécute AVANT la génération d'alerte. Désactiver la tâche seule ne suffit pas.

**Crash loop MORT/RELEVE = plusieurs instances du même gateway pollent le même jeton Telegram.**
La 409 « polling conflict — previous session still held open » signifie DEUX pollers sur le MÊME
token. Diagnostic sans divulguer les jetons : comparer les empreintes `sha256` des
`TELEGRAM_BOT_TOKEN` des profils concernés (default/watch/veille) pour confirmer des bots distincts ;
`getMe` (curl) pour le nom du bot ; `getUpdates?timeout=5` (curl) — s'il rend `{"ok":true}` alors
que le gateway est DOWN, le conflit est intermittent (instances concurrentes), pas un poller externe.

**Le test qui separe un conflit INTERNE d'un poller EXTERNE : gateway ARRETE, sonder les trois jetons a
la suite.** `hermes gateway stop`, laisser expirer le long-poll en cours (~1 min), puis `getUpdates`
sur `default`, `veille` puis `watch` : le jeton contendu rend **409** quand les deux autres rendent
**200** — donc un poller HORS de ce poste detient ce bot. Ecarter d'abord un residu local : un seul
process `gateway run` (`Get-CimInstance Win32_Process` filtre sur la ligne de commande) et une seule
connexion sortante vers Telegram (`Get-NetTCPConnection -State Established`, adresse du gateway). Un
409 reproductible sur plusieurs minutes, gateway arrete, n'est pas une session perimee qui expire.

**Un jeton présent dans un seul fichier du parc n'exclut PAS un second consommateur : l'inventaire porte
sur les processus et les sidecars, pas sur les `.env`.** Le concurrent peut être un script local
NON-Hermes rangé sous `data/` (boucle `getUpdates` PowerShell ou Python, jeton dans un `token.sec`
sidecar) avec sa propre tâche planifiée qui le relance — et deux fichiers peuvent porter le MÊME bot id
avec des secrets différents (l'un révoqué, l'autre vivant). Trois axes, à croiser : (a) les processus
dont la ligne de commande cite le script (`Get-CimInstance Win32_Process | Where-Object { $_.CommandLine
-like '*<script>*' }`), (b) leurs tâches (`Get-ScheduledTask` + `Get-ScheduledTaskInfo` — une répétition
courte relance un poller muet toutes les quelques minutes), (c) chaque fichier portant ce bot id,
`token.sec` et copies de rotation compris, trié par `getMe` (200 = vivant, 401 = révoqué). Le tell de ce
montage dans les logs du gateway est `Unrecognized slash command <cmd> from telegram` : le gateway a bien
mangé la mise à jour, et la commande appartient en réalité à l'autre consommateur — donc répondre
« encore utile ou vestige » pour cet autre consommateur est un choix à présenter à l'opérateur, pas une
réparation à faire seul.

**`hermes gateway restart` ne repare PAS un 409 dont la source est externe.** L'adaptateur du profil
retente 5 fois sur ~200 s (`Telegram polling conflict (n/5)` dans `logs/gateway-stdio.log`, adapter
`platforms__telegram__home_<hash>.adapter`), puis passe `fatal` ; entre deux echecs `gateway_state.json`
peut repasser a `connected`, donc **un `connected` qui flappe n'est pas un etat sain** — relire l'etat
plus de 200 s apres le demarrage et croiser avec les lignes de conflit avant d'annoncer « les 3 profils
UP ». Issue a proposer : retrouver l'autre consommateur du bot, ou revoquer le jeton (BotFather) et en
poser un neuf dans le `.env` du profil ; un `restart` supplementaire ne fait que rejouer le cycle.
Rapporter l'etat par plateforme (`default:telegram` OK / `watch:telegram` en conflit) plutot qu'un
« les 3 profils UP » global : `hermes gateway list` les annonce servis meme quand un adaptateur est mort.

**Trouver le process d'un profil : lire `gateway_state.json`, pas grepper la ligne de commande.** Le VBS du profil `veille` lance `gateway run` avec `HERMES_HOME` (variable d'env) et SANS `--profile veille` — donc `Get-CimInstance … -match 'profile veille'` ne trouve rien et fait conclure à tort « gateway down » alors qu'il tourne (PID vivant). Lire le PID dans le `gateway_state.json` du profil, pas le flag `--profile`. **Sous multiplexage, le fichier PAR PROFIL MENT** : seul le `gateway_state.json` RACINE fait foi — il porte le PID du process unique, `served_profiles` et une entree par profil et par plateforme (`default:telegram`, `veille:telegram`, `watch:telegram`) avec leur etat et leur `error_code`. `profiles/<nom>/gateway_state.json` reste figé sur le dernier etat standalone (`gateway_state: "stopped"`, adaptateurs `fatal`) et fait conclure a tort « le profil est mort » alors que `hermes gateway list` le rend « served by the default multiplexer ». Lire le racine d'abord ; l'autre ne sert qu'a dater l'epoque ou le profil tournait seul.

**Battement horaire** (ajouté le 17/09) : une ligne `[battement] <heures>h : N/M gateways up, X alerte(s) | default=up …`
est écrite **une fois par heure même quand tout va bien**, pour donner un historique de disponibilité
lisible (24 points/jour) et parsable par `scripts\verif_24h.ps1`. Les lignes par tick existaient déjà ;
c'est le résumé compact qui manquait. Sur ce journal, aucun accès visuel ne distingue « tout va bien »
de « rien ne tourne » sans un tel repère.

**Piège d'un marqueur d'idempotence dans un script périodique** : le script RÉÉCRIT son état à chaque
tick. Si le marqueur « déjà fait » (ici `_battement_heure`) n'est pas reporté dans le nouvel état, il
disparaît au tick suivant et le garde-fou se réarme tout seul — observe : deux lignes de battement
pour la même heure, la seconde écrite par le tick planifié qui suivait un run manuel. Tout marqueur
« dernière exécution » doit être re-lu puis réécrit :

```powershell
if ($dernierMarqueur -ne $valeurCourante) { …; $nouvelEtat['_marqueur'] = $valeurCourante }
else { $nouvelEtat['_marqueur'] = $dernierMarqueur }   # sans ce else, le marqueur est perdu
```

Vérifier le comportement en enchaînant **deux exécutions dans la même fenêtre** (attendu : une seule
ligne) — un seul run ne prouve rien, c'est le second qui révèle la perte du marqueur.

**Piège PowerShell à ne jamais introduire dans un script de surveillance** : `$pid` est une variable
**en lecture seule** (PID du process courant) — `$pid = ...` échoue avec « Impossible de remplacer la
variable PID, car elle est constante ou en lecture seule », et l'échec se produit en plein milieu de
la boucle. Nommer sa variable `$gwPid`.

**Ce qui reste exploitable** : `gateway-exit-diag.log` calcule la fenêtre de mort (la ligne `previous_unclean_exit`
au redémarrage suivant), et la comparaison des drapeaux de démarrage (`console_window_attached`,
`breakaway`) entre l'instance morte et la vivante.

**Mort au démarrage hors Job Object** : `hermes gateway start` lancé depuis un shell se fait tuer à la
fermeture de ce shell (#91675 — le CLI le diagnostique lui-même au redémarrage suivant). Relancer par
`schtasks /Run /TN Hermes_Gateway*`, jamais par `hermes gateway start`.

**Piège Python à ne jamais introduire dans un script de vivacité** : sur Windows `os.kill(pid, 0)`
**TUE** le processus cible (il appelle `TerminateProcess`, ce n'est pas une sonde comme sur POSIX).
Pour tester une liveness : `Get-Process -Id <pid>` (PowerShell) ou `psutil.pid_exists`.

## Gateway restart after update

After `hermes doctor` shows "A previous update pulled new code but did not restart running gateways" → run `hermes gateway restart`. This fixes mixed `sys.modules` (code and binary out of sync). The gateways keep serving stale modules until explicitly restarted.

## Gateway double-process is normal

`hermes gateway status` reports one PID but `Get-CimInstance Win32_Process` where CommandLine like '*gateway*' routinely shows 2: parent `...\.venv\Scripts\python.exe -m hermes_cli.main gateway run` (PPID = Task Scheduler) and child `...\.hermes-runtime\python\generation-...\python.exe -m hermes_cli.main gateway run` (PPID = parent). Do not treat as zombie — killing the child alone drops gateway (`No gateway process detected`). Only kill stale generations: CreationDate older than last `schtasks /Run /TN Hermes_Gateway` or PID not matching `hermes gateway status`. Verify with `ProcessId, ParentProcessId, CreationDate` table before any taskkill.

## Restart verification

After `hermes gateway restart` or `schtasks /Run /TN Hermes_Gateway`, wait 7-9s then check `hermes gateway status` and `Get-Content "$env:LOCALAPPDATA/hermes/logs/gateway.log" -Tail 25` for `telegram connected` / `polling healthy` / `set_my_commands OK`. Log tail is authoritative — status alone can show `No gateway process detected` while child is still warming (2s turn machinery). ESTOP check is `Test-Path "$env:LOCALAPPDATA/hermes/ESTOP"` — must be False for normal ops.

