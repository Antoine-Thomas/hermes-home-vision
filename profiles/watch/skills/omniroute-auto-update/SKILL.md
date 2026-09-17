---
name: omniroute-auto-update
description: "Use when auto-launching OmniRoute or discovering new free AI models (GLM, nemotron, etc.) for the eco combo."
version: 1.0.0
author: searching-murphy
license: mit
metadata:
  hermes:
    tags: [omniroute, auto-launch, model-discovery, cron, free-models]
    related_skills: [omniroute-gateway, omniroute-cost-tracker]
---

# OmniRoute Auto-Update

Lance OmniRoute de façon invisible et découvre les nouveaux modèles IA gratuits.

## Ce que fait ce skill

1. **Lancement invisible d'OmniRoute** — via un VBS (fenêtre masquée, aucun flash
   de console) idempotent : ne relance pas si le port 20128 est déjà ouvert.
2. **Découverte de nouveaux modèles gratuits** — interroge `/v1/models`, compare
   aux modèles déjà présents dans les combos, sonde les candidats "free" par un
   appel réel et journalise les verdicts.
3. **Cron invisible** — un cron Hermes (sans fenêtre) réexécute la découverte.

## API réelle (vérifiée 2026-09-02)

- OmniRoute : `http://127.0.0.1:20128` (dashboard `/api`, inference `/v1`).
- Auth : Bearer key dans `~/.omniroute/.env` (`OMNIROUTE_API_KEY=...`), valable
  pour `/v1/*` ET `/api/*` (lecture + écriture).
- Lecture des combos : `GET /api/combos` → `{"combos":[...]}`.
- Liste des modèles : `GET /v1/models` → `{"data":[{id,...}]}`.

⚠️ Les chemins `/v1/combos/eco` et `PUT /v1/combos` n'existent PAS.

## Point clé : "gratuit" ne veut pas dire "fonctionne"

- Le suffixe `free` dans un ID (`oc/*-free`) ne garantit pas un modèle sans clé.
- **GLM-5.3 n'est PAS gratuit** via API (payant sur Z.AI et ZenMux). Seul
  `zc/glm-5.3` (provider local `zcode`) est gratuit en preview, et il exige
  l'app ZCode installée (`zcode.z.ai`) sinon il renvoie `502 spawn zcode ENOENT`.
- Un modèle s'ajoute au combo UNIQUEMENT après un probe réel :
  `POST /v1/chat/completions` avec `max_tokens=50` qui renvoie HTTP 200 ET un
  `choices[0].message.content` non vide. Un `200` sur `/models` ne suffit pas.

## Fichiers

- `scripts/omniroute_launch.vbs` — lancement invisible (copie du launcher installé).
- `scripts/discover_free_models.py` — découverte + probe + journal daté.
- `references/model_verdicts.md` — verdicts par modèle (à alimenter).

## Commandes

```bash
# Découvrir + sonder les nouveaux modèles gratuits (lecture seule, sans écrire dans les combos)
python scripts/discover_free_models.py --dry-run

# Idem + ajouter automatiquement les modèles validés à la fin du combo eco
python scripts/discover_free_models.py --apply

# Lancer OmniRoute de façon invisible (idempotent)
wscript //B scripts/omniroute_launch.vbs
```

Le `--apply` n'ajoute un modèle que s'il a passé le probe (HTTP 200 + contenu
non vide) et qu'il n'est pas déjà dans un combo. Le combo n'est jamais réécrit
sans sauvegarde préalable (`backups/`).

## Cron invisible

Créé via l'outil `cronjob` d'Hermes (aucune fenêtre console). Voir
`references/cron.md` pour le prompt de création et la vérification.
