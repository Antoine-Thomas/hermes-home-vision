# ANIMA 0.2 — Changelog

> **Bascule 0.1 → 0.2, mesurée le 2026-10-07 à 11:47:04 (+0200)** sur la machine d'origine
> (`%LOCALAPPDATA%\hermes`, Windows 11 natif). Toutes les valeurs de ce document sont relevées —
> par la sonde elle-même ou par mesure directe — aucune n'est estimée.
> Version précédente documentée : **0.1** (2026-09-29).

## Bascule 0.1 → 0.2 (2026-10-07)

### Ajouts vérifiés

- **4ᵉ profil `docs-writer`.** Quatre environnements isolés : `default`, `watch`, `veille`,
  `docs-writer`. `profiles/docs-writer/config.yaml` : primaire **DeepSeek direct**
  (`model.default: deepseek-flash`, `model.provider: deepseek`) et **aucun bot Telegram configuré**
  (0 occurrence de `telegram`, `bot_token` ou `chat_id` dans le fichier, contre 4 sections
  `telegram:` dans le profil `default`).

- **Laya ONNX officiel.** Serveur de décision local `127.0.0.1:8787` **LISTENING**
  (PID 11764 : `python.exe server.py --onnx-dir …\data\laya-onnx\english --port 8787`).
  Composant `laya` = **READY**, sonde à 408 ms. Modèle : ModernBERT-large + tête typée,
  **421 M paramètres**, **Apache-2.0** (Convai Innovations), export `mariojcr/laya-onnx`,
  checkpoint `english` (1,69 Go) sous `data\laya-onnx\`.

- **12 sauvegardes `.env` isolées hors du dépôt** — `%USERPROFILE%\hermes-secrets-backup\`,
  arborescence miroir par profil : `default\` 2, `docs-writer\` 2, `veille\` 2, `watch\` 6.
  Déplacement, jamais suppression.

- **Plugin `anima-memoire-router` 0.2.0.** `plugin.yaml` : `version: 0.2.0`,
  `author: ANIMA 0.1`, `kind: standalone`. Actif : listé dans `plugins.enabled` et
  `entries.anima-memoire-router.settings.mode: "on"`. Trace du passage de version :
  `backups_H_phaseB\anima-memoire-router_plugin.yaml.20260929` est en `0.1.0`.

### Corrections

- **ACL du `.env` racine (profil `default`) durcie.** Avant : 4 ACE, **toutes héritées `(I)`**,
  dont `OMATHS\CodexSandboxUsers:(I)(RX)` — un groupe applicatif tiers pouvait lire les secrets.
  Après : **3 ACE `(F)` non héritées** (`Système`, `Administrateurs`, `searc`), 0 `(I)`,
  0 `CodexSandboxUsers`. Les **quatre** `.env` sont désormais cohérents, mesuré fichier par
  fichier : `ACE(F)=3 · heritees(I)=0 · CodexSandboxUsers=0` pour `default`, `watch`, `veille`
  et `docs-writer`. Le contenu des fichiers est inchangé (sha256 identique avant/après l'ACL).

- **Sonde `fallback` : deux bugs corrigés** (`data/route_ia_fix/health_anima.py`).
  1. La comparaison portait sur `primaire["model"]`, alors que le parseur de `config.yaml`
     remplit la clé **`default`** : `primaire.get("model")` valait donc toujours `None` et
     `repli_active` était **toujours `True`**.
  2. `dernier_etage_atteint` était vrai **par construction** : le dernier étage de
     `fallback_providers` est `deepseek/deepseek-flash`, soit le modèle primaire lui-même, donc
     « atteint » dès que le primaire sert. Le dernier étage n'est désormais compté que s'il est
     distinct du primaire (nouvel indicateur `dernier_etage_est_primaire`).

  **Résultat mesuré après la sonde du 2026-10-07 11:47:04 — `fallback = READY`** :
  `repli_active=False`, `dernier_etage_atteint=False`, `dernier_etage_est_primaire=True`,
  `failure_streak=0`, aucun motif. L'état publié avant correction était `DEGRADED` en continu.
  Contrôle inverse vérifié : sur une chaîne dont le dernier étage est un vrai repli distinct et
  effectivement utilisé, l'alerte « dernier étage de la chaîne atteint » se déclenche toujours —
  le correctif n'éteint pas le signal.

### État connu au 2026-10-07T11:47:04

| Composant | Statut | Échecs | Dernier succès |
|---|---|---|---|
| couts | READY | 0 | 2026-10-07T11:47:04 |
| cron | DEGRADED | 330 | — |
| fallback | READY | 0 | 2026-10-07T11:47:04 |
| gateway | READY | 0 | 2026-10-07T11:46:59 |
| jev | READY | 0 | 2026-10-07T11:47:02 |
| laya | READY | 0 | 2026-10-07T11:47:02 |
| memoire | READY | 0 | 2026-10-07T11:47:04 |
| nim_proxy | READY | 0 | 2026-10-07T11:46:59 |
| ollama | FAILED | 75 | 2026-10-06T15:56:10 |
| omniroute | READY | 0 | 2026-10-07T11:46:59 |
| profils | READY | 0 | 2026-10-07T11:46:59 |
| rag | READY | 0 | 2026-10-07T11:47:01 |
| reindex | READY | 0 | 2026-10-07T11:47:04 |
| siyuan | READY | 0 | 2026-10-07T11:47:01 |
| wazuh | FAILED | 75 | 2026-10-06T15:56:15 |

**État global : `FAILED`** — motif « au moins un composant critique FAILED » ; `critical_state =
FAILED`. C'est un constat honnête : **ollama et wazuh sont arrêtés et la 0.2 ne les répare pas.**

### Hors périmètre

- **`ollama`** — FAILED, arrêté depuis le 2026-10-06 15:56:10 (75 échecs consécutifs).
  `WinError 10061` sur `http://127.0.0.1:11434/api/tags` : aucun processus, aucun port en écoute.
  Service externe, à la charge de l'opérateur.
- **`wazuh`** — FAILED, arrêté depuis le 2026-10-06 15:56:15 (75 échecs). Indexer injoignable
  (`https://127.0.0.1:9200/_cluster/health`), `conteneurs: {}` : le démon Docker n'est pas
  démarré, ni `9200` ni `55085` n'écoutent. **Aucune configuration Wazuh n'a été modifiée.**
- **`cron`** — DEGRADED : 1 job actif en erreur sur 12. `veille-hebdo` (profil `veille`),
  4 échecs consécutifs, dernier run 2026-10-05T10:07:47, `RuntimeError: [504] Request exceeded
  OmniRoute's local rate-limit execution expiration … for openai/nv`. Le planificateur lui-même
  est sain (battement `cron/ticker_heartbeat` frais).
- **backend `9119`** — retiré le 2026-09-29, statut `OUT_OF_SCOPE / OBSOLETE` — preuve :
  `data/route_ia_fix/backend_9119_retirement_plan.md §6`.

### À trancher

- **Contradiction sur le rôle de Laya.** `wiki/concepts/laya-onnx-windows.md` présente Laya comme
  « le fallback local gratuit de JEV » ; `docs/ARCHITECTURE_AEGIS.md` affirme l'inverse — « JEV
  reste le décideur principal ; Laya est un accélérateur gratuit, pas un substitut » — le repli de
  JEV étant la route locale `rag` via `wiki/scripts/jev_router.py`, avec la mention « aucun repli
  vers un second moteur ». Accord JEV ↔ Laya mesuré : **6/10 (60 %, cible 80 %)**. Arbitrage en
  attente, consigné dans `wiki/contradictions.md`.

## Mise à jour du 2026-10-07 12:00

Redémarrage de Docker Desktop (Wazuh) et du service Ollama. Le tableau du 11:47:04 ci-dessus
reste en place : il fait foi pour cette date.

| Composant | 11:47:04 | 11:59:40 |
|---|---|---|
| ollama | FAILED (75 échecs) | **READY** (0) |
| wazuh | FAILED (75 échecs) | **READY** (0) |
| fallback | READY | READY |
| cron | DEGRADED | DEGRADED (veille-hebdo, 504 OmniRoute — inchangé) |
| overall_state | FAILED | **DEGRADED** |
| critical_state | FAILED | **READY** |

Le seul composant encore dégradé est `cron`, à cause du job `veille-hebdo` en 504 OmniRoute
(4 échecs consécutifs, prochain run 2026-10-12T10:00). Le planificateur lui-même est sain.

Détails mesurés :
- ollama : PID 21404, port 11434, /api/tags → qwen2.5:7b (4,68 Go) intact
- wazuh : 3 conteneurs Up (dashboard 8443, indexer 9200, manager 55085), indexer_code 200
