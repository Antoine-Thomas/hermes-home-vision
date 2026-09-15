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
| ComfyUI (portable, dossier `C:\Users\searc\ComfyUI-LTX`) | **v0.35.0** — python 3.13.14, torch 2.13.0+cu130, transformers 4.57.6, diffusers 0.36.0, opencv-python-headless 5.0.0.93 |
| LTX-2.3 (GGUF) | **poids installés (27,7 Go)**, validation en attente (voir section 10) |

Sites Local : oldstyle, reold, searching-murphy, sm, the-one (certificats SSL locaux présents).

## 5. Endpoints configurés

| Service | Endpoint | État |
|---|---|---|
| OmniRoute (LLM par défaut de Hermes) | http://127.0.0.1:20128/v1 | déclaré, port en écoute |
| Ollama (provider déclaré) | http://127.0.0.1:11434/v1 | déclaré, serveur arrêté |
| Repli Hermes | deepseek / deepseek-flash | configuré |
| AirLLM (8000) | — | écarté sur décision (port libre) |
| LTX-2.3 / ComfyUI | http://127.0.0.1:8188 | installé, serveur testé plusieurs fois |

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

## 8. Décisions prises par l'utilisateur

1. LTX-2 : **ComfyUI portable + GGUF Q4_K_S**, chemin `C:\Users\searc\ComfyUI-LTX`, ≤30 Go.
2. AirLLM : **ne pas installer**.
3. `C:\Windows\System32\wp` : **l'utilisateur s'en occupe**, je n'y touche pas.

## 9. LTX-2.3 — installation détaillée

Choix : **LTX-2.3** et non LTX-2.5. Motifs mesurés, pas supposés :
- LTX-2.5 n'existe pas en GGUF chez un éditeur non protégé pour la partie encodeur
  (`elix3r/gemma4-12b-with-proj-ltx-2.5-GGUF` est **gated**), et son transformer seul fait
  15,33 Go : avec un encodeur de 8,4 Go et les VAE, l'ensemble sort du plafond de 30 Go.
- LTX-2.3 est la ligne que ComfyUI v0.35 prend en charge nativement et pour laquelle le nœud
  `ComfyUI_LTX2_SM` documente exactement la disposition des fichiers GGUF.
- Le transformer retenu (unsloth, 12,96 Go) est la **même famille de licence** (« other » = LTX)
  que les fichiers Abiray ou QuantStack proposés dans le plan, en 4 Go plus léger, et il vient
  du même dépôt que les VAE, ce qui garantit la cohérence des versions.

Contenu installé : voir `INSTALL_LOG.md`, étape 4 (tableau des 6 fichiers + les 3 correctifs
d'environnement).

**RÉSOLU le 15/09/2026 — la chaîne complète fonctionne.** Deux vidéos générées de bout en bout
depuis un prompt texte, avec piste audio (le modèle LTX-2.3 est audio-vidéo) :

| Mesure | À froid (1er passage) | À chaud (modèle en mémoire) |
|---|---|---|
| Durée totale | 132,79 s | 205,11 s |
| Secondes par image | 5,31 s | 8,20 s |
| Secondes par étape (8 étapes) | 16,60 s | 25,64 s |
| Rapport au temps réel (vidéo de 1,04 s) | ×127 | ×197 |

Réglages du test : 640×384, 25 images, 24 i/s, 8 étapes, mode `distilled`, `offload=True`,
transformer Q4_K_S sur NVMe. Sorties : `output/video/ltx_test_00001_.mp4` (89 Ko) et
`_00002_.mp4` (151 Ko), H.264 + AAC. Contenu vérifié, pas seulement l'absence d'erreur : écart-type
spatial de 54,7 puis 75,3 (une image unie donnerait ~0), mouvement entre images présent, et
l'image extraite du premier test correspond bien au prompt demandé (plage au lever du soleil,
océan, vagues, sable, nuages dorés).

**La cause racine était un dictionnaire vide, pas un fichier manquant.** Diagnostic en trois
mesures : le constructeur du nœud avertissait lui-même
`Uninitialized parameters or buffers: ['scale_shift_table', 'patchify_proj.weight', ...]` ; le
modèle comptait 4186 paramètres fantômes sur 4186 ; et l'instrumentation a montré que
`load_sd` remettait **0 clé sur 4444** parce que les opérations de renommage du nœud vident le
dictionnaire avec ce GGUF — alors que les noms bruts du fichier correspondent exactement à ceux du
modèle. Correctif : relire le GGUF sans ces opérations quand le résultat est vide
(`LTX2/ltx_core/loader/single_gpu_model_builder.py`, fonction `load_sd`). Après correctif :
4444 clés, intersection de 4186 avec le modèle, **0 paramètre fantôme**.

Autres correctifs de la chaîne (déjà en place) : `transformers<5` (4.57.6), `diffusers==0.36.0`,
`opencv-python-headless`, et un try/except sur `vision_tower` dans `encoder_configurator.py`.

Méthode de diagnostic à retenir : chercher d'abord `Uninitialized parameters` dans le journal du
nœud — il nomme lui-même les modules vides — et comparer le nombre de clés du dictionnaire chargé
au nombre de paramètres du modèle. C'est ce couple de chiffres qui a évité un téléchargement de
18 Go inutile.

Détail du parcours, conservé parce qu'il documente le piège : le fichier `connector-11.safetensors`
(6,34 Go, MIT) a été téléchargé et vérifié — total installé **34,0 Go**, 262 tenseurs dont les 129
clés `video_embeddings_connector.*`, 129 `audio_embeddings_connector.*` et les 4
`text_embedding_projection.*_aggregate_embed.*` (le fichier de 2,31 Go supprimé était donc bien
redondant). Son effet a été réel : l'encodeur de texte est passé. L'erreur s'était alors déplacée à
l'échantillonneur, sous la forme `NotImplementedError: Cannot copy out of meta tensor; no data!`
dans `model.py`, sur un `Linear` `weight(4096, 128)` : `patchify_proj`. Trois hypothèses avaient
été écartées par la mesure — fichier incomplet (les tenseurs sont dans le GGUF), complément par nom
depuis le dictionnaire (0 rempli), téléchargement du transformer appairé de 18,14 Go — avant que
le comptage des clés ne désigne le vrai coupable : **le dictionnaire était vide**.

État vérifié du reste de la chaîne : serveur ComfyUI opérationnel, 9 nœuds LTX2 exposés, poids
présents et lisibles. Consommation mesurée pendant une génération : la VRAM reste basse (le
transformer est diffusé par blocs depuis le NVMe), la RAM libre est descendue à 30,8 Go après deux
générations, contre 42 Go au repos.

## 10. Optimisation Local — relevé, non appliqué

Chemins réels : `%APPDATA%\Local\run\<hash>\conf\php\php.ini` et `...\conf\mysql\my.cnf`.

| Réglage | Actuel | Cible proposée | Motif |
|---|---|---|---|
| `memory_limit` | 256M | 512M | WooCommerce et les migrations réclament plus que 256M |
| `max_execution_time` | 1200 | inchangé | déjà large |
| `post_max_size` / `upload_max_filesize` | 1000M / 300M | inchangé | suffisant |
| `innodb_buffer_pool_size` | 32M | 256M | 64 Go de RAM disponibles, 32M étrangle les requêtes |

Non appliqué : ces fichiers sont générés par Local et peuvent être réécrits par l'application ;
le changement exige un redémarrage des 5 sites. À valider avant d'y toucher.

## 11. Vérification des liens et des chiffres du plan LTX-2 (faite le 15/09)

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


## 12. SiYuan — second cerveau (15/09/2026)

- **Version installée** : 3.8.2 (winget, installation par utilisateur), noyau
  `SiYuan-Kernel 3.8.2`, `pandoc 3.10.1` embarqué.
- **Workspace** : `C:\Users\searc\SiYuan\hermes-projects` (conf, data, bases reconstruites).
- **Sécurité** : le noyau n'écoute que sur `127.0.0.1:6806`, jamais sur `0.0.0.0`. L'interface
  web exige l'`accessAuthCode` (code généré à l'installation, présent dans
  `hermes-projects\conf\conf.json`) ; les API exigent `api.token`, un secret distinct, placé dans
  `%LOCALAPPDATA%\hermes\.env` sous `SIYUAN_TOKEN`. Le refus a été testé : sans jeton, avec un
  mauvais jeton, et avec l'accessAuthCode à la place du jeton d'API, le noyau répond
  `Auth failed` — l'authentification est donc réellement active.
- **Test de connexion** : `POST /api/notebook/lsNotebooks` → `{"code":0,"data":{"notebooks":[]}}`,
  et `POST /api/query/sql` (`SELECT COUNT(*) FROM blocks`) → `[{"n":0}]`. Vérifié deux fois : une
  fois avec le noyau lancé avec le secret en ligne de commande, une fois relancé sans lui
  (conf.json relu) — c'est cette seconde vérification qui prouve que l'installation est durable.
- **Skill** : `productivity/siyuan` installé depuis le dépôt officiel (verdict d'analyse autorisé),
  prérequis `jq` installé (1.8.2).
- **Non fait volontairement** : aucune synchronisation S3/WebDAV (à discuter), aucun notebook créé
  (proposition en attente de validation), `config.yaml` de Hermes non modifié. Le serveur MCP
  optionnel mentionné par le skill n'a pas été installé — il exige une modification de `config.yaml`.

Point à trancher : le code d'accès de l'interface web est celui généré à l'installation et se trouve
dans `conf.json`. Si tu préfères le choisir toi-même, dis-le et je le remplace dans le fichier (le
noyau le relit au démarrage).

Premiers contenus déposés dans le second cerveau, sur ta demande : notebook `hermes-skills` avec
« Automatisation des réseaux sociaux » (les cinq CLI — Twitter, LinkedIn, Discord, Telegram,
Instagram — avec leurs prompts d'installation et la mise à jour quotidienne) et « Veille
technologique et mise à jour » (prompt d'auto-mise à jour de Hermes, et la trame du rapport techno
quotidien). Importés depuis `Desktop\skills siYUAN\`, à l'identique, accents et emojis compris.
Ce sont des notes, pas des skills Hermes : aucun frontmatter, contenu rédigé.

## 13. Structure du second cerveau (15/09/2026)

Six notebooks, 23 documents au total (21 créés ce jour, 2 notes d'origine intactes) :

| Notebook | Documents | Contenu |
|---|---|---|
| `hermes-projets` | 5 | Un par site Local : oldstyle, reold, searching-murphy, SM, the one |
| `hermes-skills` | 12 | Les 2 notes d'origine + un document par skill réellement utilisé (10) |
| `video-ia` | 3 | Une par branche : A LatentSync, B source photo, C LTX-2.3 |
| `apprentissage-continu` | 0 | Vide volontairement : à remplir avec la Phase 1 |
| `journal` | 1 | La panne LTX-2.3 du 15/09 (symptôme, mesures, cause, correctif, prévention) |
| `veille` | 2 | Sources suivies (seulement ce que la note d'origine ne couvre pas), idées en attente |

Les documents `hermes-projets` ne contiennent aucune donnée inventée : versions WordPress / PHP /
MySQL / nginx lues dans `%APPDATA%\Local\sites.json`, extensions et numéros de version lus dans les
fichiers des extensions, état actif déduit du dump SQL de sauvegarde (et signalé comme tel), date et
taille de la dernière sauvegarde lues sur disque. Les documents `hermes-skills` sont extraits
verbatim des fichiers `SKILL.md` (rôle, version, pièges, commandes) ; le fichier du skill reste la
référence.

Convention appliquée à chaque document : en-tête `> **Statut**` et `> **Dernière mise à jour**`, puis
Fait / Reste à faire / Pièges / Commandes.

Le script `C:\Users\searc\SiYuan\construire_structure.py` reconstruit l'ensemble et ne touche à aucun
document existant ; `gather_sites.py` relit l'état des sites Local.

## 14. Code d'accès et démarrage automatique (15/09/2026)

- Code d'accès de l'interface web remplacé par celui choisi par l'utilisateur (`Hermes@SiYuan2026`),
  dans `hermes-projects\conf\conf.json`, après sauvegarde du fichier et avec le noyau arrêté (il
  réécrit sa configuration en s'arrêtant). Le jeton d'API n'a pas été touché.
  Vérifié : interface sans code → HTTP 401 ; avec le nouveau code → `code 0` ; avec un mauvais code →
  refus explicite ; API avec le jeton d'API → toujours `code 0`.
- Tâche planifiée **utilisateur** (pas système, sans privilège élevé) « SiYuan - noyau second
  cerveau », déclenchée à l'ouverture de session, qui lance `demarrer_siyuan.cmd`. Le script vérifie
  d'abord que le port 6806 est libre et ne fait rien si le noyau tourne déjà ; la tâche est en
  `MultipleInstances IgnoreNew` et sans limite de durée.
  Vérifié en déclenchant réellement la tâche : noyau démarré (nouveau processus en écoute sur
  6806), API opérationnelle. C'est un test du déclencheur, pas seulement de la création.
