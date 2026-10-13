# Architecture — ANIMA Reactor 0.3 (Couche 5, orchestration réactive)

> **Statut : v1.7 — intégré au dépôt hermes-home-vision, mesuré le 2026-10-13.**
> Version de référence : Hermes Agent v0.21.6+131.g38880bd, POC MARI validé
> (`C:/mari-poc/CLOTURE_POC.md`). Toutes les valeurs ci-dessous sont relevées
> sur la machine d'origine (`%LOCALAPPDATA%\hermes`, Windows 11 natif).

## 1. Vue d'ensemble

ANIMA Reactor est la **couche 5** du système ANIMA : l'orchestration réactive.
Elle transforme la supervision passive (lire `health_anima_state.json` et
constater) en **supervision autonome** (détecter une transition d'état et
déclencher une action traçable).

Le réacteur est un **watcher Python** qui :

1. Lit l'état de santé ANIMA (`health_anima_state.json`) toutes les 30 s ;
2. Mémorise l'état précédent de chaque composant ;
3. Détecte les transitions `READY/DEGRADED → FAILED/BLOCKED` ;
4. Émet un signal MARI via le bridge (`POST /fire`) ;
5. Journalise chaque cycle et chaque transition dans `watcher.log`.

Décision locale, action traçable : le watcher ne « répare » rien lui-même —
il signale, et le système cible (MARI / couche de remédiation) décide.

## 2. Composants

| Composant | Rôle | Emplacement |
|---|---|---|
| Watcher | Boucle de supervision + détection de transitions | `scripts/anima_watcher.py` |
| Config | Ports, chemins, seuils, kill-switch | `scripts/reactor_config.json` |
| Bridge (POC) | Nœud MARI hébergé, expose `POST /fire` | `C:/mari-poc/bridge` (HORS dépôt) |
| State file | État de santé ANIMA, produit par la couche 3 | `%LOCALAPPDATA%\hermes\data\route_ia_fix\health_anima_state.json` |
| Journal | Trace des cycles + transitions | `C:/mari-poc/journal/watcher.log` |
| Kill-switch | Fichier de contrôle d'arrêt | `C:/mari-poc/DISABLE` |
| Check | Script de contrôle de la chaîne | `scripts/check_reactor.ps1` |

## 3. Flux E2E

```
health_anima_state.json (toutes les 30 s)
        │  lecture
        ▼
anima_watcher.py ── compare last_state (mémoire interne)
        │  transition READY/DEGRADED → FAILED/BLOCKED détectée
        ▼
POST http://127.0.0.1:55553/fire
        │  {"fireId": "anima-<composant>-fail", "sourceId": "anima-watcher"}
        ▼
Bridge MARI (nœud Orleans, silo 55551 / gateway 55552 / REST 55553)
        │  signal émis, total incrémenté
        ▼
journal/watcher.log  ← "Transition <composant>: anima-<composant>-fail -> POST result: ..."
```

Cycle nominal : lecture → comparaison → (si transition) POST → journal → sleep 30 s.

## 4. Contrats

### 4.1 Format du state file (entrée)

`health_anima_state.json` : objet JSON dont chaque clé de premier niveau est un
composant avec un champ `last_state` :

```json
{ "ollama": {"last_state": "FAILED", "failure_streak": 10}, ... }
```

Valeurs d'état reconnues : `READY`, `DEGRADED`, `FAILED`, `BLOCKED`.
Fichier absent ou illisible → cycle vide, log `state file vide` (pas de crash).

### 4.2 POST /fire (sortie)

- URL : `http://127.0.0.1:55553/fire`
- Méthode : POST, `Content-Type: application/json`
- Corps : `{"fireId": "<id>", "sourceId": "anima-watcher"}`
- Réponse 200 : `{"status": "signal emitted", "fireId": "...", "total": N}`
- Timeout côté watcher : 5 s ; échec réseau → log `POST /fire error`, cycle poursuit.

### 4.3 Kill-switch

`C:/mari-poc/DISABLE` présent → le watcher journalise `DISABLE file present` et
sort immédiatement (avant le premier cycle et à chaque itération).

## 5. Ports

| Port | Usage | Plage |
|---|---|---|
| 55551 | Silo MARI (Orleans) | dédiée, hors plage Wazuh |
| 55552 | Gateway MARI (Orleans client) | dédiée |
| 55553 | REST bridge (`/status`, `/fire`) | dédiée |

Plages à ne PAS confondre : **54985–55084 = Wazuh** (jamais citée comme active
dans ce module). `check_reactor.ps1` vérifie que les ports 55551–55553 sont
libres **et** que la plage Wazuh est vide avant de déclarer la chaîne saine.

## 6. Sécurité

- **Isolation runtime** : le watcher et la config vivent dans le dépôt
  (`scripts/`), le bridge C# reste dans `C:/mari-poc/` — hors dépôt, hors
  runtime Hermes.
- **Aucun secret** : aucun token, clé API ou mot de passe dans le code, la
  config ou les docs. Le bridge ne s'authentifie pas (loopback uniquement).
- **Loopback** : le bridge écoute sur `127.0.0.1` (`Endpoint.Loopback: true`).
- **Aucune action de remédiation active** : le watcher émet des signaux, il ne
  modifie aucun fichier de configuration Hermes, ne touche ni gateway ni tâches
  planifiées.
- **Kill-switch** : arrêt garanti par fichier de contrôle, sans dépendre d'un
  signal OS.

## 7. Pitfalls (pièges connus)

1. **`StopAtDurationEnd=True` expiré** — bug latent ANIMA corrigé à l'occasion
   de v1.7 : un trigger horodaté expiré laissait le système 5 jours sans
   supervision effective. Toujours vérifier la fraîcheur du state file
   (`_maj` < 15 min), pas seulement sa présence.
2. **Fichier d'état absent ≠ état vide** : le watcher log `state file vide` sans
   émettre de signal — une coupure de la couche 3 produit un silence, pas une
   alerte. Vérifier le journal.
3. **Ports déjà occupés** : un silo fantôme (ancien bridge non tué) bloque le
   lancement. `check_reactor.ps1` détecte 55551–55553 occupés avant le build.
4. **Plage Wazuh confondue** : ne jamais lancer un test sur 54985–55084.
5. **Windows `findstr`/bash** : les vérifications de ports doivent utiliser
   `netstat -ano | findstr` (cmd) — la syntaxe bash `grep` ne voit pas les
   sorties `findstr` dans tous les contextes (voir `check_reactor.ps1`).

## 8. Limites assumées

- Le bridge C# reste dans `C:/mari-poc/` — un clone du dépôt ne peut pas
  relancer la chaîne sans le POC local.
- Aucune action de remédiation active (fichier de contrôle uniquement).
- Watcher **non persistant** : pas de service Windows, pas de tâche planifiée,
  pas d'envoi Telegram. La relance est manuelle (`REACTOR_INSTALL.md`).
- Fenêtre de détection : 30 s par cycle — une transition qui revient à
  `READY` entre deux cycles n'est pas vue.
- Le watcher est monoprocessus : deux instances simultanées produiraient des
  signaux en double (pas de verrou).

## 9. Vérifications

La procédure de vérification complète (13 checks) est dans
[`docs/REACTOR_INSTALL.md`](REACTOR_INSTALL.md). Résumé des preuves v1.7
(mesurées le 2026-10-13) :

- Build bridge : exit 0 (0 erreur, 18 warnings NU1608).
- `GET /status` → HTTP 200, `{"status":"ok","signalsEmitted":0}`.
- `POST /fire anima-ollama-fail` → `{"status":"signal emitted","total":1}`.
- `POST /fire anima-wazuh-fail` → signal émis.
- Kill-switch : `DISABLE` créé → log `DISABLE file present` → supprimé.
- Ports 55551/55552/55553 libres après arrêt propre du bridge.