# Hermes Home Vision

> **Version actuelle : `1.2`** — version améliorée, recommandée → branche `v1.2-ameliorations`, tag `v1.2`
> **Version originale : `1.1`** — [consulter / télécharger](https://github.com/Antoine-Thomas/hermes-home-vision/tree/v1.1-original) → branche `main`, tag `v1.1-original`

> Installation personnelle de Hermes Agent — 3 profils isolés, supervision continue, veille automatique.

Dépôt **privé** (accès au propriétaire) : `https://github.com/Antoine-Thomas/hermes-home-vision` — il
contient **tout** : le runtime Hermes (configuration, profils, skills, scripts) **et** sa documentation
rangée sous `docs/`. Un seul `git clone` restaure l'ensemble.
Visibilité : le dépôt a été trouvé **public** le 21/09/2026 alors que sa description annonçait
« Privé » ; il a été **repassé en privé** le même jour, après un contrôle de **tout l'historique**
(`docs/scripts/scan_secrets_history.py` — aucune valeur de secret réelle). Détail en §8.

Version de référence : **Hermes Agent v0.21.3 (2026.9.14)**, upstream `97962358`.
Chemin de l'installation sur la machine d'origine : `%LOCALAPPDATA%\hermes` (Windows natif, pas WSL).

---

## Choisir sa version

| Version | Statut | Branche / Tag | Documentation |
|---|---|---|---|
| **1.1** | Originale, figée, téléchargeable | `main` / `v1.1-original` | [Release 1.1](../../releases/tag/v1.1-original) · [Wiki](../../wiki/Version-1.1) |
| **1.2** | Améliorée, **recommandée** | `v1.2-ameliorations` / `v1.2` | [Fiche détaillée](docs/IMPROVEMENTS.md) · [Changelog](docs/CHANGELOG-v1.2.md) · [Wiki](../../wiki/Version-1.2) |

Les deux versions sont **téléchargeables indépendamment**. La 1.1 n'est ni supprimée ni réécrite :
`main` reste au commit `1f1f089`. Ce que la 1.2 change exactement — et ce qu'elle ne change pas — est
détaillé dans [`docs/IMPROVEMENTS.md`](docs/IMPROVEMENTS.md).

**Branche par défaut du dépôt : `v1.2-ameliorations`** — la page d'accueil affiche donc ce README-ci.
`main` reste la 1.1, intacte et téléchargeable.

### Installation rapide (1.2)

```bash
git clone https://github.com/Antoine-Thomas/hermes-home-vision.git
cd hermes-home-vision
git checkout v1.2
```

Prérequis, étapes complètes et vérifications : [Wiki — Installation 1.2](../../wiki/Installation-1.2).

---

## 1. Qu'est-ce que c'est

Hermes Agent déployé en configuration **multi-profils** sur Windows 11. Trois profils isolés — chacun
son `config.yaml`, son `.env`, son bot Telegram, sa clé OmniRoute, son modèle par défaut et sa chaîne
de repli :

| Profil | Rôle | Modèle par défaut | Repli |
|---|---|---|---|
| `default` (bureau) | assistant opérateur : code, vidéo IA, WordPress, second cerveau | `eco` (routeur local, gratuit d'abord) | `nvidia-stack` → `deepseek/deepseek-flash` |
| `watch` | surveillance des services et automatisations | `nvidia-stack` (déterministe, gratuit) | `nemotron-super` → `auto/best-free` → `deepseek-flash` |
| `veille` | veille technologique : arXiv, HuggingFace, RSS, catalogue OpenRouter → synthèse datée | `nvidia-stack` | `nemotron-super` → `auto/best-free` |

Aucun credential n'est partagé entre profils : un bot Telegram n'appartient qu'à un seul profil, et
les clés du routeur sont dédiées (`hermes_watch`, `hermes_veille`).

---

## 2. Architecture

```
      ┌───────────────────┐      ┌───────────────────┐      ┌───────────────────┐
      │ default (bureau)  │      │       watch       │      │      veille       │
      │ config.yaml       │      │ config.yaml       │      │ config.yaml       │
      │ .env dédié        │      │ .env dédié        │      │ .env dédié        │
      │ bot Telegram 1    │      │ bot Telegram 2    │      │ bot Telegram 3    │
      │ clé OmniRoute 1   │      │ clé hermes_watch  │      │ clé hermes_veille │
      └─────────┬─────────┘      └─────────┬─────────┘      └─────────┬─────────┘
                │                          │                          │
                └──────────────┬───────────┴──────────────┬───────────┘
                               │                          │
                  ┌────────────▼───────────┐   ┌──────────▼───────────┐
                  │   OmniRoute   20128    │   │   Proxy NIM   20200  │
                  │   routeur LLM, combos  │   │   Nemotron local     │
                  └────────────┬───────────┘   └──────────────────────┘
                               │
      ┌────────────────────────┼──────────────────────────────────────┐
      │   RAG   8200           │   Backend   9119        SiYuan  6806 │
      │   index 2ᵉ cerveau     │   cœur Hermes         6 notebooks    │
      └────────────────────────┴──────────────────────────────────────┘
```

Services communs aux trois profils : **OmniRoute** (20128, routeur LLM et combos `eco` /
`nvidia-stack`), **proxy NIM** (20200, normalise les appels NVIDIA NIM : préfixes de modèles et
paramètres rejetés), **RAG** (8200, index vectoriel du second cerveau ; santé sur `/sante`),
**backend** (9119, API/dashboard), **SiYuan** (6806, base de connaissances, 6 notebooks).

**Supervision.** La tâche Windows `Hermes_Gateway_HealthCheck` (toutes les 5 minutes) vérifie que
chaque gateway est vivant (PID **et** commande `gateway run` — un PID recyclé ne compte pas), le
relève par `Start-ScheduledTask`, alerte sur Telegram **uniquement sur transition d'état** et écrit
une ligne `[battement]` par heure dans `logs/gateway-health.log`, ce qui donne un historique de
disponibilité sur 24 h.

**Cadence métier.** Le job cron `veille-hebdo` du profil `veille` part le lundi à 08h00, produit un
document SiYuan daté et le livre sur Telegram.

---

## 3. Structure du dépôt

```
%LOCALAPPDATA%\hermes\           racine = runtime Hermes
├── config.yaml                  config du profil default (modèle, repli, toolsets, plateformes)
├── .env.example                 modèle du profil default (noms de variables seuls)
├── SOUL.md / recovery_runbook.md consignes et procédures de reprise
├── memories\                    mémoire persistante : MEMORY.md, USER.md
├── skills\                      bibliothèque de skills du profil default (par catégories)
├── profiles\
│   ├── watch\                   config.yaml + .env.example + skills\ du profil watch
│   └── veille\                  config.yaml + .env.example + skills\ du profil veille
├── scripts\                     automatisations du runtime (healthcheck, tâches, A2A, vérification)
├── cron\                        jobs du profil default et leur historique d'exécution
├── gateway-service\             lanceurs VBS des gateways (démarrage masqué, hors Job Object)
├── omniroute-launch.vbs/.cmd    lancement silencieux d'OmniRoute (garde LISTENING)
└── docs\                        documentation, rapports, architecture, snapshots
    ├── ARCHITECTURE_HERMES.md   architecture consolidée + points ouverts
    ├── A2A_PREPARATION.md       procédure d'activation A2A (non activée)
    ├── architecture_2_agents.md décision d'architecture du pair local
    ├── README.md                rôle du dossier docs et notes de fusion
    ├── RAPPORT_*.md             rapports de session
    ├── snapshot\                baselines et copies de référence
    └── scripts\                 bootstrap.ps1, restore-from-github.md, push-to-github.md,
                                 baseline_t0.py, scan_secrets_history.py
```

Non versionné volontairement : `.env`, `auth.json`, `state.db*`, `sessions/`, `cache/`, `logs/`,
`backups/`, `pastes/`, `mcp-tokens/`, `whatsapp/`, `pairing/`, `runtime/`, `state/`, `gateway/`,
`data/` (venvs, modèles, index RAG), `hermes-agent/` (dépôt upstream imbriqué), `*_token.json`,
`*secret*.json`, `*.pem`, `*.key`.

---

## 4. Installation sur une nouvelle machine

### Prérequis

- **Windows 11**, PowerShell 5.1+ (fourni), connexion réseau.
- Python 3.11, Node.js, git, ripgrep, ffmpeg : **installés par l'installeur Hermes** — rien à
  préparer à la main (le paquet exige `Python >=3.11,<3.14`).

### Étapes

1. **Installer Hermes** (PowerShell, sans droits admin) — crée `%LOCALAPPDATA%\hermes`, son venv, son
   Git Bash embarqué et les outils :
   ```powershell
   iex (irm https://hermes-agent.nousresearch.com/install.ps1)
   hermes --version        # attendu : Hermes Agent v0.21.3
   ```

2. **Poser la configuration de ce dépôt** par-dessus le runtime. `git clone` refuse un dossier non
   vide et `%LOCALAPPDATA%\hermes` vient d'être créé : utiliser `git init` + `fetch` + `checkout`,
   qui écrivent les fichiers suivis **sans toucher** aux fichiers propres à la machine (`.env`,
   `state.db`, `cache/`) :
   ```powershell
   cd $env:LOCALAPPDATA\hermes
   git init -b main
   git remote add origin https://github.com/Antoine-Thomas/hermes-home-vision.git
   git fetch --depth 1 origin main
   git checkout -f -b main origin/main
   ```

3. **Créer les trois `.env`** depuis les modèles, puis les remplir (voir §5) :
   ```powershell
   copy .env.example .env
   copy profiles\watch\.env.example  profiles\watch\.env
   copy profiles\veille\.env.example profiles\veille\.env
   ```
   Sans cette étape, les gateways démarrent sans Telegram ni modèle.

4. **Recréer les tâches planifiées et démarrer les services** — c'est le rôle de
   `docs\scripts\bootstrap.ps1` (DryRun par défaut : il n'écrit rien sans `-Apply`) :
   ```powershell
   .\docs\scripts\bootstrap.ps1 -RepoUrl https://github.com/Antoine-Thomas/hermes-home-vision.git
   .\docs\scripts\bootstrap.ps1 -RepoUrl https://github.com/Antoine-Thomas/hermes-home-vision.git -Apply
   ```
   Il installe Hermes si besoin, pose la configuration du dépôt, copie les `.env.example`, recrée les
   **14 tâches** dont la cible est dans le dépôt, démarre les services dans l'ordre
   (SiYuan → OmniRoute → proxy NIM → RAG → backend → gateways) et écrit son journal dans
   `docs\snapshot\bootstrap_<horodatage>.log`. Il **liste** les 6 tâches dont le fichier cible est
   hors dépôt (`data\`, `C:\ProgramData\Hermes`, SiYuan, cua-driver) sans les créer.
   Procédure complète, y compris les étapes manuelles : `docs\scripts\restore-from-github.md`.

   *Variante manuelle* (si tu préfères ne pas lancer le bootstrap) — recréer les tâches avec les
   scripts du dépôt, puis démarrer les services dans l'ordre :
   ```powershell
   # tâches : les 3 gateways + le healthcheck
   .\scripts\creer_tache_gateway.ps1 -TaskName Hermes_Gateway        # (-DryRun par défaut, puis -Apply)
   .\scripts\creer_tache_gateway.ps1 -TaskName Hermes_Gateway_watch
   .\scripts\creer_tache_gateway.ps1 -TaskName Hermes_Gateway_veille
   .\scripts\check_gateways.ps1 -InstallTask -Apply
   ```
   puis **SiYuan** → **OmniRoute** (`omniroute-launch.vbs`) → **proxy NIM**
   (tâche `Hermes_NVIDIA_NIM_Proxy`) → **RAG** (`data\rag\serveur_rag.py` — attention : aucun lanceur
   n'existe pour celui-ci, cf. `ARCHITECTURE_HERMES.md` §7.9) → **backend**
   (`gateway-service\Hermes_Serve.vbs`) → gateways `default`, `watch`, `veille`.

5. **Vérifier** :
   ```powershell
   hermes profile list      # 3 profils, gateways running
   hermes doctor
   powershell -ExecutionPolicy Bypass -File .\scripts\verif_24h.ps1
   ```
   `verif_24h.ps1` compare l'état courant à la baseline T0 (`docs\snapshot\baseline_T0.json`). Cette
   baseline décrit **la machine d'origine** (notebooks SiYuan, fragments RAG, identifiants de cron) :
   sur une nouvelle machine, la régénérer d'abord avec `docs\scripts\baseline_t0.py`.

---

## 5. Secrets (NON versionnés)

Aucun `.env` n'est suivi par git (motifs `.env`, `.env.*`, `**/.env*`). Les modèles fournis ne
contiennent que des **noms** de variables, jamais de valeur.

| Fichier | Variables attendues |
|---|---|
| `.env` (profil `default`) | `OMNIROUTE_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL`, `SIYUAN_TOKEN`, `SIYUAN_URL`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `KIMI_API_KEY`, `NVIDIA_API_KEY_GEMMA4`, `EMAIL_*`, `WHATSAPP_*` |
| `profiles\watch\.env` | `OMNIROUTE_API_KEY` (clé dédiée `hermes_watch`, restreinte à 5 modèles), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL`, `DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `KIMI_API_KEY`, `NVIDIA_API_KEY_GEMMA4`, `WHATSAPP_*` |
| `profiles\veille\.env` | `OMNIROUTE_API_KEY` (clé dédiée `hermes_veille`, 7 modèles autorisés), `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL`, `SIYUAN_TOKEN`, `SIYUAN_URL` |

**Règles d'isolation**

- Un bot Telegram n'appartient qu'à **un** profil : ne jamais recopier un jeton d'un `.env` à
  l'autre. Deux gateways sur un même bot se neutralisent, et `hermes profile list` signale le
  « credential partagé » (c'est arrivé : le bloc `EMAIL_*` partagé entre `default` et `watch` a été
  retiré, le second gateway relevait la même boîte).
- Les clés `hermes_watch` / `hermes_veille` sont restreintes à une liste de modèles : elles ne
  donnent pas l'administration du routeur (qui exige la clé du poste).
- Le jeton SiYuan est **unique par workspace** : partagé entre `default` et `veille` par
  construction. Une rotation se fait en un seul endroit (Réglages → À propos), puis dans les deux
  `.env`.
- Pas de `hermes profile create <nom> --clone` ni `--clone-channels` : un profil cloné hérite de
  credentials qui ne lui appartiennent pas.
- **Nouvelles clés par machine** : une réinstallation ailleurs exige de **nouvelles** clés (bots,
  clé OmniRoute, jeton SiYuan). Réutiliser les mêmes casse l'isolation — deux machines répondraient
  sur le même bot.

**Rotation d'un secret, sans jamais l'afficher** :

```powershell
# Telegram : BotFather > /mybots > API Token > Revoke, puis poser la nouvelle valeur dans le .env
$t = (Select-String -Path "$env:LOCALAPPDATA\hermes\.env" -Pattern '^TELEGRAM_BOT_TOKEN=').Line -replace '^TELEGRAM_BOT_TOKEN=',''
curl.exe -s -o NUL -w "nouveau: %{http_code}\n" "https://api.telegram.org/bot$t/getMe"   # 200 attendu
```

---

## 6. Scripts source de vérité

| Script | Rôle |
|---|---|
| `scripts\check_gateways.ps1` | healthcheck des 3 gateways : détection ≤5 min, relevage, alerte sur transition, battement horaire |
| `scripts\creer_tache_gateway.ps1` | crée/durcit une tâche de gateway (logon + répétition courte, hors Job Object) — `-DryRun` par défaut |
| `scripts\verif_24h.ps1` | rapport T+24h contre la baseline T0 (SiYuan, RAG, cron, ticks horaires, gateways, alertes, A2A OFF) |
| `scripts\activer_a2a.ps1` / `desactiver_a2a.ps1` | activation / retour arrière A2A, paramétrés par profil et par port, diff affiché avant écriture |
| `scripts\probe_omniroute.py` | sonde les modèles gratuits et maintient le combo `eco` (ajout + élagage après 3 échecs terminaux, plancher 2 cibles) |
| `scripts\check_memory.ps1` | contrôle de saturation de la mémoire persistante (lecture seule) |
| `docs\scripts\baseline_t0.py` | mesure l'état de référence → `docs\snapshot\baseline_T0.json` |
| `docs\scripts\scan_secrets_history.py` | scanne **tout l'historique** git (tous les blobs) sur 6 motifs de secrets — contrôle avant push |

---

## 7. A2A (Agent-to-Agent)

**État : préparé, NON activé.** Plugin `a2a-platform` désactivé, aucun port en écoute (9900 et 9901
muets), aucune clé `A2A_*`, aucun pair déclaré. Les scripts d'activation et de rollback sont
paramétrés (`-LocalProfile`, `-LocalPort`, `-Profile`, `-Port`, `-PeerToken`, `-WriteEnvKeys`),
validés en `-SelfTest` sans toucher au `config.yaml`, et les jetons par paire sont générés mais
**non posés**. Checklist complète, blocs de configuration et commandes uniques :
`docs\A2A_PREPARATION.md`.

À retenir si l'activation se décide : `a2a_agents` est une **table indexée par nom de pair**, pas une
liste `- name:` ; `max_spawn_depth = 1` est le seul garde-fou anti-récursion ; `tasks/cancel` n'est
pas un vrai abort ; `a2a_orchestrate(mode="best")` renvoie la réponse **la plus longue**.

---

## 8. Sécurité

- **Aucun secret versionné** — ni `.env`, ni `state.db`, ni `auth.json`, ni clé privée. Contrôle
  reproductible :
  ```bash
  git ls-files | grep -E '\.env|state\.db|auth\.json' | grep -v '\.example$'   # attendu : vide
  python docs/scripts/scan_secrets_history.py --repo .                        # attendu : 0 occurrence
  ```
- **Historique purgé.** L'ancien dépôt de documentation contenait, dans un fichier pourtant nommé
  `snapshot/env.pre_update.redacted`, un **jeton Telegram actif** ; le même historique portait aussi
  `snapshot/.env`, `snapshot/state.db` et des copies de `.env` (clés API incluses). Tous ces blobs
  ont été **retirés de l'historique par `git filter-repo`** avant la fusion : le dépôt publié ne
  contient plus aucune valeur, y compris dans ses commits passés. Le fichier est recréé comme **trace
  neutralisée** (`docs/snapshot/env.pre_update.redacted`, placeholders seulement). Le bot concerné
  reste actif en local — seul le blob a quitté l'historique.
- Conséquence assumée : les SHA des commits de l'ancien dépôt de documentation ont changé. Les
  identifiants cités dans les rapports restent lisibles comme références historiques.
- **Contrôle rejoué le 21/09/2026** pour la version 1.2, sur l'historique complet : `objets=2494`,
  `blobs=1564`, `volume=11.2 Mo` — `telegram_bot_token: 0`, `google_api_key: 0`, `github_token: 0`,
  `huggingface_token: 0`, `pem_private_key: 0`, et **1 seul blob `sk_*` classé placeholder**
  (16 caractères, exemple pédagogique dans une référence de skill). Conclusion du script :
  `aucune valeur de secret reelle dans l'historique`.
- **Visibilité remise en cohérence le 21/09/2026** : le dépôt a été trouvé **public** alors que sa
  description annonçait « Privé » et que la règle ci-dessous proscrit une publication sans re-scan.
  Il a été **repassé en privé** après l'audit ci-dessus, et sa description mise à jour.
- Ne jamais rendre ce dépôt public sans re-scan : un dépôt privé n'est pas un coffre, tout ce qui y
  entre reste dans l'historique. Ce contrôle a été rejoué le 21/09/2026 pour la 1.2 et doit être
  rejoué avant toute publication ultérieure.

---

## 9. Documentation

| Document | Contenu |
|---|---|
| `docs\ARCHITECTURE_HERMES.md` | architecture consolidée : 3 profils, scripts, tâches planifiées, points de fuite connus, dette A2A (11 points), points ouverts, mode observation 24 h |
| `docs\A2A_PREPARATION.md` | procédure d'activation A2A : état mesuré, checklist, blocs de config, commandes, rollback, points d'attention |
| `docs\architecture_2_agents.md` | décision d'architecture du pair local bureau ↔ veille |
| `docs\README.md` | rôle du dossier `docs`, notes de fusion, notes de sécurité |
| `docs\RAPPORT_*.md`, `docs\INSTALL_LOG.md` | rapports de session et journal d'installation, commande par commande |
| `docs\snapshot\` | baselines T0, configs de référence, diffs des scripts livrés |
| `docs\scripts\push-to-github.md` | procédure de publication (dépôt privé, contrôles bloquants) |
| `docs\scripts\bootstrap.ps1` | remise en route sur une machine vierge — DryRun par défaut, `-Apply` pour exécuter |
| `docs\scripts\restore-from-github.md` | restauration pas-à-pas : bots Telegram, clés OmniRoute, jeton SiYuan, `data/`, tâches hors dépôt |
| `docs\scripts\baseline_t0.py` | mesure la baseline T0 (notebooks SiYuan, fragments RAG, cron) — à régénérer sur une nouvelle machine |
| `docs\IMPROVEMENTS.md` | fiche détaillée des améliorations 1.1 → 1.2 : état réel de chaque version, bénéfices, fichiers concernés |
| `docs\CHANGELOG-v1.2.md` | changelog de la version 1.2 (Keep a Changelog, convention SemVer) |

### Voir aussi

- [`docs/IMPROVEMENTS.md`](docs/IMPROVEMENTS.md) — fiche détaillée des améliorations v1.1 → v1.2
- [`docs/CHANGELOG-v1.2.md`](docs/CHANGELOG-v1.2.md) — changelog de la 1.2
- [Wiki du dépôt](../../wiki) — accueil, installation 1.2, améliorations détaillées, migration
  depuis la 1.1, archives 1.1, FAQ

---

## Licence et contact

**Aucune licence déclarée.** Le dépôt ne contient aucun fichier `LICENSE`, ni en 1.1 ni en 1.2 : son
contenu est donc sous le régime par défaut du droit d'auteur (« tous droits réservés »), sans droit
d'usage, de modification ou de redistribution accordé au-delà de ce que permettent les conditions de
GitHub. Usage personnel. Les composants tiers (Hermes Agent, OmniRoute, SiYuan, NVIDIA NIM) restent
sous leurs licences respectives.

Contact : Antoine-Thomas — <https://github.com/Antoine-Thomas>
