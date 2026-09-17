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

## Étape 4 bis — Connecteur téléchargé (autorisé le 15/09)

Commandes :
```
curl -L -C - --retry 5 -sS \
  -o "C:/Users/searc/ComfyUI-LTX/ComfyUI_windows_portable/ComfyUI/models/checkpoints/connector-11.safetensors" \
  "https://huggingface.co/smthem/LTX-2.3-test-gguf/resolve/main/connector-11.safetensors?download=true"
# suppression du fichier inutile de 2,31 Go (les deux liens durs)
```
- 6,34 Go, 6 344 498 464 octets exactement, licence MIT, non protégé.
- En-tête lu avant usage : 262 tenseurs = 129 `video_embeddings_connector.*`
  + 129 `audio_embeddings_connector.*` + les 4 `text_embedding_projection.*_aggregate_embed.*`.
  Le fichier de 2,31 Go supprimé était donc bien redondant.
- Total installé : 34,0 Go (plafond autorisé 31,7 Go, dépassement validé).

Effet : l'encodeur de texte passe (nœuds 1, 2, 3, 6 OK). L'échec se déplace au nœud 7
(`LTX2_SM_KSampler`) : `Cannot copy out of meta tensor; no data!`.

Diagnostic mené, sans rien télécharger de plus :
- instrumentation du nœud : le module vide est `patchify_proj`, `weight(4096, 128)` + `bias(4096,)` ;
- lecture du GGUF : 4444 tenseurs, `patchify_proj`, `adaln_single`, `proj_out` présents ;
- lecture du state_dict par le lecteur du nœud : 4444 clés, dont `patchify_proj.weight` ;
- complément des paramètres vides depuis le state_dict en mémoire : 0 rempli, donc au moment du
  chargement plus rien n'est vide — le module vide apparaît après, sur l'objet que reçoit
  `BlockGPUManager`.
Ce n'est donc pas une pièce manquante mais un chemin de chargement du nœud.

Tentatives de correction restées dans le code (utiles même si non concluantes) :
`LTX2/ltx_core/model/transformer/model.py` (diagnostic des modules vides, injection depuis le
connecteur) et `single_gpu_model_builder.py` (complément par nom depuis le state_dict du GGUF).

Non-régression revérifiée après ces manipulations : inchangée (voir tableau de l'étape 7).

## Étape 4 ter — Résolution : la chaîne LTX-2.3 génère (15/09/2026)

Cause racine, trouvée par la mesure et non par hypothèse : `load_sd` remettait un dictionnaire
**vide (0 clé sur 4444)** parce que les opérations de renommage du noeud ne s'appliquent pas au
GGUF d'unsloth, dont les noms bruts correspondent pourtant exactement à ceux du modèle. Résultat :
4186 paramètres sur 4186 restaient sur le disque virtuel, et torch levait
`Cannot copy out of meta tensor` au moment de l'échantillonnage.

Trois mesures ont mené au diagnostic :
```
grep -a "Uninitialized parameters" comfyui.log   # le constructeur nomme lui-meme les modules vides
# instrumentation : nombre de cles du dictionnaire vs nombre de parametres du modele
[correctif] cles modele=4186 cles dictionnaire=0 intersection=0      <- avant
[correctif] GGUF relu SANS operations de renommage : 4444 cles       <- correctif
[correctif] cles modele=4186 cles dictionnaire=4444 intersection=4186
[DIAG setup] parametres=4186 | sur disque virtuel=0                  <- apres
```

Correctif appliqué (`ComfyUI_LTX2_SM/LTX2/ltx_core/loader/single_gpu_model_builder.py`, `load_sd`,
branche `use_gguf`) : quand `load_gguf_checkpoint(..., sd_ops=...)` renvoie un dictionnaire vide,
relire le fichier avec `sd_ops=None`. Instrumentation conservée dans `setup_for_inference` et
`_initialize_submodule` (comptage des paramètres fantômes, garant de la non-régression).

Résultat mesuré (640x384, 25 images, 24 i/s, 8 étapes, mode distilled, offload=True) :
```
execution_success | fichier output/video/ltx_test_00001_.mp4 (89 Ko, H.264 + audio AAC)
a froid : 132,79 s  -> 5,31 s/image, 16,60 s/etape  (inclut le chargement des 13 Go)
a chaud : 205,11 s  -> 8,20 s/image, 25,64 s/etape  (modele deja en memoire, nouveau prompt)
contenu verifie : ecart-type spatial 54,7 puis 75,3 ; mouvement entre images present ;
                   l'image extraite correspond au prompt (plage au lever du soleil).
```
Le second fichier (`ltx_test_00002_.mp4`, 151 Ko) provient d'un prompt different (renard dans la
neige) : la génération fonctionne, elle n'est pas figée sur un seul résultat.

Aucun téléchargement de 18 Go n'a été nécessaire : les 34,0 Go installés suffisent.

## Étape 10 — SiYuan 3.8.2 (second cerveau) — 15/09/2026

```
winget install --id=B3log.SiYuan --exact --version 3.8.2 --accept-package-agreements --accept-source-agreements
mkdir -p "C:\Users\searc\.config\siyuan"   # sinon l'app plante (voir piege 1)
winget install --id=jqlang.jq --exact      # requis par le skill
hermes skills install official/productivity/siyuan --yes
"<...>\SiYuan-Kernel.exe" serve --workspace="C:\Users\searc\SiYuan\hermes-projects" --port=6806
```

Piège 1 — fenêtre blanche au premier lancement : l'application Electron écrit son journal dans
`%USERPROFILE%\.config\siyuan\`, dossier qui n'existe pas sur une installation neuve, et meurt en
`ENOENT` sans démarrer son noyau. Correctif : créer le dossier. Le noyau (`SiYuan-Kernel serve`)
est le chemin fiable et sert aussi l'interface web.

Piège 2 — deux secrets, pas un : `accessAuthCode` protège l'interface, `api.token` authentifie les
API. Le plan indiquait de récupérer « Settings > About > API Token » : c'est bien `api.token` qu'il
faut mettre dans `SIYUAN_TOKEN`, pas l'accessAuthCode. Test à l'appui, l'un pour l'autre donne
`Auth failed [header: Authorization]`.

Piège 3 — `jq` absent : le skill en dépend pour toutes ses commandes ; sans lui, aucune sortie
n'est exploitable.

Résultats : noyau 3.8.2 en écoute sur 127.0.0.1:6806, `lsNotebooks` → `code 0`, SQL → `n=0`,
interface web protégée (401 sans code), mauvais jeton refusé. Redémarrage sans secret en ligne de
commande validé (conf.json relu). Script de démarrage : `C:\Users\searc\SiYuan\demarrer_siyuan.cmd`.
Non-régression revérifiée après coup : inchangée.

## Étape 10 bis — Premiers contenus du second cerveau (15/09/2026)

Import de deux notes depuis `C:\Users\searc\Desktop\skills siYUAN\` :
```
notebook hermes-skills (id 20260915170151-gtqknum)
  Automatisation des réseaux sociaux   id 20260915170217-7rwoqt1  (2814 car., 5 liens, 6 blocs de code)
  Veille technologique et mise à jour  id 20260915170217-69gqhnp  (2955 car., 3 blocs de code)
```
Méthode : script `C:\Users\searc\SiYuan\import_notes.py` (POST JSON, jeton lu dans le `.env`),
`--remplacer` pour supprimer puis recréer les documents existants du notebook.

Deux pièges rencontrés ici :
- premier import sans accents (précaution inutile) : SiYuan gère l'UTF-8 nativement, y compris les
  emojis ; les textes ont été réimportés à l'identique des originaux ;
- deux documents créés dans la même seconde portent le même horodatage : `ORDER BY created` ne les
  départage pas. Toujours vérifier par identifiant explicite, pas par tri de date.

Vérifications faites en relisant depuis SiYuan (et non sur la seule réponse de l'API) : titres et
chemins accentués corrects, corps des deux documents présents et distincts, recherche plein texte
opérationnelle (`twitter-cli` retrouvé), blocs de code préservés.

Note : ces fichiers sont des NOTES (pas des skills Hermes : aucun frontmatter, contenu rédigé).
Elles ont donc été déposées dans la base de connaissances, pas dans le dossier des skills.

## Étape 10 ter — Structure complète + finitions (15/09/2026)

Décisions actées et exécutées :

1. Code d'accès de l'interface remplacé par le choix de l'utilisateur. Ordre impératif : arrêter le
   noyau D'ABORD (il réécrit `conf.json` en s'arrêtant), sauvegarder le fichier, éditer, redémarrer.
   Le `api.token` n'a pas été touché.
2. Tâche planifiée utilisateur (`Register-ScheduledTask`, déclencheur `AtLogon`, `MultipleInstances
   IgnoreNew`, sans limite de durée) qui lance `demarrer_siyuan.cmd`. Testée en la déclenchant.
3. Structure : 6 notebooks, 21 documents créés (5 sites, 10 skills, 3 branches vidéo, 1 journal,
   2 veille), `apprentissage-continu` laissé vide comme demandé.

Données des documents « projets » : toutes lues sur disque (`sites.json`, fichiers d'extension,
dump SQL de sauvegarde) — aucune valeur inventée ; l'état actif des extensions est signalé comme
déduit du dump et non d'une instance en cours. Documents « skills » : extraits verbatim des
`SKILL.md`.

Curation demandée ensuite : le document « Sources suivies » a été réduit à ce que la note
« Veille technologique » ne contient pas (dépôts suivis, versions à surveiller) et renvoie à elle
pour la liste des sources, au lieu de la recopier.

Non-régression revérifiée après coup : Hermes 0.21.2, WP-CLI 2.12.0, torch CUDA, les 7 venvs IA,
les 5 sites Local, 7 certificats SSL — inchangé.
