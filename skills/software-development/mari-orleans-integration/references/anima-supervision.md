# Supervision ANIMA — branchement vers MARI

ANIMA (script de supervision Hermes, tâche « Hermes - Health Architecture ») publie un fichier d'état JSON que le watcher consomme et transforme en signaux MARI. C'est le canal de branchement réel d'une alerte ANIMA → porte MARI.

## Format du state file

- Chemin réel : `C:/Users/<user>/AppData/Local/hermes/data/route_ia_fix/health_anima_state.json` (PAS `journal/health_anima_state.json` qui n'existe pas).
- Dict JSON à 2 niveaux : clé = composant (gateway, profils, omniroute, nim_proxy, ollama, rag, siyuan, laya, jev, wazuh, cron, reindex, memoire, couts, fallback), valeur = objet `{last_state, failure_streak, last_check, last_success}`.
- `last_state` ∈ {READY, DEGRADED, FAILED} — une transition = last_state passe de READY/DEGRADED → FAILED.
- ANIMA RÉÉCRIT ce fichier lui-même toutes les ~15 min (tâche planifiée) : ne jamais s'étonner de voir des champs changer hors simulation (ex. jev streak 17→18 pendant un test) — c'est l'écriture naturelle d'ANIMA, pas une fuite du test.

## Watcher (anima_watcher.py, Python pur urllib)

- Cycle 30 s : lit le state file, garde `last_state[composant]` en mémoire, n'émet RIEN au 1er passage (baseline).
- Sur transition READY/DEGRADED → FAILED : `POST /fire {"fireId":"anima-<composant>-fail","sourceId":"anima-watcher"}`.
- Kill-switch : si `C:/mari-poc/DISABLE` existe → log `DISABLED`, aucune émission.
- Log dans `C:/mari-poc/journal/watcher.log`.
- Mode `--dry-run` par défaut : log des cycles sans POST — la logique de détection se valide en dry-run AVANT le mode réel.

## Protocole de test simulé (transition artificielle)

1. **Vider** `remediation/` et `watcher.log` ; démarrer le watcher ; attendre 1-2 cycles (baseline capturée = READY).
2. Simuler la 1re transition : écrire FAILED sur le composant A dans le state file, attendre 1 cycle → watcher POST `anima-A-fail`.
3. Simuler la 2e transition : écrire FAILED sur le composant B **à moins de la fenêtre ActiveWindowInterval** après A (ex. 10 s < 60 s) → porte AND déclenche → 1 fichier remediation.
4. **Restaurer immédiatement** les composants simulés à leurs valeurs d'origine (streak, last_state, last_check) — obligation utilisateur. La restauration ne couvre que les champs touchés ; les autres champs dérivent naturellement.

Ordre obligatoire : capturer la BASELINE d'abord (watcher démarré), simuler PENDANT le run. Modifier le fichier AVANT de démarrer prend FAILED comme baseline → 0 transition détectée (pas un bug du watcher).

## Piège silo inactif (vu en test réel)

Le bridge doit être FRAIS (< 15 min) pendant le test watcher complet : un silo inactif > 15 min voit ses grains collectés (CollectionAge) et les POST rendent 200 mais sont avalés — le watcher a pourtant bien détecté et émis. Redémarrer le bridge avant le run, et vérifier le déclenchement par `grep -c "Start sequence" bridge.log`, pas par le HTTP 200.

## Processus résiduels

Vérifier AVANT de lancer un watcher qu'aucun n'est déjà actif (deux écrivains sur le même log = cycles interlacés) : `powershell -File C:/mari-poc/journal/check_watcher.ps1`, ou `Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*anima_watcher*' }`. Un `taskkill /PID <wrapper>` (PID rendu par background=true) tue le wrapper bash, pas le child python — tuer tous les PIDs python matchant la CommandLine.
