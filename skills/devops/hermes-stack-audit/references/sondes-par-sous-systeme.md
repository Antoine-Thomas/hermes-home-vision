# Sondes par sous-systeme (verifiees)

Commandes reellement utilisees lors d'un audit complet, et emplacements d'etat correspondants.
Chargement des variables de `%LOCALAPPDATA%\hermes\.env` avant toute sonde qui lit une cle :
`set -a; . "$LOCALAPPDATA/hermes/.env" 2>/dev/null; set +a`.

## Decisions locales (Laya / JEV)

- Self-test Laya — le venv Hermes suffit (`onnxruntime` + `tokenizers` y sont installes, aucun
  torch) :
  `"$LOCALAPPDATA/hermes/hermes-agent/venv/Scripts/python.exe"`
  `"$LOCALAPPDATA/hermes/skills/mlops/laya-onnx-windows/scripts/laya_onnx.py"`
  `--onnx-dir "$LOCALAPPDATA/hermes/data/laya-onnx/english" --self-test`
  Comparer les 4 sorties aux valeurs documentees dans la skill `laya-onnx-windows` : une sortie
  differente = export ou prompt divergent, pas un probleme de mesure.
- Comparaison Laya / JEV sur les memes questions : un script jetable qui importe les deux
  helpers (`laya_onnx.LayaOnnx` et `jev_helper.jev`) et fait tourner 3 passes par moteur.
  Le charger depuis `cache/scratch/` ; le helper JEV lit `OPENROUTER_API_KEY` dans l'environnement
  puis dans le `.env`, donc exporter le `.env` d'abord.
- JEV seul : `python "$LOCALAPPDATA/hermes/skills/typesafe-ai/scripts/jev_helper.py"` (3 primitives,
  latence et cout par appel affiches). C'est le seul verdict fiable sur sa disponibilite.

## OmniRoute

- Presence : `netstat -ano | grep -E ":20128\b"` ; identite du process :
  `powershell -NoProfile -Command "Get-Process -Id <pid> | Select-Object ProcessName,Path,StartTime"` ;
  relance automatique : tache planifiee `OmniRoute-Watchdog` (tick 5 min).
- Endpoints fiables (Bearer = `OMNIROUTE_API_KEY` de `~/.omniroute/.env`) : `GET /api/v1/models`,
  `POST /api/v1/chat/completions` avec `model=<bare name du combo>`. `/health` n'existe pas : voir
  le piege `curl` dans la SKILL.md.
- Usage : `~/.omniroute/storage.sqlite`, table `call_logs` (`timestamp, status, model,
  requested_model, provider, duration, tokens_*`). Detail par appel :
  `~/.omniroute/call_logs/<AAAA-MM-JJ>/*.json`. Log applicatif :
  `~/.omniroute/logs/application/app.log` (JSON, un objet par ligne). Le dossier `logs/` de
  Hermes ne contient AUCUN log OmniRoute.
- Lecture en `mode=ro` (le serveur tient la base) :
  `sqlite3.connect("file:<chemin>?mode=ro", uri=True)`. Requetes utiles : par provider
  (nombre, `AVG(duration)`, `MAX(duration)`, taux `status >= 400`) et distribution des statuts.
- **Piege de lecture** : le champ `provider` porte le premier segment du modele DEMANDE — quand un
  combo echoue, la ligne vaut `eco`, `nvidia-stack`, `eco-fast`… et non le fournisseur reel. Ne
  calculer les taux par fournisseur que sur les lignes dont `provider` est un vrai fournisseur,
  et lire les autres comme « appels visant ce combo ». Exclure `model='connection-test'` des
  classements par modele (sondes des boutons « Test connection »).
- Disjoncteurs et connexions : tables `domain_circuit_breakers`, `provider_connections`
  (colonnes `provider`, `is_active`, `test_status`, `last_error`), `api_keys` (`expires_at`,
  `last_used_at`).

## Wazuh / surveillance continue

- Hebergement : `docker ps -a` et `docker system df` ; ports attendus : 1514, 1515, 55000, 9200.
  Si le demon n'est pas joignable, tout le reste du sous-systeme est un constat d'arret — ne pas
  enchainer les sondes qui en dependent.
- Agent Windows : `/c/Program Files (x86)/ossec-agent/ossec.log` ; boucle
  `ERROR (1216) Unable to connect to '[127.0.0.1]:1514/tcp'` + `ERROR (1208) ... :1515` =
  manager absent. Comptage : `grep -c ERROR` / `grep -c WARNING`.
- Config Hermes : `data/security-monitoring/config.json` (seuils, timeouts, services, allowlists)
  et `data/security-monitoring/common.py` (`get_recent_alerts`, `wazuh_password`,
  `ollama_generate`, `send_telegram`). Voir la skill `security-monitoring` pour les pieges
  d'alerte.
- Taches planifiees `SecurityMonitoring-*` : lire l'action reelle et `LastTaskResult`
  (`Get-ScheduledTaskInfo`), pas seulement l'etat `Ready`.

## Hermes (gateway, memoire, skills)

- Etat : `logs/gateway-health.state.json` (profil par profil), `logs/gateway-health.log`,
  `logs/agent.log`, `logs/errors.log`, `logs/gateway.log` (chercher `UNCLEANLY` : une vie de
  gateway terminee sans chemin de sortie = SIGKILL/OOM, a rapporter).
- Taches : `Hermes_Gateway`, `Hermes_Gateway_HealthCheck` — `LastRunTime` + `LastTaskResult`
  donnent l'uptime reel mieux qu'un `Get-Service`.
- Permissions : `icacls` sur `.env` et `config.yaml`. Comparer a un fichier de secret sain
  (`~/.omniroute/.env`, qui n'a que Systeme / Administrateurs / l'utilisateur) : un groupe herite
  en `(RX)` sur le `.env` d'Hermes donne un acces lecture a toutes les cles API.
- Volumetrie : `state.db` et ses `.bak.*`, `logs/*.log.1`, nombre de `SKILL.md` (`find ... | wc -l`),
  memoire native (`wc -c memories/MEMORY.md memories/USER.md`) mise en face de
  `memory.memory_char_limit` de `config.yaml` — au-dessus de la limite, **tout ajout de memoire est
  refuse** et l'agent doit le savoir avant d'ecrire.
- Sessions : les compter avec `search_files` (`target='files'`, dossier `sessions/`) ; profils :
  `hermes profile list`.

## Windows

- Pare-feu : `Get-NetFirewallProfile` (attendu : Domain/Private/Public actifs). Defender :
  `Get-MpComputerStatus` (`AntivirusEnabled`, `RealTimeProtectionEnabled`, `IsTamperProtected`,
  `QuickScanAge`). MAJ : `Get-WindowsUpdate` (distinguer pilotes et correctifs de securite).
  Comptes : `Get-LocalUser` ; groupes : `Get-LocalGroup` ; taches non-Microsoft :
  `Get-ScheduledTask | Where-Object { $_.State -eq 'Ready' -and $_.TaskPath -notmatch 'Microsoft' }`.
  Detail des cmdlets et du durcissement : voir la skill `windows-ops`.
- Ports : `netstat -ano | grep -i listening` puis deduplication des adresses. Un service
  applicatif doit ecouter en `127.0.0.1` ; signaler tout ecoute en `0.0.0.0` (135/139/445 SMB,
  2179 Hyper-V, 5040/7680 Windows) et tout port LAN.
- Espace : `df -h /c` ; gros fichiers `find <dir> -maxdepth 2 -size +50M -printf "%s %p\n"` ;
  VHDX : `*.vhdx` sous `%LOCALAPPDATA%\Docker` et `%LOCALAPPDATA%\Packages` (un vhdx de
  plusieurs dizaines de Go ne se reduit que par compactage apres prune, pas par suppression).
