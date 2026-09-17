# Hermes Agent — installation personnelle

Copie de sauvegarde **privée** de l'installation Hermes Agent de ce poste (Windows 11), poussable
sur un dépôt GitHub privé et restaurable ailleurs. Ce dépôt ne contient **que de la configuration,
des skills, des scripts et des profils** — aucun secret, aucune base de sessions, aucun binaire de
l'installation upstream.

Version de référence : **Hermes Agent v0.21.3 (2026.9.14)**, upstream `97962358`, install git.
Chemin de l'installation sur cette machine : `%LOCALAPPDATA%\hermes` (Windows natif, pas WSL).

---

## 1. Qu'est-ce que c'est

Trois profils Hermes isolés (leur propre `config.yaml`, leur propre `.env`, leur propre gateway) :

| Profil | Rôle | Modèle par défaut | Gateway |
|---|---|---|---|
| `default` (bureau) | opérateur : code, vidéo IA, WordPress, second cerveau | `eco` (OmniRoute, gratuit d'abord) | tâche `Hermes_Gateway`, port local |
| `watch` | second profil historique : surveillances et automatisations, copie complète des skills | `nvidia-stack` (OmniRoute, gratuit) | tâche `Hermes_Gateway_watch` |
| `veille` | veille techno (arXiv, HuggingFace, RSS, OpenRouter) → synthèse datée + alertes | `nvidia-stack` (OmniRoute, gratuit) | tâche `Hermes_Gateway_veille` |

Briques partagées, appelées par les trois profils :

| Service | Adresse | Rôle |
|---|---|---|
| OmniRoute | `127.0.0.1:20128` | routeur LLM (combos `eco`, `nvidia-stack`), clés API dédiées par profil |
| Proxy NIM | `127.0.0.1:20200` | normalise les appels NVIDIA NIM (préfixes de modèles, params rejetés) |
| RAG | `127.0.0.1:8200` | second cerveau : index vectoriel (`/sante`, `/search`), e5-base, ~2 400 fragments |
| SiYuan | `127.0.0.1:6806` | base de connaissances (6 notebooks : journal, veille, video-ia, hermes-projets…) |
| Backend | `127.0.0.1:9119` | API/dashboard Hermes |

Surveillance et cadence : tâche Windows `Hermes_Gateway_HealthCheck` (PT5M) qui teste chaque gateway
(PID vivant **et** commande `gateway run`), le relève par `Start-ScheduledTask`, alerte sur Telegram
**uniquement sur transition d'état** et journalise une ligne `[battement]` par heure dans
`logs/gateway-health.log`. Côté `veille`, un job cron hebdomadaire (`veille-hebdo`, lundi 08h00)
produit un document SiYuan et le livre sur Telegram.

---

## 2. Installation sur une nouvelle machine

Prérequis : **Windows 11**, PowerShell 5.1+ (fourni), et une connexion réseau. Python, Node.js, git,
ripgrep et ffmpeg **sont installés par l'installeur Hermes** — pas besoin de les préparer à la main
(Python 3.11 est requis par le paquet : `requires-python >=3.11,<3.14`).

1. **Installer Hermes Agent** (PowerShell, sans admin) :
   ```powershell
   iex (irm https://hermes-agent.nousresearch.com/install.ps1)
   ```
   L'installeur crée `%LOCALAPPDATA%\hermes` (runtime, `hermes-agent\`, venv, `bin\`, MinGit).
   Vérifier : `hermes --version` → `Hermes Agent v0.21.3`.
   *Pour une version figée :* `git clone https://github.com/NousResearch/hermes-agent` puis
   `uv pip install -e ".[all]"` dans le venv de l'installation.

2. **Poser la configuration de ce dépôt** par-dessus le runtime. `git clone` refuse un dossier
   non vide, et `%LOCALAPPDATA%\hermes` vient d'être créé par l'installeur : utiliser
   `git init` + `fetch` + `checkout`, qui écrivent les fichiers suivis **sans supprimer** les
   fichiers propres à la machine (`.env`, `state.db`, `cache/`) :
   ```powershell
   cd $env:LOCALAPPDATA\hermes
   git init -b main
   git remote add origin https://github.com/<ton-user>/hermes-home.git
   git fetch --depth 1 origin main
   git checkout -f -b main origin/main
   ```
   C'est exactement ce que fait `scripts\bootstrap.ps1` (dépôt `hermes-install`, §Phase 3).

3. **Créer les `.env`** à partir des modèles du dépôt, puis les remplir (voir §3) :
   ```powershell
   copy .env.example .env
   copy profiles\watch\.env.example  profiles\watch\.env
   copy profiles\veille\.env.example profiles\veille\.env
   ```
   Aucun `.env` n'est versionné : sans cette étape, les gateways démarrent sans Telegram ni modèle.

4. **Restaurer les tâches planifiées et les services** avec le bootstrap du dépôt de documentation
   (`Desktop\hermes_install\scripts\bootstrap.ps1`, DryRun par défaut) :
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 -RepoUrl <url-du-depot-home>
   ```
   Il enchaîne : prérequis → structure → `.env` → tâches planifiées → services → vérification.

5. **Vérifier** :
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\scripts\verif_24h.ps1     # comparaison à la baseline T0
   hermes profile list                                                  # 3 profils, gateways running
   hermes doctor
   ```

6. **Mettre à jour la baseline** après l'installation sur la nouvelle machine : les valeurs de
   `snapshot\baseline_T0.json` (dépôt `hermes-install`) sont celles de la machine d'origine
   (notebooks SiYuan, fragments RAG, ids de cron) — les régénérer avec
   `scripts\baseline_t0.py` avant d'utiliser `verif_24h.ps1` comme contrôle quotidien.

---

## 3. Secrets (NON versionnés)

**Aucun `.env` n'est suivi par git** (motifs `.env`, `.env.*`, `**/.env*` dans `.gitignore`).
Les modèles fournis (`.env.example`) ne contiennent que des **noms de variables**, jamais de valeur.

### Racine — `.env` (profil `default`)

| Variable | Rôle |
|---|---|
| `OMNIROUTE_API_KEY` | clé OmniRoute du poste (sert aussi de jeton d'administration sur `/api/keys`) |
| `TELEGRAM_BOT_TOKEN` | bot du profil (`@Hermes_assistante_2026_bot`) |
| `TELEGRAM_ALLOWED_USERS` | liste blanche des chats autorisés (id numérique) |
| `TELEGRAM_HOME_CHANNEL` | canal de livraison par défaut des jobs cron |
| `SIYUAN_TOKEN` | jeton d'API du workspace SiYuan |
| `SIYUAN_URL` | `http://127.0.0.1:6806` |
| `DEEPSEEK_API_KEY` | dernier étage de repli payant (`deepseek-flash`) |
| `OPENROUTER_API_KEY`, `KIMI_API_KEY`, `NVIDIA_API_KEY_GEMMA4` | providers secondaires (vision, fallback) |
| `EMAIL_ADDRESS`, `EMAIL_PASSWORD`, `EMAIL_IMAP_HOST`, `EMAIL_SMTP_HOST`, `EMAIL_ALLOWED_USERS`, `EMAIL_POLL_INTERVAL` | canal email du gateway (IMAP/SMTP, mot de passe d'application) |
| `WHATSAPP_ENABLED`, `WHATSAPP_MODE`, `WHATSAPP_ALLOWED_USERS`, `WHATSAPP_CLOUD_PHONE_NUMBER_ID`, `WHATSAPP_CLOUD_ACCESS_TOKEN` | bridge WhatsApp (désactivé si non appairé) |

### `profiles\watch\.env` (profil `watch`)

`OMNIROUTE_API_KEY` (**clé dédiée `hermes_watch`**, restreinte à 5 modèles), `TELEGRAM_BOT_TOKEN`
(bot propre `@Omaths2_watch_bot`), `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL`,
`DEEPSEEK_API_KEY`, `OPENROUTER_API_KEY`, `KIMI_API_KEY`, `NVIDIA_API_KEY_GEMMA4`, `WHATSAPP_*`.

> **Pas de `EMAIL_*` ici, volontairement.** Les deux profils partageaient le mot de passe email du
> bureau : deux gateways pollaient la même boîte, et `hermes profile list` avertissait d'un
> « credential partagé ». Le bloc a été retiré le 17/09/2026. Si `watch` doit un jour traiter
> l'email, lui donner une **boîte distincte** (un second mot de passe d'application sur la même
> boîte ne change pas l'identité du canal).

### `profiles\veille\.env` (profil `veille`)

`OMNIROUTE_API_KEY` (**clé dédiée `hermes_veille`**, 7 modèles autorisés), `TELEGRAM_BOT_TOKEN`
(`@Hermesveille1_veille_bot`), `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL`, `SIYUAN_TOKEN`,
`SIYUAN_URL`.

> **Règle d'isolation** : le profil `veille` ne doit **jamais** hériter du `.env` du bureau — pas de
> `hermes profile create veille --clone`, pas de `--clone-channels`. Deux profils sur le même bot
> Telegram se neutralisent (un bot n'appartient qu'à un profil).
>
> **Nouvelles clés par machine** : une réinstallation sur une autre machine exige de **nouvelles**
> clés (bots Telegram, clé OmniRoute, jeton SiYuan). Réutiliser les mêmes clés casse l'isolation des
> profils et fait que deux machines répondent sur un même bot.

### Rotation d'un secret (sans jamais l'afficher)

```powershell
# Telegram : BotFather > /mybots > API Token > Revoke, puis poser la nouvelle valeur dans le .env
$t = (Select-String -Path "$env:LOCALAPPDATA\hermes\profiles\veille\.env" -Pattern '^TELEGRAM_BOT_TOKEN=').Line -replace '^TELEGRAM_BOT_TOKEN=',''
curl.exe -s -o NUL -w "nouveau: %{http_code}\n" "https://api.telegram.org/bot$t/getMe"   # 200 attendu
```

---

## 4. Structure du dépôt

```
%LOCALAPPDATA%\hermes\
├── config.yaml              # config du profil default (modèle, repli, toolsets, plateformes)
├── .env.example             # noms des variables du profil default (aucune valeur)
├── SOUL.md                  # personnalité/consignes du profil default
├── recovery_runbook.md      # procédures de reprise (ESTOP, bots, vérifications)
├── memories\                # MEMORY.md + USER.md (mémoire persistante du profil default)
├── skills\                  # bibliothèque de skills partagée par le profil default (catégories : devops,
│                            #   media, mlops, productivity, research, software-development, wordpress…)
├── profiles\
│   ├── watch\               # config.yaml + .env.example + skills\ (copie complète du profil)
│   └── veille\              # config.yaml + .env.example + skills\ (sous-ensemble veille)
├── scripts\                 # source de vérité des automatisations (voir §5)
├── cron\                    # définitions et historique d'exécution des jobs du profil default
├── gateway-service\         # lanceurs VBS des gateways (démarrage masqué, hors Job Object)
├── omniroute-launch.vbs/.cmd# lancement silencieux d'OmniRoute (garde LISTENING)
└── data\  (NON versionné)   # venvs, modèles, index RAG, xtts, nvidia… trop volumineux / propriétaire
```

Non versionné volontairement : `.env`, `auth.json`, `state.db*`, `sessions/`, `cache/`, `logs/`,
`backups/`, `pastes/`, `mcp-tokens/`, `whatsapp/`, `pairing/`, `runtime/`, `state/`, `gateway/`,
`data/`, `hermes-agent/` (dépôt upstream imbriqué), `*_token.json`, `*secret*.json`, `*.pem`, `*.key`.

---

## 5. Scripts source de vérité

| Script | Rôle | Idempotence |
|---|---|---|
| `scripts\check_gateways.ps1` | healthcheck des 3 gateways : détection ≤5 min, relevage, alerte sur transition, battement horaire | lecture seule + relevage |
| `scripts\verif_24h.ps1` | rapport T+24h contre la baseline T0 (SiYuan, RAG, cron, ticks, gateways, alertes, A2A OFF) | lecture seule (`-NoReport`) |
| `scripts\activer_a2a.ps1` / `desactiver_a2a.ps1` | activation / retour arrière A2A, paramétrés par profil et par port, diff affiché avant écriture | `-SelfTest` (aucune écriture) |
| `scripts\probe_omniroute.py` | sonde les modèles gratuits et maintient le combo `eco` (ajout + élagage après 3 échecs terminaux, plancher 2 cibles) | re-jouable (état persistant) |
| `scripts\creer_tache_gateway.ps1` | (re)crée la tâche planifiée d'un gateway avec répétition courte | `-DryRun` par défaut, `-Apply` |
| `scripts\check_memory.ps1` | contrôle de saturation de la mémoire persistante (lecture seule) | lecture seule |

---

## 6. Documentation complète

- `Desktop\hermes_install\ARCHITECTURE_HERMES.md` — architecture consolidée : les 3 profils, les
  scripts, les tâches planifiées, les points de fuite connus, la dette A2A en 11 points, le mode
  observation 24 h et ses critères de validation.
- `Desktop\hermes_install\A2A_PREPARATION.md` — préparation A2A (activation non faite).
- `Desktop\hermes_install\README.md` — rôle du dépôt de documentation, liste des rapports.
- `Desktop\hermes_install\scripts\restore-from-github.md` et `push-to-github.md` — procédures de
  restauration et de publication.

---

*Dernière mise à jour : 2026-09-17 — dépôt nettoyé de tout secret (audit : 0 occurrence sur les
motifs jeton Telegram, clé Google, `sk-`, `ghp_`, `hf_`, clé privée PEM).*
