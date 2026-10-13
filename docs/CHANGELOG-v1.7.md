# Changelog — Version 1.7 — ANIMA Reactor 0.3

> **Statut : publiée.** Tag `v1.7` — commit `feat(v1.7-reactor)`.
> Toutes les valeurs sont mesurées le **2026-10-13** sur la machine d'origine.

## [1.7.0] — 2026-10-13

### Les changements en détail

**Couche 5 — orchestration réactive.** La supervision ANIMA passe de passive
(lire `health_anima_state.json` et constater) à autonome (détecter une
transition d'état et émettre un signal traçable). Le watcher Python
(`scripts/anima_watcher.py`) lit l'état de santé toutes les 30 s, mémorise
l'état précédent de chaque composant, et POSTe `anima-<composant>-fail` sur le
bridge MARI quand un composant passe `READY/DEGRADED → FAILED/BLOCKED`.
Mesures : `POST /fire` → HTTP 200 `{"status":"signal emitted","total":1}`.

**Watcher.** Copie exacte (SHA256 `15558782…`) de la version Phase 4c du POC :
`C:/mari-poc/anima_watcher.py` → `scripts/anima_watcher.py` (103 lignes). Le
`STATE_FILE` reste en chemin absolu vers
`%LOCALAPPDATA%\hermes\data\route_ia_fix\health_anima_state.json`.

**Config Reactor.** `scripts/reactor_config.json` centralise ports (55551 silo /
55552 gateway / 55553 REST), chemins (state file, remediation, log), seuils
(`window_seconds: 60`) et kill-switch (`C:/mari-poc/DISABLE`).

**Check Reactor.** `scripts/check_reactor.ps1` vérifie en une passe : bridge
`/status` (200), ports 55551–55553 libres, state file frais (`_maj` < 15 min),
plage Wazuh 54985–55084 vide, service Wazuh, gateway Hermes.

**Page wiki.** `wiki/concepts/mari-reactor.md` documente le concept : définition,
composants, flux, quand utiliser / ne pas utiliser, lien ANIMA, références.

**Skill MARI.** `skills/software-development/mari-orleans-integration/` (4
fichiers, 40K) : skill auto-généré pendant le POC, intégré tel quel dans le
dépôt pour référence.

### Ajouté

- `docs/ARCHITECTURE_REACTOR.md` — architecture de la couche 5 (9 sections).
- `docs/CHANGELOG-v1.7.md` — ce document.
- `docs/REACTOR_INSTALL.md` — prérequis + procédure de relance + kill-switch.
- `scripts/anima_watcher.py` — watcher de supervision réactive.
- `scripts/reactor_config.json` — configuration du réacteur.
- `scripts/check_reactor.ps1` — contrôle de la chaîne complète.
- `wiki/concepts/mari-reactor.md` — page wiki L1 du concept.
- `skills/software-development/mari-orleans-integration/**` — skill POC MARI.

### Modifié

- `README.md` — section « ANIMA Reactor 0.3 » + lien vers l'architecture.

### Corrigé

- **Bug latent ANIMA : trigger `StopAtDurationEnd=True` expiré.** Un déclencheur
  horodaté expiré laissait la supervision sans effectivité pendant 5 jours
  d'aveuglement. Détecté lors des vérifications Phase 1 : la fraîcheur du state
  file (`_maj` < 15 min) est désormais un contrôle explicite du check Reactor.

### Sécurité

- Isolation runtime Hermes : la couche 5 est hors `%LOCALAPPDATA%\hermes`
  (bridge) et hors gateway — le watcher n'émet que des signaux loopback.
- Aucun secret, aucun `.env`, aucun fichier `.cs` dans le commit.

### Limites assumées

- Bridge C# reste dans `C:/mari-poc/` (hors dépôt) — la chaîne complète n'est
  pas reproductible depuis un clone seul.
- Aucune action de remédiation active (fichier de contrôle uniquement).
- Watcher non persistant : relance manuelle, pas de service ni de Telegram.

### Notes de migration

Aucune : la v1.7 n'ajoute aucun changement de configuration runtime. La ligne
de rollback vise le dernier commit avant cette release
(`git rev-parse v1.7^`), soit le commit v1.6.