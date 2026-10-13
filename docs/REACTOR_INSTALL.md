# Installation et relance — ANIMA Reactor 0.3

> Procédure de mise en service de la couche 5 (orchestration réactive).
> Valide pour la machine d'origine (`%LOCALAPPDATA%\hermes`, Windows 11 natif).
> Le bridge C# vit dans `C:/mari-poc/bridge` — **hors dépôt**, non committé.

## 1. Prérequis

| Dépendance | Version requise | Vérification |
|---|---|---|
| .NET SDK | 8.0.425 | `dotnet --list-sdks` |
| .NET Runtime | 8.0.31 (Microsoft.NETCore.App) | `dotnet --list-runtimes` |
| Python | >= 3.8 | `python --version` |
| Wazuh | WazuhSvc RUNNING | `sc query WazuhSvc` |
| POC MARI | `C:/mari-poc/` (bridge, mari, journal) | `ls C:/mari-poc/` |

Le SDK 8 est obligatoire pour compiler un TFM `net8.0` — le runtime seul ne
suffit pas (NU1100, targeting packs manquants), le SDK 10 ne le remplace pas.

## 2. Ordre de lancement

```
1. Vérifier l'état de départ   → scripts/check_reactor.ps1 (doit être sain)
2. Lancer le bridge            → cd C:/mari-poc/bridge && dotnet run -c Debug
3. Tester /status              → curl http://127.0.0.1:55553/status  → 200
4. Lancer le watcher           → python scripts/anima_watcher.py
5. Vérifier le journal         → C:/mari-poc/journal/watcher.log (Cycle 1)
```

### 2.1 Démarrage du bridge

```bash
cd C:/mari-poc/bridge
dotnet build -c Debug          # attendu : 0 erreur
dotnet run -c Debug            # attendu : "Now listening on: http://127.0.0.1:55553"
```

### 2.2 Démarrage du watcher

```bash
cd %LOCALAPPDATA%\hermes
python scripts/anima_watcher.py
```

Le watcher boucle toutes les 30 s. Premier cycle attendu dans le journal :

```
[HH:MM:SS] ANIMA Watcher started (real mode)
[HH:MM:SS] Cycle 1: <composants>=<état>, ...
```

## 3. Vérifications fonctionnelles (13 checks)

1. `dotnet --list-sdks` contient `8.0.425`
2. `dotnet --list-runtimes` contient `Microsoft.NETCore.App 8.0.31`
3. `python --version` >= 3.8
4. State file `%LOCALAPPDATA%\hermes\data\route_ia_fix\health_anima_state.json` :
   `_maj` < 15 min (sinon : signaler, ne PAS relancer la tâche de production)
5. `netstat -ano | findstr "55551 55552 55553"` → vide AVANT lancement
6. `netstat -ano | findstr "549\|550"` → vide (hors plage Wazuh)
7. `sc query WazuhSvc` → RUNNING
8. `cd C:/mari-poc/bridge && dotnet build -c Debug` → exit 0
9. Bridge lancé → `curl http://127.0.0.1:55553/status` → HTTP 200
10. `POST /fire anima-ollama-fail` + sleep 10 + `POST /fire anima-wazuh-fail` +
    sleep 10 → signaux émis, `total` incrémenté
11. Kill-switch : créer `C:/mari-poc/DISABLE` → watcher log `DISABLE file
    present` → supprimer `DISABLE`
12. `git status --short` dans `%LOCALAPPDATA%\hermes` → inchangé (aucun fichier
    runtime touché par la chaîne)
13. Arrêt propre : tuer le bridge → ports 55551/55552/55553 libres

Tout check NO-GO → **STOP**, ne pas lancer le watcher.

## 4. Kill-switch

```bash
# Arrêt immédiat du watcher (contrôle par fichier, sans signal OS)
touch C:/mari-poc/DISABLE        # le watcher journalise et sort au cycle suivant
rm    C:/mari-poc/DISABLE        # réarmement
```

Comportement vérifié (Phase 1, check 11) : fichier présent → log
`DISABLE file present — watcher exiting`, processus terminé.

## 5. Arrêt propre

1. Supprimer `C:/mari-poc/DISABLE` s'il existe.
2. Tuer le watcher (Ctrl+C ou kill du PID).
3. Tuer le bridge : `taskkill /pid <PID> /f` (approbation requise).
4. Vérifier : `netstat -ano | findstr "55551 55552 55553"` → vide.

## 6. Dépannage

| Symptôme | Cause probable | Action |
|---|---|---|
| `/status` refusé | Bridge non lancé ou port occupé | `check_reactor.ps1`, tuer silo fantôme |
| Log `state file vide` | Couche 3 coupée ou fichier absent | Vérifier `health_anima_state.json`, fraîcheur |
| Log `POST /fire error` | Bridge down, timeout 5 s | Relancer le bridge, re-vérifier `/status` |
| `DISABLE file present` | Kill-switch oublié | `rm C:/mari-poc/DISABLE` |
| Build NU1100 | SDK 8 absent | `winget install Microsoft.DotNet.SDK.8` |
| Build NU1608 (warning) | Version CodeAnalysis résolue 4.9.2 vs 4.8.0 requise | Sans impact, build OK |

## 7. Limites

- Watcher **non persistant** : aucune tâche planifiée, aucun service, aucun
  Telegram. La relance est manuelle (procédure §2).
- Aucune action de remédiation active : le watcher émet des signaux, il ne
  corrige pas l'état.
- Le bridge est requis : sans `C:/mari-poc/bridge`, le watcher tourne mais
  chaque `POST /fire` échoue (log d'erreur, pas de crash).