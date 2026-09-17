# Restaurer l'installation sur une nouvelle machine

Guide pas-à-pas pour repartir d'un Windows 11 vierge jusqu'à une installation Hermes fonctionnelle
avec les trois profils. Compagnon du script `bootstrap.ps1` : le script fait les étapes mécaniques,
ce document dit **ce qui reste à faire à la main** (et pourquoi le script ne peut pas le faire).

Dépôt unique : `https://github.com/Antoine-Thomas/hermes-home-vision` (~5 Mo, privé).
Ce qu'il contient : le runtime (racine) **et** sa documentation (`docs/`). Ce qu'il ne contient pas :
les secrets, les bases de sessions, `data/` (venvs, modèles, index RAG).

---

## Ordre exact des commandes

```powershell
# 1) Hermes Agent (cree %LOCALAPPDATA%\hermes, son venv, Node, MinGit, ripgrep, ffmpeg)
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
hermes --version                      # attendu : Hermes Agent v0.21.3

# 2) la configuration du depot, par-dessus le runtime (jamais 'git clone' : le dossier n'est pas vide)
cd $env:LOCALAPPDATA\hermes
git init -b main
git remote add origin https://github.com/Antoine-Thomas/hermes-home-vision.git
git fetch --depth 1 origin main
git checkout -f -b main origin/main

# 3) le reste : DryRun d'abord, on lit, puis on applique
.\docs\scripts\bootstrap.ps1 -RepoUrl https://github.com/Antoine-Thomas/hermes-home-vision.git
.\docs\scripts\bootstrap.ps1 -RepoUrl https://github.com/Antoine-Thomas/hermes-home-vision.git -Apply

# 4) les .env (le script a copie les modeles) : remplir les valeurs, voir plus bas
notepad .env
notepad profiles\watch\.env
notepad profiles\veille\.env

# 5) relancer les gateways pour prendre les .env, puis verifier
hermes gateway restart ; hermes -p watch gateway restart ; hermes -p veille gateway restart
hermes profile list ; hermes doctor
```

Le bootstrap est **idempotent** : relançable autant de fois que nécessaire, il ne supprime rien, ne
réécrit jamais un `.env` existant et saute ce qui est déjà en place. Sans `-Apply`, il n'écrit rien
et affiche ce qu'il ferait. Son journal va dans `docs\snapshot\bootstrap_<horodatage>.log`.

---

## Ce que le script fait, ce qu'il ne peut pas faire

| Étape | Qui |
|---|---|
| Installer Hermes (Python, Node, git, outils) | **script** (installeur officiel) |
| Poser la configuration du dépôt (`git init`+`fetch`+`checkout`) | **script** |
| Copier les 3 `.env.example` → `.env` (sans les remplir) | **script** |
| Recréer les tâches planifiées **recreables** (14) | **script** |
| Démarrer les services dans l'ordre et attendre qu'ils écoutent | **script** |
| Vérifier les ports, les profils, `doctor`, `verif_24h` | **script** |
| Créer les bots Telegram | **toi** (§ ci-dessous) |
| Générer la clé OmniRoute (poste + par profil) | **toi** |
| Créer le jeton d'API SiYuan | **toi** |
| Installer SiYuan et recréer les 6 notebooks | **toi** |
| Restaurer `data/` (venvs, modèles, index RAG) | **toi** |
| Recréer les 6 tâches dont le fichier cible est hors dépôt | **toi** (table plus bas) |

---

## 1. Les bots Telegram (un par profil)

Un bot Telegram n'appartient qu'à **un** profil : il en faut **trois**.

1. Dans Telegram, ouvrir **@BotFather** → `/newbot` → nom → identifiant unique terminant par `bot`.
2. Récupérer le jeton (`123456789:AA…`) et le coller dans le `.env` du profil correspondant
   (`TELEGRAM_BOT_TOKEN=`). **Jamais dans le chat**, jamais dans un dépôt.
3. Récupérer son **id numérique** : écrire au bot, puis ouvrir
   `https://api.telegram.org/bot<TON_JETON>/getUpdates` et lire `message.chat.id`.
   Le mettre dans `TELEGRAM_ALLOWED_USERS` **et** `TELEGRAM_HOME_CHANNEL` (c'est la liste blanche —
   sans elle, le bot ne répond à personne).
4. Vérifier : `curl.exe -s -o NUL -w "%{http_code}" "https://api.telegram.org/bot<JETON>/getMe"` → `200`.

## 2. Les clés OmniRoute

Le routeur LLM local lit ses clés dans son propre dashboard (`http://127.0.0.1:20128`), pas dans
Hermes.

1. Démarrer OmniRoute (tâche `OmniRouteServer`, ou `omniroute-launch.vbs`).
2. Dashboard → *API keys* : créer **trois** clés — une pour le poste (`default`), une `hermes_watch`
   (restreinte, quelques modèles), une `hermes_veille` (restreinte, 7 modèles).
   `POST /api/keys` ne renvoie la valeur **qu'une seule fois** : la copier dans le `.env` du profil
   au moment de la création (champ `OMNIROUTE_API_KEY`).
3. Vérifier la portée d'une clé restreinte : `GET /v1/models` avec cette clé ne doit annoncer que
   les modèles autorisés.

## 3. SiYuan et son jeton

1. Installer **SiYuan** (application externe, hors dépôt) et pointer son workspace sur
   `%USERPROFILE%\SiYuan\hermes-projects`.
2. Recréer les 6 notebooks : `journal`, `veille`, `video-ia`, `hermes-projets`, `hermes-skills`,
   `apprentissage-continu`.
3. Récupérer le jeton : *Réglages → À propos → API token*. Il est **unique par workspace** : le
   mettre dans `.env` (profil `default`) **et** dans `profiles\veille\.env` (`SIYUAN_TOKEN`), et
   `SIYUAN_URL=http://127.0.0.1:6806` dans les deux.
4. Vérifier : `curl -s -X POST http://127.0.0.1:6806/api/notebook/lsNotebooks -H "Authorization: Token <JETON>" -H 'Content-Type: application/json' -d '{}'` → `"code":0` et 6 notebooks.

## 4. `data/` — ce qui n'est pas versionné

Le dépôt ne contient **aucun** volumineux. À restaurer ou recréer :

- `data\rag\` : le script d'indexation et le serveur (`serveur_rag.py`, port 8200). L'index se
  reconstruit (`reindex_auto.py`, tâche quotidienne 03h00) — compter plusieurs heures la première fois.
- `data\nvidia\` : `nvidia-nim-proxy.py` + `nvidia-nim-launch.vbs` (proxy NIM, port 20200) et les
  clés `NVIDIA_API_KEY_*`.
- `data\omniroute\` : scripts de maintenance du combo `eco` (`restore_eco_*.py`, `reorder_eco.py`).
- Les venvs vidéo/IA (`data\video_youtube\`), les modèles Ollama, les LoRA : à réinstaller selon
  l'usage, rien de tout cela n'est nécessaire pour faire tourner les trois profils.

> **Le serveur RAG n'a aucun lanceur dans le parc** (ni tâche, ni script) : il doit être démarré
> explicitement (`python data\rag\serveur_rag.py`). Le bootstrap le fait et le signale. Détail :
> `ARCHITECTURE_HERMES.md` §7.9.

## 5. Les 6 tâches planifiées hors dépôt

Le bootstrap recrée les 14 tâches dont la cible est **dans** le dépôt. Les 6 suivantes dépendent de
fichiers absents du dépôt : à recréer une fois ces fichiers restaurés.

| Tâche | Action attendue | Fichier requis |
|---|---|---|
| `Hermes - Reindex RAG` | `python.exe "…\data\rag\reindex_auto.py"` (quotidien 03h00) | `data\rag\reindex_auto.py` |
| `Hermes_NVIDIA_NIM_Proxy` | `wscript.exe "…\data\nvidia\nvidia-nim-launch.vbs"` (logon + PT15M) | `data\nvidia\nvidia-nim-launch.vbs` |
| `SiYuan - noyau second cerveau` | `wscript.exe "…\SiYuan\demarrer_siyuan_silencieux.vbs"` (logon) | application SiYuan |
| `Hermes-PurgeReports` | `powershell -File "C:\ProgramData\Hermes\purge_reports.ps1"` (quotidien 02h00) | `C:\ProgramData\Hermes\purge_reports.ps1` |
| `AudioGuardian-Watchdog` | `wscript.exe "…\data\surveillance\audio_guardian\guardian-watchdog.vbs"` (PT5M) | `data\surveillance\…` |
| `cua-driver-serve` | `powershell -Command "Start-Process …cua-driver.exe serve"` (logon) | logiciel tiers |

Ne **pas** recréer `HermesGateway` (tâche désactivée, vestige d'avant le renommage : elle lançait
`hermes gateway start`, ce qui recrée le piège du Job Object — voir `docs\ARCHITECTURE_HERMES.md`).

---

## 6. Vérifications finales

```powershell
for ($p in 6806, 8200, 9119, 20128, 20200) { "$p -> " + (Test-NetConnection 127.0.0.1 -Port $p -InformationLevel Quiet) }
hermes profile list          # 3 profils, gateways running
hermes doctor                # les 4 avertissements preexistants (npm, cle optionnelle) sont normaux
hermes gateway list          # ✓ par profil
```

Puis la baseline : `docs\snapshot\baseline_T0.json` décrit **la machine d'origine** (notebooks SiYuan,
fragments RAG, identifiants de cron). Sur la nouvelle machine, la régénérer **avant** d'utiliser
`verif_24h.ps1` comme contrôle :

```powershell
python docs\scripts\baseline_t0.py        # ecrit docs\snapshot\baseline_T0.json
powershell -ExecutionPolicy Bypass -File .\scripts\verif_24h.ps1
```

## 7. Règles à ne pas contourner

- **Nouvelles clés par machine** : ne jamais réutiliser les jetons de la machine d'origine. Deux
  machines sur le même bot Telegram se neutralisent, et le profil `veille` ne doit jamais hériter du
  `.env` du bureau (pas de `--clone`, pas de `--clone-channels`).
- **Aucun secret dans le chat, dans un dépôt ou dans une issue** : ce qui est collé est déjà exposé
  (transcript, `state.db`, presse-papiers) — le remède est la rotation, pas la suppression.
- **Le dépôt privé n'est pas un coffre** : il contient l'historique complet. Toute mise en public
  exige un re-scan (`docs\scripts\scan_secrets_history.py --repo .`).
- **L'agent A2A reste désactivé** par défaut (`docs\A2A_PREPARATION.md` décrit l'activation et son
  rollback si le besoin se présente).
