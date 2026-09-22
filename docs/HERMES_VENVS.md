# Les deux venvs de l'installation Hermes — état, usages, procédure

Date : 2026-09-19 (2e passe, 11:40)
Machine : Windows 11, `C:\Users\searc`
Installation : `C:\Users\searc\AppData\Local\hermes\hermes-agent` (dépôt git, `main` @ `d4d9b76d8c`, Hermes 0.21.3)

## 0. Où on en est (à lire en premier)

| point | état |
|---|---|
| `venv` = venv de référence | **oui** — 175 paquets, dist-info 0.21.3, sur le PATH |
| Lanceurs persistants repointés sur `venv` | **fait** — gateways, tâches planifiées, shims PATH, **et le backend 9119** (`Hermes_Serve.vbs`, repointé le 19/09 à 11:30, sauvegarde `.bak.20260919`) |
| `.venv` (0.20.5) | **encore présent** — seul consommateur restant : la session CLI interactive ouverte à la main |
| Renommage `.venv` → `.venv.retired-0.20.5` | **non fait** — refusé par Windows tant que la session tourne (voir §6). Script prêt : `docs\retirer_venv_legacy.ps1` (+ `.cmd` pour double-clic) |
| Conservation prévue | garder `.venv.retired-0.20.5` **30 jours** (jusqu'au ~2026-10-19), puis supprimer si aucun besoin |
| Paquets à installer dans `venv` | **aucun** (voir §3, verdict des 4 paquets) |

## 1. Les deux environnements

| | `venv` | `.venv` |
|---|---|---|
| Chemin | `hermes-agent\venv` | `hermes-agent\.venv` |
| Rôle | **venv officiel**, installé et maintenu par l'installeur / `hermes update` | reste d'une installation précédente (Hermes **0.20.5**) |
| Métadonnées `hermes_agent-*.dist-info` | **0.21.3** | **0.20.5** (périmées) |
| Code exécuté | code du dépôt (partagé) | code du dépôt (partagé) |
| Paquets installés | 175 | 135 |
| Python | 3.11.16 | 3.11.16 |
| `pyvenv.cfg` → `home` | `.hermes-runtime\python\generation-1787488254-…` | `.hermes-runtime\python\generation-1787325413-…` (génération antérieure) |
| Sur le PATH | oui (préfixé par Hermes dans ses shells) | non |

**Décision (Option A, la plus sûre)** : `venv` est le venv de référence. Aucune synchro `pip` n'a été
faite vers `.venv` : elle casserait la session en cours (réécriture de `site-packages` sous un
interpréteur vivant) et **rétrograderait torch** de 2.14.0 vers 2.4.1+cu118. `.venv` n'est donc pas
« mis à jour » : il est mis à la retraite (§6).

## 2. Qui utilise quoi (preuves, pas déductions)

**Session CLI en cours — `.venv`**
- `Get-CimInstance Win32_Process` : `"…\hermes-agent\.venv\Scripts\hermes.exe"` (PID 4204), plus son
  python (18504) et le worker runtime (4516). Lancée **à la main** depuis ce chemin.

**Commandes `hermes` lancées depuis un shell — `venv`**
- `which -a hermes` → `…\hermes-agent\venv\Scripts\hermes` en premier, `…\hermes\bin\hermes` ensuite.
- Chaînes embarquées dans les lanceurs (trampoline `uv`) :
  - `hermes\bin\hermes.exe` → shebang `#!C:\Users\searc\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`
  - `hermes\bin\hermes-acp.exe` → même shebang
  - `venv\Scripts\hermes.exe` → shebang relatif `#!python.exe` (donc le python de `venv`)
- `hermes\bin` est dans le PATH **utilisateur** : la voie « officielle » (Win+R, explorateur) aboutit
  elle aussi à `venv`.
- Contrôle de bout en bout : `bin\hermes.exe --version` → 0.21.3 / `d4d9b76d` ; `bin\hermes.exe skills list` → OK.

**Gateways (`default` + `veille`) — `venv`**
- `gateway-service\Hermes_Gateway.vbs` : `VIRTUAL_ENV=…\hermes-agent\venv` et
  `…\venv\Scripts\python.exe -m hermes_cli.main gateway run`. Idem `Hermes_Gateway_veille.vbs`.
- Vérifié en direct : les processus gateway parents sont bien `venv\Scripts\python.exe`.

**Tâches planifiées**
| tâche | interpréteur | état |
|---|---|---|
| `Hermes - desaturer memoire` | `hermes-agent\venv\Scripts\python.exe` | OK |
| `Hermes - Reindex RAG` | `data\rag\venv\Scripts\python.exe` (venv **distinct**, dédié au RAG) | OK |
| `Hermes - serve backend` | **`venv`** depuis le 19/09 11:30 (pointait sur `.venv`) | OK, 9119 répond 200 |
| `Hermes_Gateway`, `Hermes_Gateway_veille` | `venv` (via les `.vbs`) | OK |
| `Hermes_Gateway_watch` | désactivée (profil watch) | — |

**Backend 9119 (`hermes serve`) — repointage vérifié le 19/09**
- Avant : `"…\hermes-agent\.venv\Scripts\python.exe" -m hermes_cli.main serve` (PID 8556) →
  worker runtime PID 7728 qui écoutait sur 9119.
- Correction : `Hermes_Serve.vbs` (2 copies : `gateway-service\` et `docs\hermes\`) repointé sur
  `…\hermes-agent\venv\Scripts\python.exe`, sauvegardes `.bak.20260919`.
- Après redémarrage de la tâche : `"…\hermes-agent\venv\Scripts\python.exe" -m hermes_cli.main serve`
  (PID 10592) → worker PID 5752 qui écoute sur 9119, **HTTP 200**. Plus aucun processus `serve`
  n'utilise `.venv`.

## 3. Paquets critiques et verdict des 4 paquets « manquants »

| paquet | `venv` | `.venv` | écart |
|---|---|---|---|
| hermes (version du code) | 0.21.3 | 0.21.3 | identique (code partagé par le dépôt) |
| `hermes_agent` (dist-info) | 0.21.3 | 0.20.5 | `.venv` a deux versions de retard |
| torch | 2.4.1+cu118 | **2.14.0** | majeur ; hors dépendances Hermes (usage IA local) |
| pydantic | 2.13.4 | 2.13.4 | identique |
| anyio | 4.15.1 | 4.12.1 | `.venv` plus vieux |
| click | 8.5.0 | 8.4.2 | `.venv` plus vieux |
| typer | absent | 0.27.2 | non requis par Hermes |
| rich | 14.3.3 | 14.3.3 | identique |
| prompt-toolkit | 3.0.52 | 3.0.52 | identique |

**Aucune dépendance obligatoire manquante** : les 5 dépendances du code courant (`openai`, `certifi`,
`python-dotenv`, `fire`, `httpx`) sont installées dans **les deux** venvs. C'est un décalage de
**versions**, pas un trou : aucun risque d'`ImportError` sur les imports obligatoires.

Verdict des 4 paquets présents seulement dans `.venv` (vérifié le 19/09, usage réel des scripts) :

| paquet | verdict | preuve |
|---|---|---|
| `faiss-cpu` | **à ne PAS installer dans `venv`** | le RAG tourne dans `data\rag\venv`, qui a `faiss 1.15.0` (import vérifié) ; la tâche « Hermes - Reindex RAG » et `serveur_rag.py` utilisent ce venv-là |
| `huggingface_hub` | déjà présent dans `venv` | `venv\Scripts\python.exe -c "import huggingface_hub"` → 1.24.0 |
| `google-api-core` | déjà présent dans `venv` | → 2.36.0 (`googleapiclient` aussi) |
| `joblib` | **inutilisé** | aucun `import joblib` dans les `.py`/`.ps1`/`.vbs` du home Hermes hors venvs |

Les scripts qui importent `faiss` sont `data\rag\chercher.py`, `data\rag\indexer.py` et leurs copies
`docs\siyuan\*.py` — tous exécutés par `data\rag\venv`. Rien à ajouter à `venv`.

## 4. Ce que la mise à jour change (et ne change pas)

`hermes update` fait un `git pull` **partagé** par les deux venvs et réinstalle les dépendances dans
**`venv` uniquement**. Après une mise à jour, le code est donc identique partout mais seul `venv` a
des dépendances alignées sur la version du jour.

## 5. Procédure — mise à jour de `venv` (voie normale)

1. `cd /c/Windows/System32`
2. Arrêter le backend serve s'il tourne (sinon l'updater s'arrête sur « Another hermes.exe is running ») :
   `taskkill /PID <pid du "…\venv\Scripts\python.exe" -m hermes_cli.main serve> /T /F`
3. `hermes update --plan` (lecture seule) puis `hermes update -y`
4. Relancer le backend : `schtasks /Run /TN "Hermes - serve backend"` puis vérifier
   `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/` → 200
5. `hermes --version` puis `hermes doctor` — attendu : `Version files consistent (0.21.3)`

`.venv` n'est plus à maintenir : il est en cours de retrait (§6). Si un jour il fallait le garder comme
venv d'outillage local, la seule synchro acceptable est
`…\.venv\Scripts\python.exe -m pip install -e "C:/Users/searc/AppData/Local/hermes/hermes-agent"`
et **jamais** `pip install -r` depuis le freeze de `venv` (rétrogradation torch).

## 6. Mise à la retraite de `.venv` — pourquoi c'est différé, et comment finir

**Tentative faite le 19/09 à 11:38, depuis la session en cours : refusée par Windows.**

```
RENOMMAGE: ECHEC -> System.IO.IOException
message: L'accès au chemin d'accès 'C:\Users\searc\AppData\Local\hermes\hermes-agent\.venv' est refusé.
```

Cause : la session CLI tourne **dans** `.venv` (PID 4204 → 18504 → 4516) et ces processus tiennent des
fichiers ouverts dans le dossier ; Windows interdit alors de renommer le dossier. Le backend 9119, qui
tenait lui aussi `.venv`, a lui été **repointé et redémarré sur `venv`** — il ne bloque plus.

**Reste à faire, hors session Hermes** (l'agent ne peut pas fermer sa propre session) :

```powershell
# depuis un PowerShell propre (aucune session Hermes ouverte)
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\searc\AppData\Local\hermes\docs\retirer_venv_legacy.ps1"
# ou double-clic sur docs\retirer_venv_legacy.cmd
```

Le script : refuse de tourner si un processus utilise encore `.venv` (et le dit), renomme de façon
réversible, puis contrôle `hermes --version`, le shim `bin\hermes.exe --version`, `hermes doctor`,
`hermes skills list` et le 9119. Journal : `docs\retirer_venv_legacy.log`.

**Rollback** (à tout moment, aussi longtemps que le dossier existe) :
`Rename-Item "…\hermes-agent\.venv.retired-0.20.5" ".venv"`

**Rétention** : garder `.venv.retired-0.20.5` 30 jours (jusqu'au ~2026-10-19). Si entre-temps un script
local a besoin de `torch 2.14.0` ou de `faiss-cpu`, préférez recréer un venv dédié plutôt que de
ressusciter celui-ci.

## 7. Commandes de diagnostic réutilisables

```bash
REPO="$LOCALAPPDATA/hermes/hermes-agent"
# quel python utilise la session en cours ?
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='hermes.exe'\" | Select-Object -ExpandProperty CommandLine"
# TOUS les processus qui utilisent .venv (prealable obligatoire au renommage)
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { \$_.CommandLine -like '*hermes-agent\.venv*' } | ForEach-Object { \$_.ProcessId.ToString() + ' ' + \$_.Name }"
# quel python cible un lanceur ?
python -c "import re,sys;d=open(sys.argv[1],'rb').read();print([s.decode() for s in re.findall(rb'[\x20-\x7e]{8,}',d) if b'python.exe' in s or b'hermes_cli' in s])" "$LOCALAPPDATA/hermes/bin/hermes.exe"
# qui ecoute sur un port, et avec quel python
powershell -NoProfile -Command "(Get-NetTCPConnection -LocalPort 9119 -State Listen).OwningProcess"
# comparaison des deux venvs
"$REPO/venv/Scripts/python.exe"  -m pip freeze | sort > "$LOCALAPPDATA/Temp/a.txt"
"$REPO/.venv/Scripts/python.exe" -m pip freeze | sort > "$LOCALAPPDATA/Temp/b.txt"
diff "$LOCALAPPDATA/Temp/a.txt" "$LOCALAPPDATA/Temp/b.txt"
```
