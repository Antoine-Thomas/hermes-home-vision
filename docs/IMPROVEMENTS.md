# Fiche détaillée des améliorations — v1.1 → v1.2

> Document séparant clairement la **version originale 1.1** de la **version améliorée 1.2**.
> Établi le **21/09/2026** à partir de l'état réel des deux branches : aucune amélioration n'est
> déclarée ici qui ne soit vérifiable par une commande (elles sont toutes données en §6).

---

## 1. Vue d'ensemble

| Élément | v1.1 (originale) | v1.2 (améliorée) |
|---|---|---|
| Statut | Stable, figée, référence historique | **recommandée** |
| Branche | `main` | `v1.2-ameliorations` |
| Tag | `v1.1-original` | `v1.2` |
| Commit de référence | `1f1f089` | *voir le tag `v1.2`* |
| Release | [1.1 — Version originale](../../releases/tag/v1.1-original) | [1.2 — Version améliorée](../../releases/tag/v1.2) |
| Documentation | `README.md` d'origine | `README.md` + `docs/IMPROVEMENTS.md` + `docs/CHANGELOG-v1.2.md` + Wiki |
| Runtime Hermes | Hermes Agent v0.21.3 (2026.9.14) | **identique** |
| Licence | aucune licence déclarée | aucune licence déclarée |

**La 1.1 n'est pas supprimée, ni déplacée, ni réécrite** : `main` reste au commit `1f1f089` et le tag
`v1.1-original` y pointe. Les deux versions se téléchargent indépendamment.

---

## 2. Ce que la 1.2 change — et ce qu'elle ne change pas

**Ce qui ne change pas.** La 1.2 n'apporte **aucune modification fonctionnelle** : `config.yaml`,
`cron/jobs.json`, `skills/`, `scripts/`, `profiles/`, `gateway-service/` sont identiques à l'octet
près à la 1.1. Un remplacement de la 1.1 par la 1.2 ne change pas le comportement du runtime.

**Ce qui change.** La 1.2 met le dépôt **en version** (tags, releases), le rend **navigable** (Wiki,
fiche d'améliorations, changelog) et **documente ses garde-fous de sécurité**. Un seul fichier
existant est modifié : `README.md`. Tout le reste est ajouté.

Le détail exact et vérifiable du diff est en §6, commande 2.

---

## 3. Améliorations apportées en 1.2

> **Note de lecture honnête.** La liste de départ décrivait la 1.1 comme un dépôt sans
> documentation ni arborescence. Ce n'est pas l'état réel de `main` : au 17/09/2026 le dépôt porte
> déjà un `README.md` de 293 lignes et `docs/` de 164 fichiers, et son `.gitignore` couvre déjà les
> secrets. Les points concernés sont donc marqués **« déjà en place »** et la 1.2 les *documente et
> les vérifie* au lieu de les présenter comme des nouveautés. C'est la seule manière de ne pas
> écrire une fiche fausse.

### 1. Documentation structurée — *déjà en place, complétée en 1.2*

- **Avant (état réel de la 1.1)** : `README.md` (293 lignes, 9 sections numérotées, tableau
  d'architecture ASCII) et `docs/` (164 fichiers : rapports, snapshots, scripts) existent déjà.
  Aucune fiche d'améliorations, aucun changelog, aucun wiki.
- **Après (1.2)** : `docs/IMPROVEMENTS.md` (ce document), `docs/CHANGELOG-v1.2.md`, un **Wiki de
  8 pages**, et un bandeau de version en tête du `README.md` qui aiguille vers la bonne version.
- **Bénéfice** : le dépôt devient lisible par quelqu'un qui ne l'a pas construit, et les deux
  versions sont explicitement séparées dans la documentation.
- **Fichiers** : `README.md` (modifié), `docs/IMPROVEMENTS.md`, `docs/CHANGELOG-v1.2.md`, Wiki.

### 2. Séparation claire des versions — *nouveau en 1.2*

- **Avant** : aucune notion de version du dépôt, **aucun tag**, une seule branche `main`. La
  « version de référence » citée dans le README était celle d'Hermes Agent (v0.21.3), pas celle du
  dépôt.
- **Après** : tag annoté `v1.1-original` sur `main`, branche `v1.2-ameliorations`, tag annoté `v1.2`,
  deux releases GitHub, et un tableau « Choisir sa version » en tête de README.
- **Bénéfice** : la 1.1 reste téléchargeable à vie (archive ZIP automatique du tag), la 1.2 est
  identifiable sans ambiguïté, et un retour arrière tient en une commande.
- **Fichiers** : tags Git, releases GitHub, `README.md`.

### 3. Sécurité du dépôt — *garde-fous déjà en place, audit exécuté en 1.2*

- **Avant (état réel de la 1.1)** : les garde-fous existaient déjà — `.env`, `.env.*`, `**/.env`,
  `auth.json`, `*.pem`, `*.key`, `state.db*` sont ignorés par `.gitignore`, `.env.example` est le
  seul modèle versionné (noms de variables uniquement), le README §8 documente la purge
  d'historique par `git filter-repo`, et `docs/scripts/scan_secrets_history.py` sait scanner
  **tout l'historique**. Ce qui manquait : ce contrôle n'avait pas été **rejoué** depuis le passage
  du dépôt en public.
- **Après (1.2)** : audit rejoué sur l'intégralité de l'historique le **21/09/2026**, résultat
  consigné dans `docs/CHANGELOG-v1.2.md` et ci-dessous ; plus aucune ambiguïté sur le fait que le
  dépôt est public et que son contenu a été contrôlé.
- **Bénéfice** : évite la fuite d'une clé API ou d'un jeton Telegram dans un dépôt public — le
  risque exact que le README §8 signale.

**Résultat de l'audit du 21/09/2026** (`python docs/scripts/scan_secrets_history.py --repo .`) :

```
depot .
objets=2494 blobs=1564 volume=11.2 Mo

telegram_bot_token   : 0 blob
google_api_key       : 0 blob
sk_key               : 1 blob(s)   <- placeholder d'exemple, 16 caracteres (sk-EXA...mmit)
github_token         : 0 blob
huggingface_token    : 0 blob
pem_private_key      : 0 blob

RESULTAT : aucune valeur de secret reelle dans l'historique (placeholders exclus)
```

Le seul blob signalé est un exemple pédagogique dans une référence de skill
(`profiles/watch/skills/.../omniroute-api-workflow.md`) : 16 caractères, valeur factice. Aucun
`.env`, `state.db` ou `auth.json` n'est suivi (`git ls-files` : vide).

- **Fichiers** : `README.md` (§8), `docs/CHANGELOG-v1.2.md`, release 1.2.

### 4. Structure du dépôt — *déjà en place*

- **Avant (état réel de la 1.1)** : l'arborescence est déjà rangée — `docs/`, `scripts/`, `skills/`,
  `cron/`, `profiles/`, `gateway-service/`, `memories/`, plus les fichiers de lancement à la racine
  (`omniroute-launch.vbs`, `restart_gateway.ps1`, `config.yaml`, `SOUL.md`). La 1.1 ne range pas
  « des fichiers en vrac à la racine ».
- **Après (1.2)** : inchangé, et désormais **documenté** par le tableau « Structure du dépôt »
  augmenté des nouveaux documents.
- **Bénéfice** : navigation et maintenance facilitées — sans réorganisation cosmétique inutile, donc
  sans casser les scripts qui référencent ces chemins.
- **Fichiers** : `README.md` (§3 et §9).

### 5. Installation — *outil déjà en place, mode opératoire documenté en 1.2*

- **Avant (état réel de la 1.1)** : l'installation n'est **pas** manuelle : `docs/scripts/bootstrap.ps1`
  automatise la remise en route (installation d'Hermes si besoin, pose de la configuration du dépôt,
  copie des `.env.example`, recréation des 14 tâches planifiées, démarrage des services dans l'ordre,
  journal horodaté) — en `DryRun` par défaut, `-Apply` pour exécuter. `docs/scripts/restore-from-github.md`
  couvre les étapes manuelles.
- **Après (1.2)** : ce mode opératoire devient consultable hors du dépôt, dans le Wiki
  (`Installation-1.2`), avec les prérequis, les commandes exactes et la vérification attendue.
- **Bénéfice** : onboarding rapide sans avoir à lire 293 lignes de README ni le code du bootstrap.
- **Fichiers** : Wiki `Installation-1.2`, `README.md` (§4).

### 6. Changelog et versioning — *nouveau en 1.2*

- **Avant** : aucun changelog, aucune convention de version pour le dépôt.
- **Après** : `docs/CHANGELOG-v1.2.md` et la convention **SemVer** (`MAJEUR.MINEUR`) appliquée aux
  deux versions : `1.1` = état figé du 17/09/2026, `1.2` = mise en version documentée.
- **Bénéfice** : historique des changements clair, et une règle écrite pour la suite (une rupture de
  compatibilité du runtime, par exemple une montée de version d'Hermes Agent, donnera une `2.0`).
- **Fichiers** : `docs/CHANGELOG-v1.2.md`.

### 7. Wiki GitHub complet — *nouveau en 1.2*

- **Avant** : inexistant.
- **Après** : 8 pages publiées dans le Wiki du dépôt.
- **Bénéfice** : documentation navigable, versions séparées, FAQ et procédure de migration.
- **Fichiers** : Wiki GitHub.

| Page | Contenu |
|---|---|
| `Home` | Accueil, choix de version, sommaire |
| `Version-1.1` | Version originale : téléchargement, installation, limites |
| `Version-1.2` | Version améliorée : téléchargement, nouveautés, vérification |
| `Installation-1.2` | Prérequis, étapes, bootstrap, vérification, dépannage |
| `Ameliorations-detaillees` | Tableau récapitulatif des 7 améliorations |
| `Migration-depuis-1.1` | Passage 1.1 → 1.2, sauvegarde, rollback |
| `Archives-1.1` | Télécharger la 1.1 : tag, branche, ZIP, release |
| `FAQ` | 10 questions fréquentes |

---

## 4. Compatibilité

| Point | Réponse |
|---|---|
| Compatible avec la 1.1 | **Oui** — mêmes fichiers d'exécution, mêmes chemins, mêmes tâches planifiées |
| Migration nécessaire | **Non** — au plus une bascule de branche (`git checkout v1.2`), procédure dans [`Migration-depuis-1.1`](../../wiki/Migration-depuis-1.1) |
| Ruptures de compatibilité | **Aucune** |
| Retour arrière | `git checkout v1.1-original` — restaure l'état exact de `main` |
| Prérequis inchangés | Windows 11, PowerShell 5.1+, Hermes Agent v0.21.3 |

---

## 5. Archives — la 1.1 reste téléchargeable

| Moyen | Lien |
|---|---|
| Branche | [`main`](../../tree/main) |
| Tag | [`v1.1-original`](../../tree/v1.1-original) |
| Release | [1.1 — Version originale](../../releases/tag/v1.1-original) |
| ZIP du tag | [`v1.1-original.zip`](../../archive/refs/tags/v1.1-original.zip) |

---

## 6. Vérifier soi-même

```bash
# 1. La 1.1 est intacte : main pointe toujours sur le commit de reference
git ls-remote origin refs/heads/main
# attendu : 1f1f0899cf8e8b72721ccac42d6b7aad8d7a5eff

# 2. Le contenu exact de la 1.2 (fichiers ajoutes / modifies)
git fetch --all --tags
git diff --stat main..v1.2-ameliorations
# attendu : README.md modifie, docs/IMPROVEMENTS.md, docs/CHANGELOG-v1.2.md ajoutes

# 3. Les deux tags existent et pointent au bon endroit
git tag -l                                  # v1.1-original, v1.2
git rev-parse v1.1-original                 # 1f1f089...

# 4. Aucun secret dans l'historique
python docs/scripts/scan_secrets_history.py --repo .
# attendu : RESULTAT : aucune valeur de secret reelle dans l'historique
```

---

## 7. Licence

Le dépôt ne contient **aucun fichier `LICENSE`** : aucune licence n'est déclarée sur la 1.1 comme
sur la 1.2 (voir la section « Licence et contact » du `README.md`). Les composants tiers — Hermes
Agent, OmniRoute, SiYuan, NVIDIA NIM — restent sous leurs licences respectives. La 1.2 ne modifie
pas ce point et n'ajoute aucune licence : c'est une décision qui appartient à l'auteur.
