# Rapport d'installation et d'optimisation — 15/09/2026

Machine : Windows 11 Pro build 26200 · Intel i7-8700 (6 cœurs / 12 threads) · 63,9 Go RAM ·
RTX 3070 Ti 8 Go (driver 616.56) · NVMe système 1,86 To (1 094 Go libres) ·
D: HDD 7,4 To (2 317 Go libres), F: SSD 894 Go (150 libres), H: SSD 224 Go (180 libres), I: HDD 932 Go (161 libres)

## 1. État initial réel (et écarts avec le plan fourni)

| Point du plan | Réalité mesurée | Conséquence |
|---|---|---|
| Local « à mettre à jour vers 10.1.2 » | Local **10.1.2.0** déjà installé (FileVersion 10.1.2.20260824.1) | Aucune mise à jour, donc aucune sauvegarde préalable obligatoire |
| Hermes « à installer via le script curl » | Hermes **v0.21.2** (2026.9.11) déjà installé, méthode git | Rien à installer |
| `~/.hermes/.env`, `~/.hermes/skills` | Chemin réel : **`%LOCALAPPDATA%\hermes`** (soit `C:\Users\searc\AppData\Local\hermes`) | Les chemins du plan ne s'appliquent pas |
| « port 8642 pour Hermes » | 8642 **libre** ; 20128 = OmniRoute (proxy LLM local) | Pas de conflit à éviter |
| « python 3.11 requis » | 3.11.16 présent (venv Hermes) + 3.10 + 3.14.7 | OK |
| « WP-CLI à installer » | **WP-CLI 2.12.0** présent (`C:\wp-cli`, lancé par le PHP de Local) | Rien à installer ; défaut mineur : `wp` nu tombe sur un fichier vide dans System32 |
| LTX-2 / ComfyUI / AirLLM / vLLM | **aucun des quatre** | À installer (décision en attente) |

## 2. Actions réalisées

1. **Audit complet** (voir INSTALL_LOG.md, étape 0) : système, GPU, disques, versions, ports,
   services Local, sites, venvs IA, dépôt des skills.
2. **Installation des 5 skills WordPress** dans `%LOCALAPPDATA%\hermes\skills\wordpress\` :
   `local-flywheel-setup`, `wordpress-site-management`, `wp-cli-automation`,
   `wordpress-backup-restore`, `wordpress-deployment`. Frontmatter vérifié, skills
   découverts par Hermes.
3. **Snapshot de configuration versionné** dans `C:\Users\searc\Desktop\hermes_install` :
   `snapshot/versions.txt`, `snapshot/config.yaml.redacted` (2 valeurs sensibles masquées —
   aucune clé n'est copiée en clair dans le dépôt), dépôt git local initialisé.
4. **Documentation** : `INSTALL_LOG.md`, `CHEATSHEET.md`, ce rapport.
5. **Non-régression** vérifiée après chaque action (Hermes, Git, Docker, torch/CUDA, WP-CLI).

Aucune modification système, aucun pilote, aucune suppression de fichier, aucune
réinstallation : conformément aux contraintes, tout ce qui est irréversible ou lourd est
laissé à ta décision.

## 3. Problèmes rencontrés et solutions

| Problème | Diagnostic | Solution |
|---|---|---|
| `wp` ne répond rien | `command -v wp` renvoie `C:\Windows\System32\wp`, un fichier de **0 octet** créé le 15/07 | Utiliser `C:\wp-cli\wp.bat` (il appelle le PHP de Local) ; la suppression du fichier vide attend ton accord |
| `php` absent du PATH | Local embarque son PHP mais ne l'expose pas | Utiliser `...\lightning-services\php-8.2.29+0\bin\win64\php.exe`, ou ajouter ce dossier au PATH (à ta main) |
| Plan qui suppose `~/.hermes` | Hermes sur Windows utilise `%LOCALAPPDATA%` | Chemins corrigés dans ce rapport et dans le cheatsheet |
| Outils IA absents | Aucun module `comfyui`, `ltx`, `airllm`, `vllm` ; aucun dossier | Installation à décider (section 5) |

## 4. Versions finales

| Outil | Version |
|---|---|
| Windows | 11 Professionnel, build 26200 |
| Local (ex-by Flywheel) | **10.1.2.0** (20260824.1) — inchangée, déjà à jour |
| Services Local | PHP 8.2.29 · MySQL 8.4.0 · MariaDB 10.11.18 · nginx 1.26.1 · Mailpit 1.24.1 |
| Hermes Agent | 0.21.2 (2026.9.11) |
| WP-CLI | 2.12.0 |
| Python | 3.11.16 (venv Hermes) · 3.10 · 3.14.7 |
| Git / Node / npm / pnpm / gh / Docker / ffmpeg | 2.55.0 · 24.15.0 · 12.0.2 · 11.24.0 · 2.100.0 · 29.7.2 · 8.1 |
| CUDA / driver | toolkits 13.2-13.3-13.4 (nvcc 13.4) · driver 616.56 |
| torch (venv Hermes) | 2.4.1+cu118, CUDA opérationnel |
| Ollama | installé, 74 Go de modèles, serveur arrêté |

Sites Local : oldstyle, reold, searching-murphy, sm, the-one (certificats SSL locaux présents).

## 5. Endpoints configurés

| Service | Endpoint | État |
|---|---|---|
| OmniRoute (LLM par défaut de Hermes) | http://127.0.0.1:20128/v1 | déclaré, port en écoute |
| Ollama (provider déclaré) | http://127.0.0.1:11434/v1 | déclaré, serveur arrêté |
| Repli Hermes | deepseek / deepseek-flash | configuré |
| AirLLM (8000) | — | non installé, port libre |
| LTX-2 / ComfyUI | — | non installé |

## 6. Skills installés et état

- Nouveaux (catégorie `wordpress`, importés du dépôt `hermes-wordpress-skills`) :
  `local-flywheel-setup`, `wordpress-site-management`, `wp-cli-automation`,
  `wordpress-backup-restore`, `wordpress-deployment` — **actifs**.
- Déjà présents et utiles à ce chantier : `wordpress-local-flywheel-publishing`,
  `wordpress-suite`, `hermes-agent`, `talking-head-video-8gb` (v1.8),
  `omniroute-suite`, `hermes-operations`, `windows-ops`, `windows-performance-tuning`.

## 7. Recommandations d'optimisation continue

1. **PHP dans le PATH** (ou `wp` en alias vers `C:\wp-cli\wp.bat`) : rend WP-CLI utilisable
   partout, y compris par les skills qui lancent `wp`.
2. **Nettoyer le `wp` vide de System32** (fichier de 0 octet, effet de bord d'une ancienne
   installation) — après ton accord.
3. **Toolsets Hermes** : seuls `hermes-cli` et `web` sont déclarés. À élargir si tu veux que
   les sessions non interactives (cron) aient plus d'outils, mais à faire en connaissance de
   cause : chaque toolset ajouté alourdit le prompt.
4. **Ollama** : arrêté. Le lancer seulement si tu veux un modèle local de secours ; sinon il
   consomme de la VRAM pour rien.
5. **Vidéo IA locale** : la machine est déjà équipée (LatentSync, LivePortrait, SadTalker,
   Wav2Lip, MuseTalk, EchoMimicV2, XTTS). Avant d'ajouter LTX-2 22B, rappel de la contrainte
   réelle : 8 Go de VRAM et un CPU 6 cœurs de 2017. La variante GGUF Q4/Q5 est la seule
   tenable ; attends-toi à des minutes par seconde de vidéo, pas à du temps réel.
6. **AirLLM** : à éviter sur cette machine (streaming disque, 0,1-1 token/s sur ce CPU) sauf
   curiosité technique ; les modèles utiles passent déjà par OmniRoute et Ollama.
7. **Disque** : télécharger les poids sur C: (NVMe, 1 094 Go libres), pas sur les SSD
   externes F: (150 Go) ou H: (180 Go).
8. **Sauvegarde des sites Local** : pas nécessaire aujourd'hui (aucune mise à jour), mais à
   faire avant la prochaine mise à jour majeure — le skill `wordpress-backup-restore` le fait
   en une commande.

## 8. Décisions en attente

1. LTX-2 : ComfyUI + GGUF Q4/Q5 (~25-35 Go) / poids complets (~66 GiB) / ComfyUI seul / rien.
2. AirLLM : installer / tester un 7B seulement / ne pas installer.
3. Suppression du fichier vide `C:\Windows\System32\wp` : autorisée ou non.

## 9. Vérification des liens et des chiffres du plan LTX-2 (faite le 15/09)

Les 11 liens du plan répondent tous en HTTP 200 (docs Hermes, dépôt Hermes, skills WordPress,
localwp.com et /releases, WP-CLI, AirLLM, Lightricks/LTX-2, ComfyUI_LTX2_SM, comfyui-mcp,
HuggingFace Lightricks/LTX-2.5). Le projet LTX-2 existe donc bien, et son dépôt de code ne
pèse que 1,6 Mo (les poids sont sur Hugging Face).

En revanche les volumes annoncés dans le plan sont faux, vérifiés via l'API Hugging Face :

| Source | Contenu | Volume réel |
|---|---|---|
| `Lightricks/LTX-2.5` (officiel) | 17 fichiers, transformer 22B bf16 42 Go, text encoder Gemma4-12B 26 Go, int8 21,5 + 15,4 Go, VAE 1,5 Go | **200,9 Go**, et dépôt **gated** (acceptation de licence + jeton) |
| `Abiray/LTX-2.5-Distilled-GGUF` (communautaire) | transformer seul en GGUF | Q3_K_S 12,7 · Q4_K_S 15,3 · Q5_K_M 18,1 · Q8_0 23,6 Go |
| `QuantStack/LTX-2.3-GGUF` | transformer seul, 27 variantes | Q3_K_S 14,0 · Q4_K_S 16,7 Go |

Un jeton Hugging Face existe déjà sur la machine (`~/.cache/huggingface/token`), mais l'accès
au dépôt officiel reste soumis à l'acceptation de la licence sur le site.

Conclusion pratique : la variante « GGUF quantifié » est la bonne, mais le total réel pour
la faire tourner est d'environ **25 à 30 Go** (transformer Q4/Q5 + text encoder GGUF + VAE),
pas 66 GiB ni 200 Go. Le README officiel recommande `--quantization fp8-cast --offload cpu`
en cas de VRAM limitée — ce qui décrit exactement cette machine (8 Go, Ampere sans FP8
natif), donc ça tournera, lentement.

