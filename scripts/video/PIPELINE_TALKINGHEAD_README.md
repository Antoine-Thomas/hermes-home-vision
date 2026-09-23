# Pipeline talking-head — porte d'entree unique

Un volet (une video YouTube) se fabrique d'un bout a l'autre avec **un seul script** :

    C:\Users\searc\AppData\Local\hermes\data\video_youtube\pipeline_talkinghead.py

Il enchaine les neuf etapes validees sur les volets 3, 4 et 5 et ecrit tout dans
`LatentSync\tests\v4_talking_head_<volet>\`. Rien n'est a relancer a la main, rien n'est
a recopier d'un volet a l'autre.

Derniere revision de ce document : **20/09/2026** (apres le volet 5).

---

## 1. Vue d'ensemble

    rush video ─┐
                ├─ a) audit de la source ................. audit_<v>_<label>.json
                │     frames sans visage, stabilite, nettete, keyframes
                ├─ b) choix de la fenetre ................. fenetre_<v>.json
                │     composite nettete 0,40 / stabilite 0,25 / centrage 0,20 / mouvement 0,15
                │     (+ 0,10 si la fenetre demarre sur une keyframe)
                ├─ c) extraction .......................... source_<v>.mp4
                │     `-c copy` si keyframe ; sinon reencodage crf 14
                ├─ d) stabilisation verticale ............. source_<v>_stab.mp4
                │     recadrage dynamique 90 % + Savitzky-Golay (7,2), k choisi (0,65)
    audio clone ─┐  │
                 │  ├─ e) boucle .......................... source_<v>_loop.mp4
                 │  │     strategie selon la duree de l'audio + mesures des jonctions
                 │  ├─ f) LatentSync 1.5 ................... sortie_latentsync_<v>.mp4
                 │  │     stage2.yaml 256 px, 20 pas, guidance 1.5, deepcache, moniteur
                 │  ├─ g) greffe hautes frequences ......... sortie_latentsync_<v>_hf_a<alpha>.mp4
                 │  │     alpha, masque `face`, blur 5, recadrage des levres
                 │  ├─ h) mesures + planche ................ mesures_hf/
                 │  └─ i) rapport MD + Telegram ............ RAPPORT_<v>.md

Le cout est entierement dans l'etape f : **149x le temps reel** mesure au volet 5
(14 h 17 pour 343,88 s de sortie, source 1080p, 8 Go de VRAM). Tout le reste se compte en
minutes.

---

## 2. Prerequis

| Element | Chemin / valeur |
|---|---|
| Interpreteur | `LatentSync\venv\Scripts\python.exe` (cv2, insightface, numpy, scipy). Le script se relance tout seul avec ce venv si `cv2` manque. |
| Depot LatentSync | `...\data\video_youtube\LatentSync` (poids `checkpoints\latentsync_unet.pt` 4,84 Go, `whisper\tiny.pt`) |
| Visages | `LatentSync\checkpoints\auxiliary\models\buffalo_l` (601 Mo, 5 modeles ONNX) |
| ffmpeg / ffprobe | dans le PATH (utilises par tous les scripts du projet) |
| Entrees | un rush video + l'audio du clone (`data\xtts\audio_youtube_<v>.wav`) |
| Skill de reference | `talking-head-video-8gb` (81 regles) — a charger avant toute intervention manuelle |

La voix se fabrique separement (`data\xtts\generer_audio_youtube_<v>b.py`) : le pipeline part
de l'audio deja produit.

---

## 3. Commandes types

### a) Verification avant de lancer (gratuit)

    cd C:\Users\searc\AppData\Local\hermes\data\video_youtube\LatentSync
    venv\Scripts\python.exe ..\pipeline_talkinghead.py ^
        --source "C:/Users/searc/Desktop/hermes tuto/talkinghead.mp4" ^
        --audio  "C:/Users/searc/AppData/Local/hermes/data/xtts/audio_youtube_v6.wav" ^
        --volet 6 --plan

### b) Preparation seule (etapes a a e, quelques minutes)

    venv\Scripts\python.exe ..\pipeline_talkinghead.py ^
        --source "..." --audio "..." --volet 6 --depuis audit
    REM puis Ctrl-C avant l'etape f, ou :
    venv\Scripts\python.exe ..\pipeline_talkinghead.py --source "..." --audio "..." ^
        --volet 6 --seulement boucle

### c) Run complet, LatentSync en tache de fond (recommande : 14 h possibles)

    venv\Scripts\python.exe ..\pipeline_talkinghead.py ^
        --source "..." --audio "..." --volet 6 --depuis latentsync --detache

Suivi du run, sans dependre de la session :

    type tests\v4_talking_head_6\moniteur_6_statut.json
    type tests\v4_talking_head_6\envois_6.log                 REM livraison Telegram, envoi par envoi
    type tests\v4_talking_head_6\latentsync_6_run.log          REM sortie complete du modele

### d) Reprendre apres une coupure

    venv\Scripts\python.exe ..\pipeline_talkinghead.py --source "..." --audio "..." ^
        --volet 6 --depuis boucle          REM les etapes deja faites sont sautees

Ou une seule etape : `--seulement latentsync|hf|mesures|rapport`. `--force` refait une etape
deja faite. Si une etape manque son entree, le pipeline le dit et nomme celle qui la produit
(« entree manquante : ..._stab.mp4 — elle est produite par l'etape d) stabilisation »).

### f) Toutes les options

| Option | Defaut | Role |
|---|---|---|
| `--source` / `--audio` / `--volet` | — | entrees et nom du dossier de travail |
| `--frames N` | 136 (5,44 s a 25 fps) | longueur de la fenetre extraite |
| `--strategie` | `auto` | `simple`, `segments` ou `ping-pong` |
| `--hauteur-loop N` | 1080 | hauteur de la source envoyee a LatentSync |
| `--alpha` / `--blur` | 1.0 / 5 | greffe hautes frequences |
| `--segmenter N` / `auto` | `0` (un seul appel) | run LatentSync en tranches de N frames |
| `--forcer-ram` | non | passe outre le controle de RAM |
| `--depuis` / `--seulement` | `audit` / — | reprise, ou une seule etape |
| `--detache` | non | LatentSync en tache de fond (recommande) |
| `--force` | non | refaire une etape deja faite |
| `--plan` | — | affiche le plan et s'arrete |

### e) Etape par etape, a la main (si un doute sur une mesure)

    venv\Scripts\python.exe tests\tester_segments.py                  REM run segmente, sans GPU
    venv\Scripts\python.exe tests\tester_moniteur.py                  REM moniteur, sur log rejoue
    venv\Scripts\python.exe tests\run_latentsync_segments.py --lister ^
        --source <loop> --audio <wav> --sortie <out> --cycle 135 --segmenter-frames 1200
    venv\Scripts\python.exe tests\post_hf_transfer.py --source <loop> --generated <latentsync> ^
        --out <hf> --alpha 1.0 --blur 5 --mask face --det-cache hf_det_<v>.npz --verify-align
    venv\Scripts\python.exe tests\hf_rapport.py --reference <loop> ^
        --colonne source=<loop> --colonne latentsync=<gen> --colonne "latentsync+HF"=<hf> ^
        --outdir tests\v4_talking_head_<v>\mesures_hf

---

## 4. Choix que le pipeline fait pour vous

- **Fenetre** : score composite normalise, jamais un critere dominant. Au volet 5, le critere
  « centrage + 2x stabilite » designait les frames 0-9 (la partie la plus molle du rush) ; le
  composite designe la frame 60, la plus nette (19,4 contre 15,3 de nettete du haut).
- **Extraction** : le GOP du rush `talkinghead.mp4` a une keyframe toutes les 30 frames ; une
  fenetre qui demarre dessus se coupe en `-c copy`, sans aucune perte.
- **Stabilisation** : filtre impose (Savitzky-Golay 7,2 — un gaussien ecrase les vrais
  mouvements rapides), seul `k` est choisi, pour une reduction de ~65 % de l'ecart-type du
  centre du visage, avec une vitesse de cadrage < 20 px/frame. Sortie : recadrage 90 % remis a
  l'echelle en Lanczos (11 % de champ en moins, nettete du haut intacte, −9 % sur la bouche).
- **Boucle** : `simple` si l'audio tient dans la source, sinon `segments` — des points de coupe
  cherches la ou les frames se ressemblent, classes sur la **moyenne** des jonctions (c'est elle
  qui defile 60 a 80 fois sur un volet) et non sur la seule pire. `ping-pong` reste disponible
  (`--strategie ping-pong`) mais **ne doit pas** servir a un talking head : le raccord est
  pixel-parfait, sauf que la bouche repart en arriere deux fois par cycle.
  La source de boucle est **ramenee a 1080p** (`--hauteur-loop`, defaut 1080) : c'est la
  resolution de travail du volet 5, et le 4K quadruplerait la RAM exigee par le modele.
- **Budget RAM verifie AVANT l'etape f.** LatentSync decode toute la video en memoire systeme
  (`frames x largeur x hauteur x 3`). Le pipeline mesure la RAM libre et **s'arrete** si le
  besoin depasse 60 % de celle-ci, au lieu de laisser la machine paginer quatorze heures :
  au volet 5, 49 Go exiges pour 2,6 Go libres. Message obtenu en rejouant le volet 5 :
  « LatentSync decoderait 49.8 Go en RAM pour 43.6 Go libres ». Trois issues : `--segmenter
  auto` (recommande, voir ci-dessous), un `--segmenter N` a la main, ou `--forcer-ram` en
  connaissance de cause.

### Le run segmente (`--segmenter`)

Le pipeline decoupe la source ET l'audio en tranches, lance une inference par tranche, puis
concatie en `-c copy`. C'est le remede au mur de RAM, et il est **automatique** :

- `--segmenter auto` prend le plus grand multiple du cycle de la boucle qui tient dans 60 % de
  la RAM libre. Sur ce poste (1920x1080, cycle de 135 frames) : 4 050 frames (162 s, 23,5 Go)
  quand 40 Go sont libres, 810 frames (32,4 s, 4,7 Go) quand il ne reste que 8 Go ;
- `--segmenter 1200` vise 1 200 frames et **arrondit au multiple superieur** du cycle
  (9 cycles de 135 = 1 215 frames) : la regle 58 est appliquee par construction, la pose ne
  saute pas au raccord ;
- la duree d'une tranche n'a pas a diviser la video : la derniere tranche est plus courte ;
- `--frames`/`--fps` sont repris des mesures de l'etape e : pas de recomptage de 8 600 frames.

Chaque tranche est reprise si elle existe deja (`tests\v4_talking_head_<v>\
segments_latentsync_<v>\`), donc un plantage a la tranche 6 sur 8 ne fait pas repartir de zero.
Les tranches de sortie sont conservees expres : elles permettent de refaire une seule tranche.

Le pipeline lance le moniteur avec `--commande-json` : la surveillance GPU (VRAM, temperature,
nvlddmkm) et l'arret d'urgence restent actifs, et la progression suit chaque tranche
(`tranche : 3/8`, `avancement : 31,2 % du run`). C'est la raison pour laquelle l'arret
d'urgence tue l'ARBRE de processus et non le seul enfant : en mode segmente l'enfant est le
script de tranches, le vrai processus d'inference est son petit-fils.
- **Greffe HF** : masque `face` (le fond est de la vraie 4K, on ne l'accentue pas), `blur 5`,
  et l'alpha se choisit sur la nettete de la source — 0,7 pour un rush net, 1,0 pour un rush
  mou (regle 74). Le pipeline ne decide pas a votre place : `--alpha`.

---

## 5. Pieges connus (chacun a coute un run)

1. **Le mur de LatentSync est la RAM systeme, pas la VRAM.** 8 600 frames de 1080p = 49 Go de
   RAM mesuree : la cadence est tombee de 13 s/it a 116-127 s/it et le run a dure 14 h 17 au
   lieu des 4 h 30 annoncees. Au-dela d'une minute de sortie : `--segmenter auto`, qui regle la
   taille des tranches sur la RAM libre.
2. **Un segment doit etre un multiple du cycle de la source** (16 s pour une source de 200
   frames, 5,40 s pour la boucle de 135 frames du volet 5), sinon la pose saute a chaque
   raccord (mesure : x9 le mouvement normal). `--segmenter` l'arrondit tout seul et l'audio est
   coupe en WAV, sur des echantillons exacts (un AAC se couperait sur des trames de ~21 ms).
3. **Jamais de fondu enchainé sur la source** destinee au ping-pong : le fondu fabrique un flou
   de liaison a chaque cycle (~80 fois sur 5 min).
4. **La source doit couvrir toute la duree de l'audio** : sinon le modele termine la fin en
   inversant la boucle et le visage parle a l'envers, sans un mot dans les logs. Le pipeline
   verifie ce point a l'etape e et s'arrete si la boucle est trop courte.
5. **Telegram : texte sans chevron et sans `parse_mode`.** Un ETA de tqdm (`01:55<00:00`) fait
   rejeter le message en HTTP 400 ; le canal casse ressemble exactement a un run mort. Le
   moniteur journalise chaque envoi (`envois_<v>.log`) et horodate le dernier succes
   (`dernier_envoi_<v>.json`) — c'est ce battement de coeur qu'un watchdog doit lire.
6. **Lire la barre `Doing inference`, pas la derniere barre vue.** La barre interieure
   `Sample frames: 16` est reecrite ~21 fois par iteration : la lire fait osciller le
   pourcentage affiche entre 0 et 100 (23 085 fragments de log, 540 barres externes).
7. **Ne jamais mettre `PYTORCH_CUDA_ALLOC_CONF`** : `max_split_size_mb:128` rend le rendu 22x
   plus lent sur cette machine (94 s/lot au lieu de 4,2).
8. **`ffprobe -show_entries frame=pts_time,key_frame` renvoie `key_frame,pts_time`** sur cette
   version. Trier par position de colonne donne 0 keyframe sur un GOP regulier : parser les
   deux champs par leur forme (voir `keyframes()` dans le pipeline).
9. **Ne pas mettre `-shortest`** entre une video et un audio plus court : la sortie perd ses
   dernieres frames (137 -> 133). Utiliser `-frames:v N` et copier l'audio.
10. **`h264_nvenc`/`cpu` et les pipes rawvideo** : un pipe declare en 3840x2160 qui recoit du
    1280x720 produit un fichier de 22 frames, sans erreur bloquante.

---

## 6. Fichiers de reference

### Le pipeline

| Fichier | Role |
|---|---|
| `data\video_youtube\pipeline_talkinghead.py` | orchestrateur (etapes a a i) |
| `LatentSync\tests\surveiller_latentsync.py` | moniteur de run : progression reelle, VRAM, temperature, events, Telegram, statut JSON |
| `LatentSync\tests\v4_talking_head_v5\surveiller_latentsync_v5.py` | lanceur conservant l'invocation historique du volet 5 |
| `LatentSync\tests\tester_moniteur.py` | test du moniteur sur un log rejoue (aucun GPU) |
| `LatentSync\tests\run_latentsync_segments.py` | run segmente : tranches source+audio, une inference par tranche, concat `-c copy`, reprise par tranche |
| `LatentSync\tests\tester_segments.py` | test du run segmente sans GPU : taille des tranches, cablage de l'etape f, plan reel |
| `LatentSync\tests\post_hf_transfer.py` | greffe hautes frequences (alpha, masque, garde des levres) |
| `LatentSync\tests\hf_rapport.py` | mesures de nettete + planche comparative |
| `LatentSync\tests\audit_source.py` | audit de ralentissement/duplication d'une source |

### Les etapes validees des volets precedents (gardees comme temoins)

`tests\v4_talking_head_v3\` : `audit_v3.py`, `score_v3.py` (score composite), `reperes_v5.py`,
`choisir_stab_v5.py`, `rendre_stab_v5.py`, `verifier_stab_v5.py`, `mesurer_boucles_v5.py`,
`envoyer_telegram_v4.py`, `source_v5_loop_344.mp4` (source du volet 5, conservee).

### Documentation

- `docs\LORA_VISAGE_RUN_2026-09-17.md` — run LoRA visage (document de reference).
- Skill `talking-head-video-8gb` (81 regles) — a charger avant toute intervention manuelle ;
  les regles 72 a 81 sont celles payees par le volet 5.
- SiYuan : `video-ia / Pipeline video - orchestrateur`.

---

## 7. Apres un volet : nettoyage

A la fin d'un volet, les dossiers de travail representent plusieurs gigaoctets et ne servent
plus. Sont a supprimer (jamais les livrables) :

    tests\v4_talking_head_<v>\mesures_hf\frames_hf\      REM frames de mesure
    LatentSync\temp_<v>\                                 REM source + audio de travail du modele
    LatentSync\tests\v4_talking_head_<v>\ffmpeg2pass-*   REM restes d'encodage 2 passes

Ce qu'il faut **garder** : la sortie finale (`sortie_latentsync_<v>_final_1080p.mp4`), la
version HF, l'audio (`audio_youtube_<v>.wav/.mp3`), le script (`script_youtube_<v>.txt` et sa
version prononcee), `planche_hf.png`, `mesures_hf.json`, la source de boucle, `RAPPORT_<v>.md`
et tous les scripts.
