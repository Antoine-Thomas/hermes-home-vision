---
title: MARI Reactor
created: 2026-10-13
updated: 2026-10-13
type: concept
tags: [anima, mari, orleans, reacteur, supervision, signals, bridge]
sources: [raw/notes/poc-mari-cloture-2026-10-13.md]
confidence: high
contested: false
contradictions: []
---

# MARI Reactor — orchestration réactive (Couche 5 ANIMA)

Le réacteur MARI est la **couche 5** du système [[anima]] : il transforme la
supervision passive (lire `health_anima_state.json` et constater) en
**supervision autonome** (détecter une transition d'état et émettre un signal
traçable). Décision locale, action traçable : il ne répare pas, il signale.

## Définition

Un watcher Python (`scripts/anima_watcher.py`) lit l'état de santé ANIMA toutes
les 30 s, mémorise l'état précédent de chaque composant, et détecte les
transitions `READY/DEGRADED → FAILED/BLOCKED`. À chaque transition, il POSTe
`anima-<composant>-fail` sur le bridge MARI (`http://127.0.0.1:55553/fire`).
Le bridge est un nœud MARI hébergé dans un processus ASP.NET Core — VGrains,
Signaux, Portes, Déclencheurs, Séquences (framework MARI, MIT).

## Composants

| Composant | Rôle | Emplacement |
|---|---|---|
| Watcher | Boucle de supervision + détection | `scripts/anima_watcher.py` |
| Config | Ports, chemins, seuils, kill-switch | `scripts/reactor_config.json` |
| Bridge (POC) | Nœud MARI, expose `POST /fire` | `C:/mari-poc/bridge` (hors dépôt) |
| State file | État de santé ANIMA (couche 3) | `%LOCALAPPDATA%\hermes\data\route_ia_fix\health_anima_state.json` |
| Journal | Trace cycles + transitions | `C:/mari-poc/journal/watcher.log` |
| Kill-switch | Fichier de contrôle d'arrêt | `C:/mari-poc/DISABLE` |
| Check | Contrôle de la chaîne complète | `scripts/check_reactor.ps1` |

## Flux

```
health_anima_state.json ──► anima_watcher.py ──► POST /fire ──► Bridge MARI
        (lecture 30s)          (transition détectée)   (55553)   (signal émis)
                                                                      │
                                              journal/watcher.log ◄───┘
```

## Quand utiliser

- Vérifier qu'un composant ANIMA (Ollama, Wazuh, RAG, SiYuan…) est surveillé
  en continu sans supervision humaine.
- Émettre un signal MARI traçable sur dégradation (`DEGRADED → FAILED`).
- Tester la chaîne complète état → signal (POC validé, 13 checks Phase 1).

## Quand NE PAS utiliser

- Pour **réparer** un composant : le réacteur émet des signaux, il n'agit pas.
- Comme service persistant : le watcher est non persistant (relance manuelle).
- Hors machine d'origine : le bridge vit dans `C:/mari-poc/`, hors dépôt.
- Sur la plage Wazuh 54985–55084 : dédiée à [[wazuh]], jamais au réacteur.

## Lien ANIMA

Le réacteur consomme le state file produit par la supervision ANIMA (couche 3)
et étend [[anima]] d'une capacité d'orchestration. La fraîcheur du state file
(`_maj` < 15 min) est le contrôle n° 4 du check Reactor — un state file périmé
signifie une couche 3 aveugle (cf. bug `StopAtDurationEnd=True` expiré, 5 jours
d'aveuglement, corrigé en v1.7).

## Références

- Architecture : `docs/ARCHITECTURE_REACTOR.md` (9 sections, v1.7).
- Installation / relance / kill-switch : `docs/REACTOR_INSTALL.md`.
- Changelog : `docs/CHANGELOG-v1.7.md` (format Keep a Changelog).
- Skill POC : skill `software-development/mari-orleans-integration`
  (`references/node-and-bridge-recipe.md`, `references/anima-supervision.md`).
- POC source : `C:/mari-poc/CLOTURE_POC.md` (hors dépôt).