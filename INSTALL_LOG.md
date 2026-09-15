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

## Étape 4 — LTX-2 / ComfyUI : INSTALLÉ, validation en attente d'une pièce

Décision retenue : **LTX-2.3** (et non 2.5) — seule ligne documentée pour le GGUF + ComfyUI, et
seule à tenir dans 30 Go. Dossier : `C:\Users\searc\ComfyUI-LTX`.

Téléchargé et vérifié (27,7 Go au total, sous la limite) :

| Fichier | Taille | Source | Licence |
|---|---|---|---|
| ComfyUI_windows_portable_nvidia.7z (v0.35.0) | 1,91 Go | Comfy-Org/ComfyUI | GPL-3 |
| ltx-2.3-22b-distilled-1.1-Q4_K_S.gguf | 12,96 Go | unsloth/LTX-2.3-GGUF | other (LTX) |
| gemma-3-12b-it-qat-Q4_0.gguf | 8,70 Go | smthem/LTX-2.3-test-gguf | MIT |
| ltx-2.3-22b-distilled_video_vae.safetensors | 1,45 Go | unsloth/LTX-2.3-GGUF | other (LTX) |
| ltx-2.3-22b-distilled_audio_vae.safetensors | 0,36 Go | unsloth/LTX-2.3-GGUF | other (LTX) |
| ltx-2.3-22b-distilled_embeddings_connectors.safetensors | 2,31 Go | unsloth/LTX-2.3-GGUF | **INUTILE (voir blocage)** |

Placement : `models/gguf/` (transformer + encodeur), `models/checkpoints/` (connecteurs),
`models/vae/`. Liens durs pour éviter tout doublon de 13 Go.

Nœuds : `ComfyUI_LTX2_SM` (smthemex) + `ComfyUI-GGUF` (city96). Le serveur démarre et expose
les 9 nœuds LTX2 ; le workflow T2V est accepté par l'API.

Trois correctifs ont été nécessaires (tous documentés et appliqués) :

| Problème | Diagnostic | Correctif |
|---|---|---|
| `No module named 'cv2'` | le python portable n'a pas OpenCV | `pip install opencv-python-headless` (5.0.0.93) |
| `'SiglipVisionModel' object has no attribute 'vision_model'` puis `'Gemma3TextConfig' object has no attribute 'rope_local_base_freq'` | le nœud est écrit pour transformers 4.5x ; la portable embarque 5.15.1 qui a renommé ces champs | `pip install "transformers<5"` -> 4.57.6 (ComfyUI autorise `>=4.50.3`), + un try/except dans `encoder_configurator.py` |
| `diffusers 0.40 requires huggingface-hub>=1.23` (incompatible avec transformers 4.57) | conflit de versions | `pip install diffusers==0.36.0` (les utilitaires GGUF requis sont présents) |

Blocage restant : `NotImplementedError: Cannot copy out of meta tensor; no data!`
Le nœud charge ses connecteurs depuis le fichier « connector » et attend les clés
`...video_embeddings_connector.*` et `...audio_embeddings_connector.*`. Lecture de l'en-tête du
fichier téléchargé chez unsloth : il ne contient que 4 tenseurs
(`text_embedding_projection.{audio,video}_aggregate_embed.{weight,bias}`) — ce n'est pas le bon
fichier. Le bon est `connector-11.safetensors` (6,34 Go, MIT, non protégé, même dépôt que
l'encodeur). Il porterait le total à 31,7 Go, au-dessus des 30 Go autorisés : **décision en
attente**, rien n'a été téléchargé de plus.

## Étape 5 — AirLLM : écarté (décision utilisateur)

## Étape 6 — Optimisation : réglages Local relevés, non modifiés

Chemins réels trouvés : `%APPDATA%\Local\run\<hash>\conf\php\php.ini` et `.../conf/mysql/my.cnf`.

| Réglage | Valeur actuelle | Recommandation |
|---|---|---|
| PHP memory_limit | 256M | 512M (confort WP + WooCommerce) |
| PHP max_execution_time | 1200 | conservé |
| PHP post_max_size / upload_max_filesize | 1000M / 300M | conservés |
| MySQL innodb_buffer_pool_size | 32M | 256M (la machine a 64 Go de RAM) |

Non appliqué volontairement : ces fichiers sont générés par Local et peuvent être réécrits par
l'application, et tout changement exige un redémarrage des sites. À faire depuis l'interface
Local (ou avec accord explicite), pas en douce.

## Étape 7 — Non-régression (après toutes les installations)

| Contrôle | Résultat |
|---|---|
| `hermes --version` | 0.21.2 (2026.9.11) — inchangé |
| `C:\wp-cli\wp.bat --version` | WP-CLI 2.12.0 |
| torch du venv Hermes | 2.4.1+cu118, CUDA True |
| 7 venvs IA (LatentSync, LivePortrait, SadTalker, Wav2Lip, MuseTalk, EchoMimicV2, XTTS) | tous importent torch et voient CUDA |
| 5 sites Local | oldstyle, reold, searching-murphy, sm, the-one |
| Certificats SSL locaux | 7 fichiers, valides jusqu'en 2036 |

Les installations de l'étape 4 sont confinées au python portable de ComfyUI : aucun venv
existant, aucun paquet de Hermes n'a été touché.


## Étape 5 — AirLLM : NON FAIT

Non installé, décision en attente. Rappel technique : AirLLM streame les couches
depuis le disque ; sur un i7-8700 et un NVMe de bureau, la latence attendue est de
l'ordre de 0,1 à 1 token/s pour un modèle 70B+, sans bénéfice face à OmniRoute
(local, gratuit) ni aux modèles Ollama déjà présents.

## Étape 8 — Documentation et commit

- `INSTALL_LOG.md` (ce journal) : commandes exactes, erreurs, correctifs.
- `CHEATSHEET.md` : commandes des trois branches vidéo + WP-CLI + Hermes + LTX-2.
- `RAPPORT_INSTALLATION.md` : état initial, actions, versions, blocages, recommandations.
- `snapshot/versions.txt` et `snapshot/config.yaml.redacted` (valeurs sensibles masquées).
- Snapshot commité dans le dépôt git local (`C:\Users\searc\Desktop\hermes_install`)
  après chaque étape validée.
