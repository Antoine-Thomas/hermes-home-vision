# Hermes Home Vision

> **Version actuelle : `1.4`** — Hermes Aegis (préparée, non publiée)
> **Version stable précédente : `1.3`** — Hermes Psychopomp
> **Version précédente : `1.2`** — version améliorée
> **Version originale : `1.1`** — figée, téléchargeable

> Installation personnelle de Hermes Agent — 4 profils isolés, supervision continue, veille automatique,
> sécurité vérifiable.

Dépôt **public** : `https://github.com/Antoine-Thomas/hermes-home-vision` — il contient **tout** : le
runtime Hermes (configuration, profils, skills, scripts) **et** sa documentation rangée sous `docs/`.
Un seul `git clone` restaure l'ensemble. L'historique a été audité le 21/09/2026 par
`docs/scripts/scan_secrets_history.py` : aucune valeur de secret réelle. Détail en §8.

Version de référence : **Hermes Agent v0.21.5+7519.ga928a95**, config version 49, upstream `a928a959e3`.
Chemin de l'installation sur la machine d'origine : `%LOCALAPPDATA%\hermes` (Windows natif, pas WSL).

---

## ANIMA 0.1 — supervision et mémoire hiérarchique

Sous-système qui enveloppe Hermes : **Hermes = le moteur, ANIMA = le système
intégré**. ANIMA surveille 15 composants (OmniRoute, RAG, SiYuan, Ollama, jobs,
coûts, repli) et route chaque question vers la bonne source de mémoire (SiYuan →
RAG → mémoire native) via JEV (repli regex) et le plugin `anima-memoire-router`.

- [Architecture](docs/ANIMA_ARCHITECTURE.md) — 4 couches, flux E2E, ports.
- [Modules](docs/ANIMA_MODULES.md) — composants + health checks.
- [Certification](docs/ANIMA_CERTIFICATION.md) — état, tests, SHA256.
- [Crypto](docs/ANIMA_CRYPTO.md) — spécification du futur module blockchain.

Flux E2E : message → profil → routeur (JEV/regex) → LLM (combo) → RAG → JEV → réponse.

## Choisir sa version

| Version | Statut | Branche / Tag | Documentation |
|---|---|---|---|
| **1.1** | Originale, figée, téléchargeable | tag `v1.1-original` | [Release 1.1](../../releases/tag/v1.1-original) · [Wiki](../../wiki/Version-1.1) |
| **1.2** | Stable | `v1.2-ameliorations` / `v1.2` | [Fiche détaillée](docs/IMPROVEMENTS.md) · [Changelog](docs/CHANGELOG-v1.2.md) · [Wiki](../../wiki/Version-1.2) |
| **1.3** | **Stable (recommandée)** | tag `v1.3` | [Changelog v1.3](docs/CHANGELOG-v1.3.md) · [Release 1.3](../../releases/tag/v1.3) |
| **1.4** | **Préparée, non publiée** — bloqueurs B1/B2 ouverts | `main`, **aucun tag** | [Architecture Aegis](docs/ARCHITECTURE_AEGIS.md) · [Changelog v1.4](docs/CHANGELOG-v1.4.md) |

Les quatre versions restent **téléchargeables indépendamment** : la 1.1 sur le tag `v1.1-original`, la 1.2
sur la branche `v1.2-ameliorations` (tag `v1.2`), la 1.3 sur le tag `v1.3`, la 1.4 sur `main` — **aucun tag
1.4 n'existe**. Aucune version n'est supprimée ni réécrite.

**Branche par défaut du dépôt : `main`** — elle porte la documentation de la **1.4 Aegis, préparée et non
publiée** ; la version stable reste la **1.3** (tag `v1.3`), et la 1.4 ne sera taguée qu'après ses deux
bloqueurs (voir §10).

### Installation rapide (1.3)

```bash
git clone https://github.com/Antoine-Thomas/hermes-home-vision.git
cd hermes-home-vision
git checkout v1.3
```

Prérequis, étapes complètes et vérifications : [Wiki — Installation 1.2](../../wiki/Installation-1.2)
(la page wiki 1.3 reste à écrire ; le détail de la 1.3 est dans `docs/CHANGELOG-v1.3.md`).

---

## 1. Qu'est-ce que c'est

Hermes Agent déployé en configuration **multi-profils** sur Windows 11. Quatre profils isolés — chacun
son `config.yaml`, son `.env`, son bot Telegram, sa clé OmniRoute, son modèle par défaut et sa chaîne
de repli :

| Profil | Rôle | Modèle par défaut | Repli |
|---|---|---|---|
| `default` (bureau) | assistant opérateur : code, vidéo IA, WordPress, second cerveau | `eco` (routeur local, gratuit d'abord) | `nvidia-stack` → `deepseek/deepseek-flash` |
| `veille` | veille technologique : arXiv, HuggingFace, RSS, catalogue OpenRouter → synthèse datée | `nvidia-stack` | `nemotron-super` → `auto/best-free` |
| `watch` | surveillance des services et automatisations | `nvidia-stack` (déterministe, gratuit) | `nemotron-super` → `auto/best-free` → `deepseek-flash` |
| `docs-writer` | rédaction documentaire (cwd `C:/Users/searc/hermes-docs`) | `deepseek-flash` (direct) | — |

Aucun credential n'est partagé entre profils : un bot Telegram n'appartient qu'à un seul profil, et
les clés du routeur sont dédiées (`hermes_watch`, `hermes_veille`). Le profil `docs-writer` ne porte ni
bot Telegram ni clé OmniRoute : il appelle directement l'API DeepSeek.

---

## Nouveautés v1.3

- **Skill TypeSafe Jev** — 3 primitives : `noul` (juger), `choice` (trancher), `score` (noter).
- **Wiki L1 non-agentique** — 17 pages FR (13 concepts + 4 entités) compilées par un script Python,
  synchronisées dans SiYuan.
- **Chaîne de repli gratuite** — `eco` → `nvidia-stack` → `free-openrouter` → `deepseek-flash`.
- **Retrait de `auto/best-reasoning`** — alias payant mesuré (résout vers un modèle Opus), retiré de la
  chaîne de repli.

Détail complet, fichiers concernés et notes de migration : [`docs/CHANGELOG-v1.3.md`](docs/CHANGELOG-v1.3.md).

---

## 2. Architecture

```
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║ COUCHE 1 — PROFILS (isolation)                                                            ║
║                                                                                           ║
║   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐          ║
║   │     default    │  │      watch     │  │     veille     │  │   docs-writer  │          ║
║   │  config.yaml   │  │  config.yaml   │  │  config.yaml   │  │  config.yaml   │          ║
║   │  .env dédié    │  │  .env dédié    │  │  .env dédié    │  │  .env dédié    │          ║
║   │  bot Telegram  │  │  bot Telegram  │  │  bot Telegram  │  │  (pas de bot)  │          ║
║   │ clé OmniRoute  │  │ clé hermes_    │  │ clé hermes_    │  │  DeepSeek seul │          ║
║   │                │  │      watch     │  │     veille     │  │                │          ║
║   └───────┬────────┘  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘          ║
║           │                   │                   │                   │                   ║
║   ACL de chaque .env : Système(F) · Administrateurs(F) · searc(F) — non héritées          ║
╚═══════════╪═══════════════════╪═══════════════════╪═══════════════════╪═══════════════════╝
            └───────────────────┴─────────┬─────────┴───────────────────┘
                                          │
╔═════════════════════════════════════════▼═════════════════════════════════════════════════╗
║ COUCHE 2 — ROUTAGE (LLM)                                                                  ║
║                                                                                           ║
║   ┌────────────────────────────────────┐        ┌────────────────────────────────────┐    ║
║   │        OmniRoute   20128           │        │        Proxy NIM   20200           │    ║
║   │  routeur LLM, combos + repli       │        │  Nemotron local (NVIDIA NIM)       │    ║
║   │  ordonné :                         │        │  normalise préfixes de modèles     │    ║
║   │    free-openrouter                 │        │  et paramètres rejetés             │    ║
║   │    nvidia-stack                    │        └────────────────────────────────────┘    ║
║   │    deepseek                        │                                                   ║
║   └────────────────────────────────────┘                                                   ║
║                                                                                           ║
║   Principe : gratuit d'abord, payant en dernier — chaque bascule est tracée (§5).          ║
╚═════════════════════════════════════════╪═════════════════════════════════════════════════╝
                                          │
╔═════════════════════════════════════════▼═════════════════════════════════════════════════╗
║ COUCHE 3 — CERVEAU (mémoire)                                                              ║
║                                                                                           ║
║   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                               ║
║   │   RAG   8200  │   │ Hermes  CLI   │   │ SiYuan   6806 │                               ║
║   │  index 2ᵉ     │   │  dashboard    │   │  base de      │                               ║
║   │  cerveau      │   │  (sans 9119)  │   │  connaissances│                               ║
║   └───────┬───────┘   └───────────────┘   └───────────────┘                               ║
║           │                                                                               ║
║   ┌───────▼────────────────────────────┐   ┌────────────────────────────────────────┐     ║
║   │  JEV  ·  OpenRouter                │   │  Laya  ·  ONNX local (CPU)             │     ║
║   │  décision typée : noul/choice/score│   │  accélérateur gratuit, hors ligne      │     ║
║   │  route wiki (L1) · RAG (L2)        │   │  JEV reste le décideur principal        │     ║
║   └────────────────────────────────────┘   └────────────────────────────────────────┘     ║
╚═════════════════════════════════════════╪═════════════════════════════════════════════════╝
                                          │
╔═════════════════════════════════════════▼═════════════════════════════════════════════════╗
║ COUCHE 4 — SÉCURITÉ (Aegis)                                                               ║
║                                                                                           ║
║   ACL minimales      secrets hors git      Wazuh           ports Windows                  ║
║   ─────────────      ─────────────────     ───────────     ──────────────────────         ║
║   3 ACE par .env     0 secret versionné    manager 55085    plage réservée 54985-55084    ║
║   non héritées       12 sauvegardes        indexer 9200    → remap, jamais de bind forcé  ║
║   CodexSandboxUsers  hors du dépôt         allowlist à jour                           ║
║   retirée            (hermes-secrets-                                                     ║
║                       backup\)                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
```

**Les quatre couches.** ① **Profils** — quatre environnements isolés (`default`, `watch`, `veille`,
`docs-writer`), chacun son `config.yaml`, son `.env` et ses credentials. ② **Routage** — OmniRoute
(20128) et le proxy NIM (20200) : gratuit d'abord, payant en dernier, bascules tracées. ③ **Cerveau** —
RAG (8200), SiYuan (6806), JEV (décision typée via OpenRouter) et Laya (accélérateur
ONNX local). ④ **Sécurité** — ACL minimales, secrets hors git, Wazuh, plages de ports Windows.

Détail complet, limites mesurées et commandes de vérification :
[`docs/ARCHITECTURE_AEGIS.md`](docs/ARCHITECTURE_AEGIS.md).

**JEV** est le skill TypeSafe d'aide à la décision (`noul` juger, `choice` trancher, `score` noter). Il
route entre le **wiki** (L1, connaissances compilées hébergées dans SiYuan) et le **RAG** (L2, recherche
brute) pour trancher les choix rapides : 2 à 5 options, critères objectifs, décision récurrente.
Modèle `typesafe/jev-1.13` via OpenRouter. **Vérifié le 27/09/2026** : route `wiki`, confiance 0,98,
0,48 s, 3,54e-05 $ par appel. Limite : score sur 10 niveaux maximum. Il ne remplace pas le modèle
principal : il décide à sa place sur les questions cadrées. Si JEV est injoignable,
`wiki/scripts/jev_router.py` bascule sur la route `rag` avec `route_source: "fallback_local"` et sort en
code **2** — la dégradation est visible, jamais silencieuse. Voir `wiki/concepts/jev.md`.

**Services communs** aux profils : **OmniRoute** (20128, routeur LLM, combos `eco` / `nvidia-stack` /
`free-openrouter` / `deepseek`), **proxy NIM** (20200, normalise les appels NVIDIA NIM : préfixes de
modèles et paramètres rejetés), **RAG** (8200, index vectoriel du second cerveau ; santé sur `/sante`,
2 934 fragments au 06/10/2026), **SiYuan** (6806, base de
connaissances, **7 notebooks**, local seulement). **Wazuh** complète la pile côté sécurité : API
manager `127.0.0.1:55085` (remap du 55000, cf. §8) et indexer `0.0.0.0:9200`.

**Supervision.** Un **seul gateway multiplexé** sert **trois des quatre profils** : la tâche Windows
`Hermes_Gateway` lance le gateway du profil `default`, et `gateway.multiplex_profiles: true`
(`config.yaml`) fait servir les profils `watch` et `veille` par ce même processus — il n'existe
**aucune** tâche `Hermes_Gateway_watch` ni `Hermes_Gateway_veille` séparée. Le profil `docs-writer`
n'est pas servi par le gateway : c'est un profil de rédaction en ligne de commande, sans canal de
messagerie. La tâche
`Hermes_Gateway_HealthCheck` (toutes les 5 minutes) vérifie que le gateway est vivant (PID **et**
commande `gateway run` — un PID recyclé ne compte pas), le relève par `Start-ScheduledTask`, alerte
sur Telegram **uniquement sur transition d'état** et écrit une ligne `[battement]` par heure dans
`logs/gateway-health.log`, ce qui donne un historique de disponibilité sur 24 h.

> **Note — multiplexage des profils.** Les profils `watch` et `veille` sont servis par le
> multiplexeur du gateway `default` (`config.yaml` → `gateway.multiplex_profiles: true`) : un seul
> processus gateway, trois configurations de profil, un seul point de supervision. Ne pas recréer une
> tâche de gateway par profil — un second gateway sur le même bot Telegram se neutralise.

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
│   ├── veille\                  config.yaml + .env.example + skills\ du profil veille
│   └── docs-writer\             config.yaml + .env.example (profil de rédaction, sans bot)
├── scripts\                     automatisations du runtime (healthcheck, tâches, A2A, vérification)
├── cron\                        jobs du profil default et leur historique d'exécution
├── gateway-service\             lanceurs VBS des gateways (démarrage masqué, hors Job Object)
├── omniroute-launch.vbs/.cmd    lancement silencieux d'OmniRoute (garde LISTENING)
└── docs\                        documentation, rapports, architecture, snapshots
    ├── ARCHITECTURE_AEGIS.md    architecture 1.4 en 4 couches (profils, routage, cerveau, sécurité)
    ├── ARCHITECTURE_HERMES.md   architecture consolidée + points ouverts
    ├── A2A_PREPARATION.md       procédure d'activation A2A (non activée)
    ├── architecture_2_agents.md décision d'architecture du pair local
    ├── CHANGELOG-v1.4.md        changelog de la 1.4 Aegis (préparée, non publiée)
    ├── CHANGELOG-v1.4-draft.md  post-mortem de la production du volet 6 (document de travail)
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
   hermes --version        # attendu : Hermes Agent v0.21.5+7519.ga928a95
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
   **12 tâches** dont la cible est dans le dépôt (un **seul** gateway multiplexé, pas un par profil),
   démarre les services dans l'ordre (SiYuan → OmniRoute → proxy NIM → RAG → backend → gateway) et
   écrit son journal dans `docs\snapshot\bootstrap_<horodatage>.log`. Il **liste** les 6 tâches dont
   le fichier cible est hors dépôt (`data\`, `C:\ProgramData\Hermes`, SiYuan, cua-driver) sans les
   créer.
   Procédure complète, y compris les étapes manuelles : `docs\scripts\restore-from-github.md`.

   *Variante manuelle* (si tu préfères ne pas lancer le bootstrap) — recréer les tâches avec les
   scripts du dépôt, puis démarrer les services dans l'ordre :
   ```powershell
   # tâches : 1 gateway multiplexé (3 profils) + le healthcheck
   .\scripts\creer_tache_gateway.ps1 -TaskName Hermes_Gateway        # (-DryRun par défaut, puis -Apply)
   .\scripts\check_gateways.ps1 -InstallTask -Apply
   ```
   puis **SiYuan** → **OmniRoute** (`omniroute-launch.vbs`) → **proxy NIM**
   (tâche `Hermes_NVIDIA_NIM_Proxy`) → **RAG** (`data\rag\serveur_rag.py` — attention : aucun lanceur
   n'existe pour celui-ci, cf. `ARCHITECTURE_HERMES.md` §7.9) → gateway multiplexé (`default` + `watch` + `veille`).

5. **Vérifier** :
   ```powershell
   hermes profile list      # 3 profils servis par 1 gateway multiplexé
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
| `profiles\docs-writer\.env` | `DEEPSEEK_API_KEY` (seul credential : profil de rédaction, sans bot Telegram ni clé OmniRoute) |

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
| `scripts\check_gateways.ps1` | healthcheck des 3 profils servis par le gateway multiplexé : détection ≤5 min, relevage, alerte sur transition, battement horaire |
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
- **Visibilité** : le dépôt est **public** depuis le 22/09/2026, après audit complet de l'historique
  (`scan_secrets_history.py`, historique purgé par `git filter-repo` le 21/09). Le dépôt ne contient
  aucune valeur de secret, ni dans les fichiers suivis, ni dans les commits passés.
- **ACL des `.env` (couche Aegis)** — les quatre fichiers de secrets (`default`, `watch`, `veille`,
  `docs-writer`) portent exactement **3 ACE non héritées** : `Système(F)` · `Administrateurs(F)` ·
  `searc(F)`. La ACE héritée `CodexSandboxUsers:(I)(RX)` — posée par un outil tiers, qui laissait un
  groupe applicatif lire les secrets — a été retirée des quatre :
  ```powershell
  icacls "<fichier>.env" /inheritance:r /grant:r "Système:(F)" "Administrateurs:(F)" "%USERNAME%:(F)"
  ```
  Vérification : `icacls <fichier>` → 3 ACE `(F)`, 0 `(I)`, 0 trace `CodexSandboxUsers`.
- **12 sauvegardes `.env` isolées hors du dépôt** — rangées dans
  `%USERPROFILE%\hermes-secrets-backup\<profil>\` (arborescence miroir par profil : sans elle, les
  fichiers homonymes s'écrasaient), avec ACL restreinte et intégrité prouvée par `sha256` identique
  avant/après. Un motif `.gitignore` empêche de **publier** un `.env`, pas de le **lire** : une copie
  laissée dans l'arbre du dépôt restait une surface (zip, indexation, sauvegarde de dossier).
- **Hygiène du dépôt** — `.gitignore` durci : `/hermes-agent/` **ancré** (le motif non ancré avalait
  aussi le skill bundled `skills/autonomous-ai-agents/hermes-agent/`, resté hors du dépôt et donc
  absent du point de restauration), motif `*.bak_*` / `**/*.bak_*` (l'ancien `.bak_` littéral ne
  matchait qu'un fichier nommé exactement `.bak_`) et `profiles/*/skills/`. Quatre fichiers `.bak`
  sortis de l'index (`git rm --cached`), **conservés sur disque**.
- **Wazuh** — manager : API sur `127.0.0.1:55085`, indexer sur `0.0.0.0:9200`, les deux déclarés dans
  `ports.allowlist`. Le port d'API du conteneur reste `55000`, mais Windows réserve la plage TCP
  **54985-55084** (mesuré : `netsh int ipv4 show excludedportrange protocol=tcp`) : le port est
  **remappé** juste au-dessus plutôt que forcé (`"127.0.0.1:55085:55000"`). Preuve de vie de l'API :
  `curl -sk -X POST "https://localhost:55085/security/user/authenticate?raw=true"` → **200 + un jeton d'API** (préfixe `ey`).
- **Règle** : avant toute modification de la visibilité (public → privé ou l'inverse), rejouer
  `python docs/scripts/scan_secrets_history.py --repo .` et vérifier 0 occurrence. Un dépôt n'est pas
  un coffre : tout ce qui entre reste dans l'historique.

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
| `docs\scripts\push-to-github.md` | procédure de publication (dépôt public, contrôles bloquants) |
| `docs\scripts\bootstrap.ps1` | remise en route sur une machine vierge — DryRun par défaut, `-Apply` pour exécuter |
| `docs\scripts\restore-from-github.md` | restauration pas-à-pas : bots Telegram, clés OmniRoute, jeton SiYuan, `data/`, tâches hors dépôt |
| `docs\scripts\baseline_t0.py` | mesure la baseline T0 (notebooks SiYuan, fragments RAG, cron) — à régénérer sur une nouvelle machine |
| `docs\IMPROVEMENTS.md` | fiche détaillée des améliorations 1.1 → 1.2 : état réel de chaque version, bénéfices, fichiers concernés |
| `docs\CHANGELOG-v1.2.md` | changelog de la version 1.2 (Keep a Changelog, convention SemVer) |
| `docs\ARCHITECTURE_AEGIS.md` | architecture de la 1.4 « Aegis » : les **4 couches** (profils, routage, cerveau, sécurité), principes directeurs, limites connues et contournements, commandes de vérification |
| `docs\CHANGELOG-v1.4.md` | changelog de la 1.4 (préparée, non publiée) : sécurité et ACL, Wazuh, JEV, Laya, skills, RAG, dépendances, bloqueurs B1/B2 |

### Voir aussi

- [`docs/IMPROVEMENTS.md`](docs/IMPROVEMENTS.md) — fiche détaillée des améliorations v1.1 → v1.2
- [`docs/CHANGELOG-v1.2.md`](docs/CHANGELOG-v1.2.md) — changelog de la 1.2
- [`docs/ARCHITECTURE_AEGIS.md`](docs/ARCHITECTURE_AEGIS.md) — architecture de la 1.4 en 4 couches
- [`docs/CHANGELOG-v1.4.md`](docs/CHANGELOG-v1.4.md) — changelog de la 1.4 (préparée, non publiée)
- [Wiki du dépôt](../../wiki) — accueil, installation 1.2, améliorations détaillées, migration
  depuis la 1.1, archives 1.1, FAQ

---

## 10. Bloqueurs de publication de la v1.4

La 1.4 « Hermes Aegis » est **préparée, non publiée** : aucun tag, aucune release. Deux bloqueurs
l'interdisent (état mesuré le 27/09/2026) :

| # | Bloqueur | État mesuré |
|---|---|---|
| **B1** | **MP4 livrable absent** (ex-« tronqué ») | `Desktop\hermes tuto\tutotete20_jev_llmwiki.mp4` : **introuvable** — dossier supprimé, corbeille vide, aucune copie ailleurs. Le tutoriel JEV / LLM Wiki doit être **réassemblé** (`assemble_v6.py`). |
| **B2** | **Watchdog volet6 en pause** | Tâche planifiée Windows `volet6-watchdog` = `Disabled` ; cron job Hermes `4a646bb6eab4` (`every 15m`) = `enabled: false`, `paused_at 2026-09-23T13:10:09+02:00`, `last_status: ok` — en pause depuis le 23/09. |

Détail, conséquences et checklist de publication : [`docs/CHANGELOG-v1.4.md`](docs/CHANGELOG-v1.4.md).

---

## Licence et contact

**Aucune licence déclarée.** Le dépôt ne contient aucun fichier `LICENSE`, ni en 1.1 ni en 1.2 : son
contenu est donc sous le régime par défaut du droit d'auteur (« tous droits réservés »), sans droit
d'usage, de modification ou de redistribution accordé au-delà de ce que permettent les conditions de
GitHub. Usage personnel. Les composants tiers (Hermes Agent, OmniRoute, SiYuan, NVIDIA NIM) restent
sous leurs licences respectives.

Contact : Antoine-Thomas — <https://github.com/Antoine-Thomas>
