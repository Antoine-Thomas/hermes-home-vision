# Hermes update — preflight en précaution (avant `hermes update`)

Séquence à exécuter AVANT un `hermes update` pour éviter les modules mixtes et la corruption state.db. Établie lors d'un update 0.21.2 → 0.21.3 sur Windows multi-profils.

## Précaution 1 — Multiplex multi-profils

L'update peut passer `gateway.multiplex_profiles` à `true` par défaut. Avec deux profils (default + watch), ça peut casser le multiplexage au boot.

```
hermes config set gateway.multiplex_profiles false
hermes config get gateway.multiplex_profiles   # -> false
```

Vérifier le YAML : la clé doit être sous `gateway:` (grep la section), pas sous un autre en-tête. Committer ce changement AVANT l'update.

## Précaution 2 — Snapshot final frais

Les snapshots auto pre_update datent de plusieurs heures ; copier une version fraîche. Sauvegarder dans un dépôt git versionné (ex. `Desktop/hermes_install/snapshot/`):

```
cd Desktop/hermes_install
mkdir -p snapshot
cp $LOCALAPPDATA/hermes/config.yaml snapshot/config.yaml
cp $LOCALAPPDATA/hermes/memories/MEMORY.md snapshot/MEMORY.md
cp $LOCALAPPDATA/hermes/memories/USER.md snapshot/USER.md
cp $LOCALAPPDATA/hermes/state.db snapshot/state.db
cp $LOCALAPPDATA/hermes/.env snapshot/.env
hermes skills list > snapshot/skills_fresh.txt
git add -A && git commit -m "Snapshot pré-update final — <date>"
```

Vérifier l'intégrité state.db avant le snapshot : `PRAGMA integrity_check` et `PRAGMA quick_check` doivent dire `ok`, et `SELECT COUNT(*) FROM messages` doit correspondre.

## Précaution 3 — Arrêter TOUS les writers

Un gateway actif pendant l'update → modules mixtes → risque de corruption state.db.

```
hermes gateway stop
hermes -p watch gateway stop
```

Vérifier qu'aucun processus ne tourne (attendu : vide) :

```
ps aux | grep -i hermes | grep -v grep
wmic process where "name='python.exe' or name='hermes.exe'" get ProcessId,CommandLine | grep -i hermes
```

(Le `wmic` dans bash nécessite des guillemets simples pour éviter l'interprétation PowerShell de `$_.CommandLine` — `$_.` de PowerShell dans une commande bash est interprété comme une variable shell vide.)

## Pendant / après

- Lancer `hermes update --plan` d'abord pour confirmer le type d'install (git/docker/nix) et qu'aucun service ne tourne.
- `hermes update` (sans `--yes`) capture la sortie dans un log.
- Contrôles : `hermes --version` (nouvelle version), `hermes doctor` (plus de mixed sys.modules, plus de commits behind), `hermes memory status`, `hermes skills list`, `PRAGMA integrity_check`/`quick_check`, diff config.yaml vs snapshot (seuls les commentaires de migration doivent différer).
- Réindexer le RAG après : `cd $LOCALAPPDATA/hermes/data/rag && ./venv/Scripts/python.exe indexer.py` (peut prendre >3 min — lancer en arrière-plan avec notify).
- Relancer le serveur RAG (8200) : c'est un serveur **manuel uniquement** (aucune tâche planifiée ne le démarre). Vérifier l'écoute avec `curl http://127.0.0.1:8200/sante` — s'il est down après l'update, le redémarrer (voir ci-dessous).

## Pièges d'exécution Windows (post-update)

### Le gateway relancé par l'update meurt (Job Object Windows)
Après `hermes update`, le gateway relancé en cold-start est souvent tué à la fermeture du shell : diagnostic « PID died without a clean shutdown record » / « gateway restart could not be verified ». Récupérer par la tâche planifiée, PAS par `hermes gateway start` (elle restera dans le shell mourant) :

```
schtasks /Run /TN Hermes_Gateway
```

Le profil watch peut avoir sa tâche **désactivée** (`Hermes_Gateway_watch` → « Désactivé »). La relancer alors via `hermes -p watch gateway start` directement. Vérifier les deux : `hermes gateway status` doit lister default ET watch.

### Lancer un serveur long-running sur Windows (git-bash)
- `setsid` **n'existe pas** sous git-bash MSYS → « command not found ».
- `terminal(background=true)` sur un serveur bloquant **renvoie quand même un timeout 420s** (il attend la fin) → ne pas lancer un serveur éternel ainsi.
- Idiome fiable : détacher via cmd :
  ```
  cd /c/Users/.../ && cmd //c "start /b venv\\Scripts\\python.exe serveur_rag.py > serveur_rag.log 2>&1"
  ```
  puis `sleep 6 && curl http://127.0.0.1:PORT/sante` pour vérifier l'écoute (le log peut être vide au début car le modèle d'embedding se charge au démarrage).

### Backend headless (`hermes serve`, port 9119) — par sa tâche planifiée, jamais en foreground
- **Ne jamais lancer `hermes serve` en foreground**, ni via `terminal(background=true)`: le backend ne rend pas la main, le terminal part en timeout 420s, et le Job Object Windows tue le processus à la fermeture du shell.
- Sa tâche utilisateur `Hermes - serve backend` (wscript + `Hermes_Serve.vbs`, mode 0 = sans fenêtre) est le lancement supporté :
  ```
  schtasks /Run /TN "Hermes - serve backend"
  ```
- **Sonder le port AVANT de relancer quoi que ce soit.** S'il répond, un backend tourne déjà : un `hermes serve` lancé à la main échoue alors avec `BACKEND_PORT_IN_USE port=9119`, ce qui est en soi la preuve qu'il est vivant. L'identification se fait sur la réponse de `/sante` — le backend headless répond `{"error":"Headless backend (hermes serve): web UI disabled — use 'hermes dashboard' for the browser UI."}`.

### Nettoyer les crashs / ports avant relance
- Après un lancement raté, vérifier d'ABORD si le port est déjà occupé par un serveur existant avant de relancer — sinon `BACKEND_PORT_IN_USE` (ex. le backend 9119 peut être occupé par la tâche planifiée). Un serveur déjà présent répond à son endpoint de santé spécifique (ex. backend headless → « web UI disabled ») — c'est le bon indicateur d'identification.
- Les `PRAGMA integrity_check` / `quick_check` sur state.db se font AVANT et APRÈS snapshot/update ; les deux doivent dire `ok`.
