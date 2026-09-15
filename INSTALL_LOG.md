# Journal d'installation — 15/09/2026

Machine : Windows 11 Pro build 26200, i7-8700 (6c/12t), 63,9 Go RAM, RTX 3070 Ti 8 Go (driver 616.56)
Dossier de travail : C:\Users\searc\Desktop\hermes_install

Chaque commande ci-dessous a été exécutée réellement ; les résultats sont ceux renvoyés par la machine.

## Étape 0 — Audit

| Commande | Résultat |
|---|---|
| `powershell Get-CimInstance Win32_OperatingSystem` | Windows 11 Professionnel build 26200 |
| `nvidia-smi --query-gpu=name,memory.total,driver_version` | RTX 3070 Ti, 8192 MiB, 616.56 |
| `powershell Get-CimInstance Win32_LogicalDisk` | C: 1 094 Go libres / 1 862 (NVMe KINGSTON SNV3S2000G) ; D: 2 317 / 7 452 (HDD) ; F: 150 / 894 (SSD) ; H: 180 / 222 (SSD) ; I: 161 / 932 (HDD) |
| `hermes --version` | Hermes Agent v0.21.2 (2026.9.11) · upstream 6bc0e9e6, installation git |
| `powershell (Get-Item ...\Local\Local.exe).VersionInfo` | Local 10.1.2.0 — FileVersion 10.1.2.20260824.1 |
| `ls lightning-services` | php-8.2.29, mysql-8.4.0, mariadb-10.11.18, nginx-1.26.1, mailpit-1.24.1 |
| `ls "%USERPROFILE%\Local Sites"` | oldstyle, reold, searching-murphy, sm, the-one |
| `php -v` (PHP de Local) | PHP 8.2.29 (NTS VC++ 2019 x64) — `php` n'est PAS dans le PATH |
| `php C:/wp-cli/wp-cli.phar --version` | WP-CLI 2.12.0 (fonctionne via le PHP de Local) |
| `command -v wp` | /c/WINDOWS/system32/wp — fichier de 0 octet, crée le 15/07 : la commande nue `wp` ne fait rien |
| `python --version`, `py --version` | 3.11.16 (venv Hermes, dans le PATH) ; 3.14.7 (lanceur py) ; 3.10 aussi présent |
| `git`, `node`, `npm`, `pnpm`, `gh`, `docker`, `ffmpeg`, `wsl` | 2.55.0 / v24.15.0 / 12.0.2 / 11.24.0 / 2.100.0 / 29.7.2 / 8.1 / WSL 2.7.13 |
| `nvcc --version` | CUDA 13.4 (toolkits 13.2, 13.3, 13.4 installés) |
| `torch` dans le venv Hermes | 2.4.1+cu118, CUDA disponible |
| `ls ~/.ollama/models/manifests/.../library` | glm-4.7-flash, hermes3:8b, llama3.2:3b, qwen2.5 — 74 Go ; serveur Ollama arrêté |
| `netstat -ano | LISTENING` | 135, 139, 445, 2179, 3000, 3111, 5040, 7680, 10086, 20128 (OmniRoute), 20131, 20132 |
| recherche ComfyUI / LTX / airllm / vllm | aucun trouvé (ni module Python, ni dossier) |
| `ls %LOCALAPPDATA%\hermes\data\video_youtube` | venvs : LatentSync, LivePortrait, SadTalker, Wav2Lip, MuseTalk, EchoMimicV2 |
| `git -C Code/hermes-wordpress-skills log --oneline -1` | 073a3d3 (dépôt propre) |

## Étape 1 — Local by Flywheel

Aucune action : la version installée (10.1.2.0) est exactement la version cible du plan.
Aucune mise à jour disponible, donc aucune sauvegarde préalable obligatoire.
Contrôles faits sans modification : services (PHP 8.2.29, MySQL 8.4.0, MariaDB 10.11.18,
nginx 1.26.1), 5 sites présents, certificats SSL locaux en place
(`.../Local/run/router/nginx/certs` : oldstyle.local, reold.local, oldsm.local).

## Étape 2 — Hermes Agent

Aucune installation : Hermes est déjà installé (v0.21.2, méthode git).
Chemin réel sur cette machine : `C:\Users\searc\AppData\Local\hermes` (et non `~/.hermes`
comme dans le plan). Relevé dans config.yaml, sans le modifier :
- modèle par défaut : provider `omniroute`, modèle `eco`, base_url `http://127.0.0.1:20128/v1`
- repli : `deepseek` / `deepseek-flash`
- provider Ollama déclaré : `http://127.0.0.1:11434/v1`
- toolsets déclarés : `hermes-cli`, `web`
- gateway : pas de port personnalisé (le 8642 du plan n'est pas occupé sur cette machine)

## Étape 3 — Skills WordPress (fait)

```
SK="$LOCALAPPDATA/hermes/skills/wordpress"
mkdir -p "$SK"
for s in local-flywheel-setup wordpress-site-management wp-cli-automation \
         wordpress-backup-restore wordpress-deployment; do
  cp -r "/c/Users/searc/Code/hermes-wordpress-skills/skills/$s" "$SK/$s"
done
```
Résultat : 5 skills copiés dans `%LOCALAPPDATA%\hermes\skills\wordpress\`, frontmatter
`name:` vérifié pour chacun, et découverts par Hermes (catégorie `wordpress`).
Le dépôt d'origine est intact (aucune modification, HEAD 073a3d3).
Non fait volontairement : suppression du fichier vide `C:\Windows\System32\wp`
(fichier système, confirmation explicite requise).

## Étape 4 — LTX-2 / ComfyUI : NON FAIT

Aucun des deux n'est installé, et rien n'a été téléchargé. Décision en attente
(voir RAPPORT_INSTALLATION.md) : ComfyUI + LTX-2 GGUF (~25-35 Go), LTX-2 complet
(~66 GiB), ou pas d'installation. Le disque C: a la place (1 094 Go libres).

## Étape 5 — AirLLM : NON FAIT

Non installé, décision en attente. Rappel technique : AirLLM streame les couches
depuis le disque ; sur un i7-8700 et un NVMe de bureau, la latence attendue est de
l'ordre de 0,1 à 1 token/s pour un modèle 70B+, sans bénéfice face à OmniRoute
(local, gratuit) ni aux modèles Ollama déjà présents.

## Étape 6 — Optimisation : partiel

Aucune modification de configuration système n'a été faite. Points relevés, à
arbitrer : toolsets Hermes limités à `hermes-cli` et `web` ; serveur Ollama arrêté ;
`php` absent du PATH (WP-CLI ne marche que via le .bat).

## Étape 7 — Snapshot et non-régression (fait)

```
mkdir -p ~/Desktop/hermes_install/snapshot
# versions.txt : systeme, outils, services Local, sites, WP-CLI, skills, ports
# config.yaml.redacted : copie de %LOCALAPPDATA%\hermes\config.yaml avec les valeurs
#   de api_key / token / secret / password remplacees par "***REDACTE***" (2 masquees)
cd ~/Desktop/hermes_install && git init && git add . && git commit
```
Vérifications de non-régression exécutées (aucun changement apporté) :
`hermes --version`, `git --version`, `docker --version`,
`php C:/wp-cli/wp-cli.phar --version` -> WP-CLI 2.12.0,
`python -c "import torch; print(torch.cuda.is_available())"` -> True.

## Étape 8 — Documentation (fait)

`CHEATSHEET.md`, `RAPPORT_INSTALLATION.md` et ce journal sont dans
`C:\Users\searc\Desktop\hermes_install`, versionnés dans le dépôt git local.
