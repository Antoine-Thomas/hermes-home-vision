# Changelog — Version 1.5 « Hermes Aegis-Sec »

> **Statut : publiée.** Tag annoté `v1.5` sur `main`. La **1.4 « Aegis » reste non publiée**
> (aucun tag `v1.4`) : ses deux bloqueurs B1/B2 restent ouverts et sont reportés en issues
> connues de la 1.5.
> Toutes les valeurs ci-dessous sont **mesurées le 08/10/2026** sur la machine d'origine
> (`%LOCALAPPDATA%\hermes`, Windows 11 natif), avec Hermes Agent **v0.21.6+131.g38880bd**,
> config version **50**, upstream `38880bd2`.

Thème de la 1.5 : **Aegis-Sec**, la couche sécurité passe de « vérifiable » à « outillée » —
un profil dédié à l'analyse défensive, le balayage de secrets corrigé, et la publication de la
documentation de la 1.4 restée en attente.

Convention : [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/) · versionnage
[SemVer](https://semver.org/lang/fr/).

---

## [1.5] — 2026-10-08

### Added

- profil **security** dédié cybersécurité : `SOUL.md` (analyste sécurité senior, séparation
  *observé* / *inféré* / *hypothèse*, citation obligatoire des sources, sévérité justifiée,
  périmètre défensif uniquement), `config.yaml` (modèle par défaut + chaîne de repli OpenRouter
  4 étages, primaire free-openrouter).
- **gateway 5 profils** : `default`, `docs-writer`, `security`, `veille`, `watch` — un seul
  gateway par hôte les sert tous (tâche planifiée `Hermes_Gateway`).

### Changed

- Hermes Agent **v0.21.5 → v0.21.6+131.g38880bd** (632 commits upstream, upstream `38880bd2`),
  config version 50.
- `docs/scripts/scan_secrets_history.py` : motif **`sk-key` ancré par lookbehind gauche**
  (`(?<![A-Za-z0-9])sk-…`) — le motif nu mordait dans les noms de fichiers contenant `sk-`
  et produisait un faux positif ; la détection des vraies clés (32-64 car alphanumériques) est
  inchangée.

### Fixed

- **faux positif `b52e8fae773b`** sur `skills/autonomous-ai-agents/hermes-agent/SKILL.md` :
  la « valeur » signalée était un fragment du nom de fichier
  `delegate-task-concurrency-diagnosis.md` (24 car, 100 % minuscules + 1 tiret, 0 chiffre,
  0 majuscule — profil impossible pour une clé). Après ancrage : **0 valeur réelle**, exit 0.

### Notes

- Les bloqueurs **B1** (MP4 manquant) et **B2** (watchdog en pause) de la 1.4 restent **ouverts** :
  reportés en « issues connues de 1.5 ». La 1.4 n'est donc ni taguée ni publiée, et aucune version
  antérieure n'est réécrite.
- Les corrections Wazuh du chantier « 5 points de sécurité » sont documentées **hors dépôt** dans
  `wazuh_securite_20261008/ROLLBACK.md` (§1 à §13) : indexer `admin/admin`, `authd` désactivé,
  logs API en JSON, ligne 81 du compose, certificat audité, rétrogradation de l'agent 4.14.8 → 4.7.3.
