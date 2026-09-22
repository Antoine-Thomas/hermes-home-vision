---
name: talking-head-video-8gb
description: "Vidéo talking-head sur GPU 8 Go : deux branches à ne jamais confondre — source vidéo (LatentSync + transfert passe-haut 4K) ou source photo (LivePortrait/SadTalker/Wav2Lip). À charger pour toute génération talking-head sur cette machine."
version: "1.9.0"
author: Searching Murphy
license: MIT
tags:
  - liveportrait
  - sadtalker
  - wav2lip
  - real-esrgan
  - vram-optimization
  - 8gb-gpu
  - talking-head
  - video-4k
---

# Talking Head Video 8GB VRAM

## Quand utiliser ce skill

TOUJOURS quand l'utilisateur demande une vidéo talking-head, ou quand le pipeline implique LivePortrait, SadTalker, Wav2Lip ou Real-ESRGAN sur cette machine (RTX 3070 Ti, 8 Go VRAM).

## ComfyUI : le template Z-Image Turbo au demarrage (constate le 16/09/2026)

A l'ouverture de `http://127.0.0.1:8188/`, l'interface affiche un workflow **Z-Image Turbo** avec deux
erreurs de modeles manquants (`qwen_3_4b.safetensors` 7,49 Go et `z_image_turbo_bf16.safetensors`
11,46 Go).

**Origine** : aucun node pack. C'est la **bibliotheque de templates livree avec ComfyUI v0.35** —
`python_embeded\Lib\site-packages\comfyui_workflow_templates_json\templates\` (paquet date du
09/09/2026). Huit templates de cette bibliotheque referencent ces deux modeles ; l'interface affiche
celui que le navigateur avait ouvert en dernier.

**Ne PAS les telecharger** : 11,46 Go en bf16 ne tiennent pas dans 8 Go de VRAM, et la chaine LTX-2.3
n'en a aucun besoin.

**Ce qui a ete fait** :

- `image_z_image.json` neutralise (`image_z_image.json.desactive`, sauvegarde `.bak` a cote) ;
- notre workflow LTX-2.3 installe dans `ComfyUI\user\default\workflows\`
  (`LTX-2.3 (workflow node pack).json`) : il s'ouvre depuis la barre laterale des workflows ;
- les sept autres templates Z-Image laisses en place (les neutraliser tous serait invasif et ne
  changerait rien : le workflow reellement affiche depend de l'etat du navigateur, pas du disque).

**Pour ouvrir la bonne chaine** : barre laterale -> Workflows -> `LTX-2.3 (workflow node pack)`, ou
lancer `ltx_test.py` (workflow LTX-2.3 au format API, celui qui a produit les rendus valides).


## REGLE 0 — APRES TOUT RENDU, LIRE LE RAPPORT QUALITE AVANT D'OUVRIR LA VIDEO

**Pipeline complet disponible : `pipeline_video.py`** (dossier `hermes_tuto_v4`). Il enchaîne tout —
lexique, XTTS, découpe, LatentSync, assemblage, contrôle qualité — en une commande :

```
python pipeline_video.py --script mon_script.txt --voix v9 --qualite --source p1002837
```

`--dry-run` liste sans exécuter, `--sans-etape N` reprend après une coupure (l'assemblage est
l'étape 5), `--force` autorise l'écrasement (sans lui, le pipeline **s'arrête** si une sortie
existe). Aucun script n'est modifié : les scripts à constantes figées sont exécutés via une copie
substituée dans le dossier temporaire. Détail : SiYuan `video-ia / Pipeline vidéo - orchestrateur`.

`assemble_v6.py` (mode `run`) appelle `controle_qualite.py` a la fin du rendu et ecrit
`rapport_qualite_<horodatage>.json` et `.txt` dans le dossier du mp4. **Ouvrir le rapport en
premier** : il dit ou regarder, et evite de chercher a l'oeil un defaut deja mesure.

Quatre controles, avec seuils : sauts d'image (MAD > 4x la mediane), flou de liaison (bandes
laterales sous 75 % de la mediane), fantomes sur les levres (cretes > 1,25x la source), bout des
levres (force du contour < 0,95x la source). Code de sortie : 0 OK, 1 ATTENTION, 2 ALERTE.

La video n'est **jamais** supprimee, meme en ALERTE : c'est volontaire, pour pouvoir la regarder.
Un ALERTE sur les sauts a intervalles reguliers (ex. toutes les 51 s) designe les frontieres de
segments LatentSync, pas un defaut de rendu. `V4_SANS_QUALITE=1` desactive le controle.

## PORTE D'ENTREE UNIQUE — pipeline_talkinghead.py (consolide le 20/09/2026)

Un volet complet se fabrique desormais avec UN script, qui enchaine les neuf etapes validees
sur les volets 3, 4 et 5 (audit, fenetre, extraction, stabilisation, boucle, LatentSync, greffe
HF, mesures, rapport + Telegram) :

```
C:\Users\searc\AppData\Local\hermes\data\video_youtube\pipeline_talkinghead.py
```

Lancer avec le python du venv LatentSync (`<racine>/venv/Scripts/python.exe`) ; le script se
relance tout seul avec ce venv si `cv2` manque. `--plan` liste sans rien executer, `--depuis
ETAPE` reprend apres une coupure, `--seulement ETAPE` ne fait qu'une etape, `--detache` lance
LatentSync en tache de fond (obligatoire pour un run de plusieurs heures).

Documentation complete (prerequis, commandes, pieges, fichiers de reference) :
`data\video_youtube\PIPELINE_TALKINGHEAD_README.md` — c'est la porte d'entree a lire AVANT de
lancer un volet. Ce skill reste la reference des regles ; le README est la reference des
commandes.

Verifie le 20/09/2026 en rejouant le rush du volet 5 (`talkinghead.mp4`, 227 frames 4K) :
l'etape b designe bien la **frame 60** (composite 0,727 contre 0,700 pour la frame 0 que le
critere naif choisissait), l'etape c coupe en `-c copy` (keyframe toutes les 30 frames), et
l'etape d reproduit la mesure du volet 5 : **28,89 -> 11,56 px d'ecart-type vertical (−60,0 %)**
avec Savitzky-Golay (7,2) et k=0,65, contre 28,86 -> 11,19 px (−61,2 %) a la main.

## TROIS BRANCHES A NE JAMAIS CONFONDRE

Ce skill couvre deux pipelines differents. Le choix se fait sur la SOURCE, jamais sur le rendu.

BRANCHE A — SOURCE VIDEO (une vraie prise de vue, ex. P1002837.MP4 4K 50 fps)
  La personne est filmee : la source fournit le mouvement, la pose et le detail reel.
  Chaine : source 4K decimee a 25 fps -> boucle ping-pong -> LatentSync (segments) ->
  transfert passe-haut 4K pleine image + recadrage des levres -> unsharp + logo.
  Regles concernees : 19, 25, 27, 33, 36 a 38, 40 a 51, 52, 53, 55 a 59.
  Propre a cette branche :
    - le cycle ping-pong de LatentSync (400 frames = 16 s) et la longueur de segment qui doit
      en etre un multiple (regle 58) ; la boucle de source SANS fondu (regle 52) ;
    - le recadrage des levres frame par frame (regle 57) ;
    - le transfert passe-haut pleine image (regle 53) ;
    - la superiorite mesuree d'une vraie prise de vue sur un portrait restaure (regle 50).

BRANCHE B — SOURCE PHOTO (un portrait fixe, ex. « portrait pour v4.jpg »)
  Aucun mouvement n'existe dans la source : c'est le modele qui l'invente.
  Chaine : restauration du portrait (GFPGAN / Real-ESRGAN) -> animation (LivePortrait,
  SadTalker, Wav2Lip, MuseTalk) -> fond flou + visage plein cadre -> unsharp + logo.
  Regles concernees : 1 a 18, 20 a 24, 26, 28 a 32, 34, 35, 39, 45.
  Propre a cette branche :
    - fond flou et cadrage (regles 11, 12, 39) parce que la source n'a pas de fond ;
    - restauration de visage et son plafond mesure (regles 31, 35, 50) ;
    - LivePortrait / MuseTalk et leurs limites de resolution (regles 2, 34).

## BRANCHE C — GENERATION IA (texte ou image -> video, via LTX-2.3 GGUF dans ComfyUI)
  Aucune source reelle : la video est entierement generee. Pas de synchronisation labiale
  avec un audio existant, pas de boucle, pas de decoupage. Voir l'annexe branche C plus bas pour la
  chaine d'outils exacte et les volumes mesures.
  Propre a cette branche :
    - choix du quant GGUF selon la VRAM (Q4_K_S = 12,96 Go pour le 22B) ;
    - `--offload cpu` et quantification fp8 des que la VRAM est < 12 Go (cas d'une 3070 Ti) ;
    - poids sur NVMe (streaming des couches depuis le disque) ;
    - temps de generation proportionnel a la duree demandee (minutes par seconde de video).

CE QUI NE TRANSFERE PAS DEPUIS A OU B VERS C : la boucle ping-pong (C n'a pas de source a
boucler), le decoupage LatentSync, le recadrage des levres, le transfert passe-haut 4K
(il n'y a pas de source fine a transférer), ni le masquage des levres.

CE QUI NE TRANSFERT PAS D'UNE BRANCHE A L'AUTRE (pieges deja payes)
  - Recette de boucle video (fenetre + fondu) : inutile sur une photo (ni mouvement ni
    couture) mais NUISIBLE sur une video, ou le fondu fabrique un flou de liaison a chaque
    cycle (regle 52). La regle 48 (scan de fenetre) reste bonne pour choisir la fenetre ;
    son etape de fondu est remplacee par « aucun fondu » .
  - Decoupage LatentSync : sur une photo, des segments quelconques ne se voient pas ; sur une
    video, la duree doit etre un multiple du cycle ping-pong, sinon la pose saute (regle 58).
    (La regle 42, « decouper ne cree pas de joint », ne vaut que pour une source quasi
    statique : elle est corrigee.)
  - Recadrage des levres (regle 57) : n'a de sens que si la source bouge et que sa bouche
    differe de la bouche generee. Sur une photo, la source est une image fixe : on masque
    entierement les levres (regle 37).
  - Transfert passe-haut : valable dans les deux cas, mais pour une photo la source est une
    image fixe (aucun detail temporel a recuperer) ; sur une video il est pleine image
    (regle 53) et recale sur les levres (regle 57).
  - Commun aux deux branches : la voix (regles 27, 54, 59), le format de sortie (15, 25, 33),
    la mesure (32, 38, 43, 44, 49, 56) et la VRAM (1, 3, 10, 55).

BRANCHE A — RECETTE VALIDEE (volet 4, P1002837, mesuree le 15/09/2026)
  1. boucle_p1002837.py : fenetre de 8 s (200 frames a 25 fps) minimisant l'ecart de pose.
  2. prep_p1002837.py 55 254 --no-fade --suffix=_clean : source 720p + source 4K, sans fondu.
  3. run_latentsync_v8b.py : audio decoupe en WAV sur des multiples de 16 s, segments de 48 s,
     -> latentsync_p1002837_v8b.mp4.
  4. assemble_v6.py run avec V4_KEEP=1.00 et V4_LIPALIGN=1 : passe-haut 4K pleine image,
     recadrage des levres par frame, unsharp 5:5:0,8, logo 280 px marge 40 alpha 0,9, CRF 16.
  5. Controle : verifier_v6.py (cotes, levres, logo, duree) + diag_sauts.py (sauts d'image aux
     raccords, clics et pauses audio) + tableau_levres.py / fidelite_hf.py pour la finesse.
  Resultats obtenus : cotes a 3,1-3,4x la source (Laplacien), contour des levres 1,33x la
  source, densite de contours 1,49x (pas de double levre), aucun pic de saut aux 5 raccords
  (max 1,22 contre 6,5 avant correction), 0 clic audio.
  Scripts de reference : Desktop/hermes_tuto_v4/ (meme machine).

### Annexe branche C — LTX-2.3 GGUF dans ComfyUI (chaine VALIDEE, mesures du 15/09/2026)

Resultats mesures sur cette machine (RTX 3070 Ti 8 Go, 640x384, 25 images, 24 i/s, 8 etapes,
Q4_K_S, offload=True, mode distilled) : 132,79 s a froid / 205,11 s a chaud, soit 5,3 a 8,2 s
par image et 16,6 a 25,6 s par etape. Autrement dit 127 a 197 fois le temps reel : compter 2 a
3,5 minutes de GPU par seconde de video generee. La sortie contient une piste AUDIO (modele
audio-video). Contenu verifie par mesure (ecart-type spatial 54 a 75, mouvement present) et non
seulement par l'absence d'erreur.

CORRECTION DU 22/09/2026 — LE COUT EST UN FORFAIT PAR CLIP, PAS PAR SECONDE. Trois rendus
mesures le meme jour, memes reglages (640x384, 8 etapes, distilled, offload), duree de video
triplee entre le premier et le troisieme :

| frames | duree video | total | dont echantillonneur |
|---|---|---|---|
| 25 | 1,0 s | 170,6 s | 93 s |
| 49 | 2,0 s | 150,8 s | 89 s |
| 97 | 4,0 s | 161,1 s | 98 s |

Le total ne bouge pas de plus de 10 % quand la video quadruple, et l'echantillonneur reste entre
89 et 98 s (~11 a 12 s par pas, 8 pas) : le cout est domine par le rechargement du transformer de
13 Go et son transfert dans 8 Go de VRAM, pas par le nombre d'images. Donc : annoncer un forfait
d'environ 2,5 a 3 min par clip a cette resolution, et rappeler que la premiere execution apres le
demarrage du serveur coute ~20 s de plus (lecture disque des 13 Go de GGUF et des 8,7 Go de
Gemma). La projection « 2 a 3,5 minutes par seconde de video » ne vaut que pour les 25 premieres
images ; ne pas la reprendre pour un clip plus long.

WORKFLOW POUR L'INTERFACE (ajoute le 22/09/2026) : le graphe valide s'exporte au format API et
s'importe dans l'interface ComfyUI (`isApiJson` -> `loadApiJson` du frontend), donc `ltx_test.py`
n'est PAS le seul moyen de lancer une generation. `exporter_workflow_api.py` (dossier
`ComfyUI-LTX`) tronque la source de `ltx_test.py` juste avant l'envoi HTTP et execute le reste :
l'export est forcement identique a ce que le script envoie. Il ecrit
`ComfyUI\user\default\workflows\LTX-2.3 GGUF 8 Go (valide).json`, visible dans la barre laterale.
Verification sans navigateur : les 11 types de noeuds du fichier doivent tous figurer dans
`GET /object_info` du serveur en cours, et le fichier doit etre servi par
`GET /api/userdata/workflows%2F<fichier encode>` (un `/` NON encode ne matche pas la route
aiohttp `/userdata/{file}` : le 404 ne veut pas dire que le fichier est absent ; la liste
`GET /api/userdata?dir=workflows&recurse=true` est le controle le plus simple).
PIEGE : le workflow deja present dans cette installation, `LTX-2.3 (workflow node pack).json`,
n'est PAS la chaine GGUF — il reclame `ltx-2.3-22b-dev.safetensors` + `comfy_gemma_3_12B_it.safetensors`
(une chaine 22B non quantifiee) et une quarantaine de Go absents. Le verifier en listant les
noms de fichiers de modeles presents dans le JSON et en les cherchant sur disque avant de le
proposer a l'utilisateur.

`mesure_sortie.py` (dossier `ComfyUI-LTX`) mesure une sortie sans la regarder : ecart-type
spatial par frame (image unie = generation ratee) et ecart moyen entre frames voisines (mouvement).
Lui passer un chemin NATIF `C:/...` : un chemin MSYS `/c/...` fait echouer ffmpeg en silence et le
script leve alors `cannot reshape array of size 0`, ce qui ressemble a un bug de mesure.
`ltx_test.py` accepte un 6e argument (la graine), ce qui permet de rejouer un graphe sans
retomber sur le meme prompt (cache de ComfyUI).

ComfyUI v0.35+ integre LTX-2 dans son coeur (pas besoin de noeud pour le modele lui-meme),
mais le README officiel de ComfyUI-LTXVideo annonce 32 Go de VRAM : sur 8 Go il FAUT passer
par un transformer GGUF et un chargeur GGUF.

Chaine retenue et MESUREE (aucun depot protege, 27,7 Go telecharges) :
  - ComfyUI portable Windows nvidia v0.35 (1,91 Go) :
    https://github.com/Comfy-Org/ComfyUI/releases/download/v0.35.0/ComfyUI_windows_portable_nvidia.7z
  - noeuds : `smthemex/ComfyUI_LTX2_SM` (obligatoire) + `city96/ComfyUI-GGUF`
  - transformer  `unsloth/LTX-2.3-GGUF` : distilled-1.1/ltx-2.3-22b-distilled-1.1-Q4_K_S.gguf (12,96 Go)
    -> ComfyUI/models/gguf/
  - text encoder `smthem/LTX-2.3-test-gguf` (MIT) : gemma-3-12b-it-qat-Q4_0.gguf (8,70 Go)
    -> ComfyUI/models/gguf/ (et non text_encoders/ : le noeud LTX2_SM_Clip lit `gguf`)
  - CONNECTEURS  `smthem/LTX-2.3-test-gguf` : connector-11.safetensors (6,34 Go)
    -> ComfyUI/models/checkpoints/   <<< PIECE OBLIGATOIRE, voir piege 1
  - VAE          `unsloth/LTX-2.3-GGUF` : ltx-2.3-22b-distilled_video_vae.safetensors (1,45 Go)
    + audio_vae (0,36 Go) -> ComfyUI/models/vae/
  Total 30,4 Go avec les connecteurs.

Pieges verifies, dans l'ordre ou ils mordent :
  1. NE PAS prendre les connecteurs chez unsloth. Le fichier
     `ltx-2.3-22b-distilled_embeddings_connectors.safetensors` (2,31 Go) ne contient que
     4 tenseurs (`text_embedding_projection.*_aggregate_embed.*`) ; le noeud attend les cles
     `...video_embeddings_connector.*` et `...audio_embeddings_connector.*` et echoue en
     `NotImplementedError: Cannot copy out of meta tensor; no data!` (parametres restes sur le
     disque virtuel). Il faut `connector-11.safetensors` (6,34 Go), extrait du checkpoint
     officiel par l'auteur du noeud. Diagnostic express : lire l'en-tete du .safetensors
     (`struct.unpack('<Q', f.read(8))` puis json des noms de tenseurs) AVANT de lancer
     ComfyUI, ca evite 10 minutes de chargement pour rien.
  2. `transformers` 5.x casse le noeud : `'SiglipVisionModel' object has no attribute
     'vision_model'` puis `'Gemma3TextConfig' object has no attribute 'rope_local_base_freq'`
     (champs renommes en 5.x). Fixer `transformers<5` -> 4.57.6. ComfyUI l'autorise
     (`transformers>=4.50.3` dans requirements.txt) : verifier cette borne avant de douter.
  3. `diffusers` 0.40 exige `huggingface-hub>=1.23`, incompatible avec transformers 4.57 :
     prendre `diffusers==0.36.0` (les utilitaires GGUF `diffusers.quantizers.gguf` y sont).
  4. `cv2` n'est pas dans le python portable : `pip install opencv-python-headless`.
  5. curl, 7z et python sont des binaires NATIFS : leur passer des chemins `C:/...` et jamais
     `/c/...`, sinon `curl: (23) client returned ERROR on write` et un fichier jamais ecrit.
  6. Le script de telechargement doit utiliser `curl -C -` (reprise) et verifier la TAILLE
     finale : un fichier tronque se charge ensuite en erreur opaque dans ComfyUI.
  7. Le noeud `smthemex/ComfyUI_LTX2_SM` ne supporte QUE la 2.3 (annonce 6 Go VRAM + 48 Go RAM) :
     ne pas l'installer en esperant y charger une 2.5.
  9. Un GGUF quantifie ne garantit pas que TOUS les modules hors blocs arrivent : avec le
     Q4_K_S d'unsloth, `patchify_proj` (Linear 4096x128) et les `adaln_single` restaient sur le
     disque virtuel et le noeud plantait a l'echantillonneur avec `Cannot copy out of meta
     tensor`. CAUSE REELLE, trouvee en trois mesures : `load_sd` renvoyait un dictionnaire VIDE
     (0 cle sur 4444) parce que les operations de renommage du noeud ne s'appliquent pas a ce
     GGUF, dont les noms bruts correspondent pourtant exactement a ceux du modele. Correctif :
     dans `LTX2/ltx_core/loader/single_gpu_model_builder.py`, fonction `load_sd`, branche
     `use_gguf`, relire le GGUF avec `load_gguf_checkpoint(paths[0], sd_ops=None)` quand le
     resultat est vide. Apres correctif : 4444 cles, intersection complete, 0 parametre fantome.
     REFLEXE a avoir avant de telecharger quoi que ce soit :
       - `grep -a "Uninitialized parameters" comfyui.log` : le constructeur du noeud nomme
         lui-meme les modules vides (il ne leve pas d'exception, il avertit et continue) ;
       - comparer le nombre de cles du dictionnaire charge au nombre de parametres du modele
         (afficher les deux, ne jamais supposer) ;
       - instrumenter `setup_for_inference` pour compter les parametres `is_meta` du modele :
         « 4186 sur 4186 » designe un chargement vide, « 0 sur 4186 » un modele sain.
     Piege secondaire : dans ce code, certaines entrees de `self.submodule` sont des PARAMETRES
     nus (`scale_shift_table`), pas des modules : tester `isinstance(m, torch.nn.Module)` avant
     d'appeler `named_parameters()` ou `.to()`, sinon l'instrumentation elle-meme plante.
  8. Placer les poids sur le NVMe, et reutiliser le meme fichier dans deux dossiers attendus
     differemment (`models/gguf` et `models/unet`) par un LIEN DUR (`ln`) : zero octet double.

## Règle n°1  Vérifier la VRAM avant tout lancement

Commande :
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv,noheader

Si VRAM > 1500 Mo, un autre processus l'utilise. Attendre ou identifier le coupable.

## Règle n°2  LivePortrait : source-max-dim 320 maximum

512p et 384p consomment 7,7 Go VRAM sur 8 Go  thrashing  1,3 img/s.
320p consomme 5,2 Go  3 img/s  44 min pour 7892 frames.
256p consomme 3,5 Go  5 img/s  à utiliser si OOM.

REFUSER de lancer LivePortrait en 512p ou 384p sur cette machine.

## Règle n°3  Segmenter les runs > 3000 frames

Découper la vidéo source en segments de 80 secondes (2000 frames à 25 fps) avec ffmpeg -f segment. Traiter chaque segment séparément avec source-max-dim 320. Concaténer à la fin avec ffmpeg -f concat.

Gain : VRAM libérée entre segments  5 img/s au lieu de 1,3.

## Règle n°4  Ne jamais utiliser taskkill /F /IM python.exe

Cette commande tue TOUS les Python, y compris Hermes et les guardians.

À la place :
Get-CimInstance Win32_Process -Filter "name='python.exe'" | Select-Object ProcessId, CommandLine | Format-List
Puis : Stop-Process -Id <PID> -Force

Jamais taskkill /IM python.exe.

## Règle n°5  Real-ESRGAN : tile=400 obligatoire

RealESRGANer(scale=4, tile=400, tile_pad=10, half=True)
Jamais tile=0 (OOM garanti). Réduire à tile=256 si OOM persistant.

## Règle n°6  Ne pas combiner GFPGAN + Real-ESRGAN sur vidéo

Sur vidéo : Real-ESRGAN seul.
Sur photo < 2K : GFPGAN + Real-ESRGAN OK.

## Règle n°7  Attendre qu'un MP4 soit valide avant de le lire

LivePortrait écrit en streaming, le moov atom n'est ajouté qu'à la fermeture.
Vérifier avec : ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 fichier.mp4
Si erreur "moov atom not found"  attendre.

## Règle n°8  Vérifier --help avant tout lancement

Les versions varient. Exemple : --batch-size n'existe pas dans inference.py de LivePortrait.
Toujours faire : .\venv\Scripts\python.exe inference.py --help

## Règle n°9  Glob pour les noms de fichiers spéciaux

SadTalker génère des noms avec ##. Le cp échoue.
Utiliser : Get-ChildItem ".\results\*\*.mp4" | Copy-Item -Destination ".\output.mp4"

## Règle n°10  NE PAS exporter PYTORCH_CUDA_ALLOC_CONF sur Windows (mesuré)

« expandable_segments:True » n'est PAS supporté sous Windows (warning au démarrage),
et « max_split_size_mb:128 » y est CATASTROPHIQUE : bloquant l'allocateur de
fusionner/garder les blocs > 128 Mo, il force des cudaMalloc/cudaFree à chaque
étape, et sous WDDM ces appels sont synchrones et lents.
Mesuré sur RTX 3070 Ti / LatentSync 1.5, segment de 61 s :
  avec max_split_size_mb:128 ... 94 s/batch  (ETA 2 h 30 pour UN segment, GPU 118 W)
  sans la variable .............. 4,2 s/batch (ETA 6 min, GPU 250 W, 1950 MHz)
Soit x22 de perte. Laisser la variable NON définie. Diagnostic : GPU à 100 %
d'utilisation mais puissance très en dessous du plafond (118 W / 290 W) et cadence
qui s'effondre = churn de l'allocateur, pas un manque de VRAM.
Si un OOM survient malgré tout, réduire la résolution de la config avant de
toucher à l'allocateur.

## Règle n°11  Fond flou obligatoire

Le fond doit être un portrait flou 16:9 (1920x1080 ou 3840x2160), pas un fond noir.
Utiliser portrait_16_9_volet4_4k.png comme base. Vérifier avant assemblage.

## Règle n°12  Visage doit remplir le cadre (pas un petit carré)

LivePortrait sort en 384x384. Dans FFmpeg, TOUJOURS faire :
[1:v]scale=1080:1080,format=yuva420p[face]
Puis overlay centré. Le visage doit faire ~1080px de haut sur 1920x1080.
Un carré de 384px est INACCEPTABLE.

## Règle n°13  Voix off : qualité de diction

La diction vient du TEXTE, pas de la temperature : **0,75 avec speed 1,0 est le reglage de
livraison**, valide sur les volets 4 et 5, et on n'y touche pas. 0,85 et au-dela font trainer
les mots et produisent des passages incomprehensibles — ce n'est PAS le remede a une diction
monotone.
Ce qui corrige reellement une phrase fautive : phrases courtes (< 150 caracteres par
segment), noms propres isoles avec une pause (virgule ou point), et graphie phonetique
tranchee par le labo de diction (regle 54).
Mesure (volet 5) : `audio_youtube_v5.wav`, 873 mots, 343,8 s, 13 tranches, genere a 0,75 ->
**12 tranches sur 13** a score Whisper >= 0,90 (la 13e a 0,88 : un simple « nvidia » mal
orthographie). Le meme reglage sert en livraison et au labo, sinon le labo ne prouve rien.
Source de verite : skill `tts-voice-cloning`, section XTTS-v2 — c'est lui qui porte les
mesures de diction ; cette regle ne fait que le rappeler pour les montages video.

## Règle n°14  Dents non serrées

Wav2Lip : NE PAS utiliser --nosmooth (garde le défaut smooth).
Vérifier sur 3 frames extraites que la bouche s'ouvre correctement sur les voyelles.

## Règle n°15  Format par défaut = 1080p H.264

Sauf demande explicite du client, sortir en 1920x1080 H.264 CRF 18,
pas en 4K. Le 4K est trop lourd pour l'upscale d'une source 384p.

## Règle n°16  MuseTalk : mmcv doit rester en 2.1.0

`mim install "mmcv>=2.0.1"` installe 2.2.0, incompatible avec mmdet 3.3.0
(AssertionError "MMCV==2.2.0 is used but incompatible" au premier import).
Forcer : pip install "mmcv==2.1.0" -f https://download.openmmlab.com/mmcv/dist/cu118/torch2.0/index.html
Combinaison qui charge : mmcv 2.1.0 + mmdet 3.3.0 + mmpose 1.3.2 + mmengine 0.10.7.

## Règle n°17  MuseTalk : mmpose exige chumpy compilé hors isolation

`mim install "mmpose>=1.1.0"` échoue sur chumpy ("No module named 'pip'" dans
l'environnement de build isolé). mmpose n'est pas optionnel :
musetalk/utils/preprocessing.py l'importe pour DWPose.
Installer chumpy d'abord : pip install --no-build-isolation chumpy
puis relancer pip install "mmpose>=1.1.0".

## Règle n°18  MuseTalk : huggingface_hub doit rester en 0.30.2

Le CLI `huggingface-cli` de download_weights.sh est déprécié et pousse hub en 1.x,
ce qui casse transformers 4.39.2 (ImportError: huggingface-hub>=0.19.3,<1.0 requis).
Télécharger tous les poids AVANT, puis : pip install "huggingface_hub==0.30.2".
Deux config.json que download_weights.sh ne récupère pas et que app.py exige :
models/sd-vae/config.json et models/whisper/config.json.

## Règle n°19  LatentSync : config 1.5 = stage2.yaml, jamais stage2_512.yaml

Le repo main est taillé pour 1.6 (aucun tag 1.5, setup_env.sh pointe sur -1.6).
Poids 1.5 : ByteDance/LatentSync-1.5 (latentsync_unet.pt 5,07 Go + whisper/tiny.pt).
VERIFIE LE 19/09/2026 : sur cette machine le checkpoint a en realite ete telecharge depuis
`ByteDance/LatentSync` (depot principal, cache `models--ByteDance--LatentSync`, revision
405eda8e..., 13/09 18:52) et non depuis `-1.5`. Ne jamais deduire la version du nom du dossier
local : la lire dans le cache HuggingFace (regle 60).
Sur 8 Go, utiliser obligatoirement configs/unet/stage2.yaml (resolution 256).
configs/unet/stage2_512.yaml est la config 1.6 (512)  dépassement VRAM.
Vérifié sur RTX 3070 Ti : sortie 1080x1920 + audio, aucun OOM.

## Règle n°20  RealScaler est payant  utiliser realesrgan-ncnn-vulkan

Les releases GitHub de Djdefrag/RealScaler n'ont AUCUN asset ; la distribution est
sur itch.io à 4,99 $ minimum. Ne pas promettre un telechargement GitHub.
Alternative libre (même moteur, portable, sans CUDA ni PyTorch) :
data/video_youtube/realscaler/realesrgan-ncnn-vulkan.exe

L'exe ne prend PAS de vidéo en entrée. Workflow obligatoire :
  1. ffmpeg -i in.mp4 -qscale:v 1 -qmin 1 -qmax 1 -vsync 0 tmp_frames/frame%08d.jpg
  2. realesrgan-ncnn-vulkan.exe -i tmp_frames -o out_frames -n realesr-animevideov3 -s 2 -f jpg
  3. ffmpeg -i out_frames/frame%08d.jpg -i in.mp4 -map 0:v:0 -map 1:a:0 -c:a copy -c:v libx264 -r <fps> -pix_fmt yuv420p out.mp4
Modèles fournis : realesrgan-x4plus, realesrgan-x4plus-anime, realesr-animevideov3 (x2/x3/x4).
L'étape 3 doit reprendre -r <fps> de la source, sinon la vidéo sort à la mauvaise vitesse.

## Règle n°21  MuseTalk : jamais de chemin avec espaces

scripts/inference.py construit ses appels ffmpeg via os.system() SANS guillemets
(lignes 123 et 231). Un chemin contenant un espace est découpé en arguments :
l'extraction de frames produit du vide et `-v fatal` masque l'erreur, donc le
diagnostic est muet. TOUJOURS copier la source dans un chemin sans espace avant
de lancer. C'est ce qui casse aussi les noms de sortie, composés du basename.

## Règle n°22  MuseTalk : fps = celui de la vidéo source

fps = get_video_fps(video_path). Une source 30 fps sur 305 s de voix produit
9150 frames au lieu de 7625. Aligner la source sur 25 fps (ffmpeg -r 25) :
cohérent avec le reste du projet et ~17 % de frames en moins.

## Règle n°23  MuseTalk : le blending est le goulot, pas le UNet

Mesures RTX 3070 Ti, 256 px, batch 8, 7621 frames de sortie :
  UNet ......... 953 lots à 1,71 s/it .......... ~27 min
  blending ..... 7620 frames à 6,5 it/s ........ ~20 min  (écriture des PNG)
  encodage ..... ffmpeg libx264 CRF 18 ......... ~6,5 min
Total ~55 min. Ne pas promettre 20-40 min.

## Règle n°24  MuseTalk : VRAM ~7,7 Go à batch_size 8

Dépasse le plafond de 7 Go de la règle 1. Les temps d'itération restent stables
(pas de thrashing), donc c'est exploitable tel quel, mais pour repasser sous 7 Go
il faut baisser --batch_size. Vérifier au cas par cas avant de lancer.

## Règle n°25  overlay + -loop 1 : la vidéo dépasse toujours l'audio

eof_action vaut `repeat` par défaut : quand la vidéo du visage se termine, sa
dernière frame est répétée, et comme le fond et le logo sont en -loop 1 la sortie
continue. -shortest ne suffit pas (padding AAC). Résultat : plusieurs secondes de
vidéo muette en fin de fichier.
Correction sans réencodage : ffmpeg -i out.mp4 -t <durée_audio> -c copy out2.mp4
Toujours comparer stream=duration de la piste vidéo et de la piste audio.

## Règle n°26  scale=1080:1080 déforme toute source 16:9

1280x720 vers 1080x1080 écrase horizontalement et étire verticalement : c'est
visible à l'œil. Toujours RECADRER en carré AVANT le scale :
  crop=720:720:288:0,scale=1080:1080
Pour trouver le bon crop, détecter le visage (insightface buffalo_l, déjà présent
dans LatentSync/checkpoints/auxiliary) sur plusieurs frames et centrer le carré
dessus. Vérifier le cadrage sur une frame rendue avant de lancer l'encodage complet.

## Règle n°27  Voix XTTS : découper le texte, ne pas ajouter de silence

Découper le script complet en morceaux de 100-150 caractères (29 morceaux pour
~3300 caractères donnent 305 s de voix). Chaque morceau XTTS se termine déjà par
0,5-1,0 s de silence naturel (médiane 0,60 s) : ne PAS rajouter de padding, la
concaténation `-c copy` est sans perte.
temperature=0.75, speed=1.0 (règle 13). Viser une DURÉE cible, pas un nombre de morceaux :
le nombre dépend du texte (une estimation à 70 morceaux pour 5 min est fausse).

## Règle n°28  MuseTalk : la perte de netteté est localisée au BAS du visage

Mesurer avant de traiter. Ratio de variance du Laplacien MuseTalk/source, par
bande du visage : front x0,80, yeux x0,70, joues x0,40, bouche x0,16, menton x0,04.
C'est la génération à 256 px + le blending qui efface la micro-texture, surtout
sous le nez. Ne pas conclure "tout le visage est flou" sans ce profil par bandes.

## Règle n°29  Unsharp : 1.2 oui, 1.5 halote, 2.0 inutilisable

Sur un visage recadré puis upscalé en 1080 : sans traitement la netteté tombe à
25 % de la source ; unsharp=5:5:1.2 remonte à 111 % (parité avec la source) sans
halo. À 1.5 des halos apparaissent, à 2.0 c'est granuleux. Toujours mesurer ET
regarder une frame avant de figer le réglage.

## Règle n°30  scale : ajouter flags=lanczos

Le scaler par défaut (bicubic) est plus mou. flags=lanczos donne un upscale plus
net pour un coût nul (mesuré +7 % de variance du Laplacien).

## Règle n°31  GFPGAN restaure vraiment, mais cher et scintillant

GFPGANv1.4 (poids 0.6) restaure les lèvres et les poils que l'unsharp ne fait que
contraster — vérifié visuellement. Mais 2,20 img/s, soit 58 min pour 7620 frames,
et l'écart entre frames consécutives monte de x1,26 (léger fourmillement), car
chaque frame est traitée indépendamment. À réserver aux cas où la restauration de
détail est indispensable. Venv utilisable : data/video_youtube/sadtalker/venv.
Attention : GFPGAN sort en 2x, donc redimensionner à la taille d'origine AVANT
d'appliquer des coordonnées de crop.

## Règle n°32  Vérifier un cadrage par les pixels, jamais à l'œil

Un modèle de vision ne voit pas une bande de fond flou de 50 px (4,6 % de la
hauteur). Mesurer : gradient vertical moyen par ligne pour localiser la couture
(elle ressort à 20+ contre 4 de bruit local), et variance du Laplacien sur les
5 dernières lignes (0,56 = fond flou, 3,34 = visage).

## Règle n°33  CRF 16 + unsharp : prévoir le double de débit

CRF 18 sur contenu statique donnait 2904 kbps ; CRF 16 + unsharp + lanczos donne
6024 kbps pour le même contenu (218,9 Mio au lieu de 106,5). Le sharpening ajoute
du haut débit à encoder. Vérifier l'espace disque et le temps d'encodage avant.

## Règle n°34  MuseTalk : la bouche est à 4 % de la netteté de la source

Mesure de référence (variance du Laplacien, bouche, même cadrage que la source) :
MuseTalk brut 3,5 contre 94,1 pour la source. C'est structurel : MuseTalk génère la
région bouche à 256×256. L'information n'existe pas dans la sortie. Aucun
post-traitement ne peut la restituer fidèlement — ne pas promettre l'égalité.

## Règle n°35  Restauration de visage : plafond mesuré

Sur la même mesure, par ordre de coût :
  GFPGAN v1.4 seul (w=0.6) ............... 7 %   (30 min, 7620 frames)
  GFPGAN + Real-ESRGAN (recette portrait) . 9 %
  Real-ESRGAN x4 seul .................... 13 %  (2 h 07)
  Real-ESRGAN x4 + unsharp 0.6 ........... 37 %  (2 h 07)
Aucun ne dépasse 37 % proprement. Les modèles génératifs restaurent la FORM
de la bouche mais produisent un rendu lisse, pauvre en hautes fréquences.

## Règle n°36  Transfert de hautes fréquences : la seule voie vers du détail réel

MuseTalk réinjecte la bouche générée dans la frame source, donc les deux images
sont alignées au pixel. On peut donc additionner à la sortie les hautes fréquences
RÉELLES de la frame source correspondante :

  hp = src_crop - gaussian(src_crop, 1.2)
  out = clip(mt_crop + 1.0 * hp * masque_visage)

Résultat mesuré : 4 % -> 71 % de la netteté source, en 4 min (30 img/s), sans GPU.
C'est la seule méthode qui ajoute du détail AUTHENTIQUE et non halluciné.

## Règle n°37  Transfert de HP : masquer les lèvres, sinon fantôme

La bouche générée ne coïncide pas avec celle de la source : sans masque, les
contours des lèvres d'origine se superposent aux nouveaux et on voit un double
contour / fantôme, surtout quand la bouche passe de fermée à ouverte.
Masque obligatoire : ellipse des lèvres dans la frame 720p (~cx 648, cy 545,
rx 72, ry 46) reportée dans le crop, avec un facteur `keep` à l'intérieur :
  masque = w_visage * (keep + (1-keep) * w_exterieur_levres)
keep = 0.35 est le bon compromis (lèvres 0.00 : 61 %, 0.35 : 67 %, 0.60 : 72 %,
mais le risque de fantôme monte avec keep).
NE PAS remplacer ce masque par un seuillage sur |src - mt| : MuseTalk régénère
toute la mâchoire, donc la différence est forte partout et le transfert s'effondre
de nouveau à 4-16 %.

## Règle n°38  Le Laplacien seul peut mentir

Des contours fantômes ajoutent de l'énergie haute fréquence et gonflent la mesure :
une version mesurée à 90 % de la source était en fait couverte de doubles contours
de lèvres. Toujours confirmer une mesure de netteté par une inspection visuelle
sur une frame à bouche OUVERTE, pas seulement bouche fermée.

## Règle n°39  Le levier n°1 sur la netteté perçue : la taille du carré visage

Bien plus efficace que n'importe quelle restauration, et gratuit. Mesures de
netteté de la bouche dans l'image finale 1920x1080, même cadrage source :

  carré 1080 (upscale 1,80x de la source 720p) ..  36
  carré  864 (upscale 1,44x) ...................  80
  carré  720 (upscale 1,20x) ................... 150
  carré  600 (upscale 1,00x, natif) ............ 288

Le RATIO contre la source ne bouge presque pas (62 % -> 69 %) : ce qui change,
c'est la netteté ABSOLUE, multipliée par 8 entre 1080 et 600. Un carré de 1080
sur une source 720p impose un agrandissement x1,8 qui amplifie tout le flou.
Vérifié sur les fichiers encodés : carré 1080 -> 41,5 ; carré 720 -> 149,0 (x3,6).

À retenir : avant de lancer GFPGAN ou Real-ESRGAN (7 % à 37 % pour 30 min à 2 h),
commencer par réduire la taille du carré visage. Le budget de pixels est alors
dépensé à agrandir une image déjà dégradée.

## Règle n°40  LatentSync conserve ~3,8x plus de netteté que MuseTalk

Sur la zone bouche, à la résolution native 720p : LatentSync 13,2 contre MuseTalk 3,5.
Mais la CONSERVATION relative dépend de la source : 58 % sur une source peu piquée,
seulement 11 % sur une source 4K downscalée (plus la source est riche, plus le
generateur a de detail à perdre). Ne jamais conclure d'un ratio calculé sur une
autre source.

## Règle n°41  LatentSync est inutilisable tel quel sur une longue vidéo en 8 Go

Cause exacte, lipsync_pipeline.py lignes 458-460 :
    synced_video_frames.append(decoded_latents)   # accumule TOUT sur le GPU
    torch.cat(synced_video_frames)                # en fait une seconde copie
~12 Go pour 7621 frames. Le process grimpe à 24,8 Go de RAM et la cadence
s'effondre : 3,8 -> 6,1 -> 8,2 -> 14 -> 41 s/it, ETA passant de 30 min à 2 h.
scripts/inference.py n'expose AUCUN paramètre de batch.
Parade : découper l'audio en segments de ~61 s (run_latentsync_segments.py).
Chaque run n'accumule alors que ~1500 frames. Mesuré : RAM 6,5 Go, cadence
stable ~4 s/it, 8 min par segment de 61 s.

## Règle n°42  Découper LatentSync ne crée pas de joint visible

Le bouclage ping-pong de la source repart de zéro à chaque segment, mais le saut
mesuré à la frontière (2,30-2,92) est égal au mouvement normal entre deux frames
(2,40-2,59), soit un ratio x0,9 à x1,2. Invisible si la source est quasi statique.
CORRECTION (15/09/2026, volet 4) : sur une source qui BOUGE, le decoupage par defaut cree
bien un saut visible a chaque frontiere : la phase du ping-pong repart de zero a chaque
appel d'inference, donc la pose de la seconde partie ne suit pas celle de la fin de la
precedente. Mesure : ecart entre frames voisines de 6,5 contre 0,71 de mediane (x9) aux
5 raccords, vus comme des sauts d'image. Correction : des segments dont la duree est un
multiple du cycle ping-pong (16 s) — voir regle 58. Le constat ci-dessus ne vaut donc que
pour une source quasi statique.
Toujours vérifier par les pixels : comparer le saut à la frontière avec le
déplacement normal, jamais à l'œil.

## Règle n°43  La variance du Laplacien n'est PAS comparable entre deux sources

Elle additionne détail ET bruit. Mesuré sur ce dossier : les bouches de deux
sources différentes différaient de x4,64 en énergie fine et encore de x4,30 après
un flou sigma 1,0 (les deux conservaient ~12-13 % de leur énergie). L'écart n'était
donc pas du bruit, mais il rend tout chiffre absolu trompeur d'une source à l'autre.
Pour comparer deux versions issues de sources différentes, mesurer chaque version
contre SA propre source. Le transfert HP importe la texture de la source — donc
aussi ses défauts : une source plus riche donne une bouche plus riche.

## Règle n°44  Un modèle de vision ne tranche pas une netteté fine

Sur ce dossier il a inversé un ordre de netteté, décrit une bouche comme des
« lèvres », et affirmé qu'une source réencodée deux fois ne l'était pas. Il reste
utile pour repérer une structure (double contour, halo, cadrage vide) mais pas pour
arbitrer une comparaison fine. Mesurer d'abord, faire confirmer par l'œil ensuite,
jamais l'inverse.

## Règle n°45  Agrandir le visage fait chuter la netteté mesurée au carré de l'agrandissement

Mesuré sur le volet 4 (même sortie LatentSync 720p, deux habillages) :
  carré 720 (upscale 1,20x de la source) ........ bouche 83,0 dans le canevas 1080p
  plein cadre 16:9 (upscale 1,50x) .............. bouche 52,9
83,0 / 1,56 (= (1,50/1,20)²) = 53,2 : l'écart est ENTIÈREMENT dû à la magnification.
Le contenu généré est identique. Donc : quand le client demande un visage plein
cadre, prévenir que la netteté absolue baissera d'autant — et comparer les versions
à taille d'affichage ÉGALE (mesurer le plafond de la source à la même taille de
visage), sinon la comparaison est fausse dans un sens comme dans l'autre.
À taille égale (visage 466 px), le rendu conserve ~70 % de la netteté de la source 4K.

## Règle n°46  Le transfert HP doit suivre la phase de CHAQUE segment LatentSync

loop_video() repart de zéro au début de chaque appel d'inference : avec un run
segmenté, la phase du ping-pong se réinitialise à chaque segment (61 s = 1525 frames
à 25 fps). Un mapping continu décale la source de plus en plus à partir du 2e
segment, et le transfert HP importe alors la texture d'une AUTRE frame (fantôme
possible dès que la source bouge). Formule : src_idx = pingpong(i % seg_frames).
Vérifier l'alignement par les pixels avant le run complet : écart moyen minimal à
décalage (0,0) — mesuré 3,0 sur ce dossier, contre ~0 pour deux frames identiques.

## Règle n°47  Pipe rawvideo + « -loop 1 » sur le logo : « -shortest » laisse une queue muette

Avec une entrée rawvideo (frames poussées dans stdin) + un logo en `-loop 1`,
`-shortest` n'arrête PAS la vidéo à la fin de l'audio : mesuré 326,88 s de vidéo
pour 324,69 s d'audio (2,2 s de dernière frame répétée, silencieuse).
Correction sans réencodage : `ffmpeg -i out.mp4 -t <durée_audio> -c copy out2.mp4`,
puis revérifier stream=duration des deux pistes.

## Règle n°48  Boucle propre d'une source qui bouge : fenêtre + fondu CALCULÉ VERS la première frame

Une source réelle (ici 4K 50 fps, 13,9 s, personne qui parle) ne boucle pas :
coupe brute = saut dernière->première de x13,2 le mouvement normal, répété à chaque
cycle. Marche à suivre mesurée :
  1. Décimer à 25 fps (source 50 fps -> chaque 2e frame : mapping exact, zéro interpolation).
  2. Balayer TOUTES les fenêtres (début, fin) et retenir celle qui minimise l'écart de
     pose à la couture, mesuré sur le HAUT du visage (le bas est régénéré par LatentSync).
     Ici : 4 s -> 7,1 ; 8 s -> 13,5 ; 13 s -> 37,3 (les fenêtres longues bouchent mal,
     la personne bouge). Compromis retenu : 8 s (41 répétitions au lieu de 81).
  3. Fondre les K dernières frames VERS la première : poids a = (j+1)/(K+0,5) croissant,
     frame = (1-a)*frame_fin + a*frame_0. Le dénominateur K+0,5 (et non K) évite un
     doublon exact de la frame 0 au raccord.
     PIÈGE : a = (j+1)/(K+1) avec le fondu appliqué à l'envers (poids décroissant vers
     la fin) ne corrige RIEN — la dernière frame reste à 92 % de la pose d'origine et
     la couture reste à x5. La dernière frame DOIT rejoindre la frame 0.
     Résultat : couture x1,29 du mouvement normal = dans la gamme du mouvement naturel.
    ATTENTION (15/09/2026) : cette etape de fondu ne s'applique PLUS a une source destinee au
    ping-pong de LatentSync — voir regle 52. LatentSync inverse une boucle sur deux, donc la
    suite est continue sans fondu ; le fondu, lui, melange deux poses et fabrique un flou de
    liaison a chaque cycle (12 frames toutes les 8 s, soit ~80 fois sur 5 min, mesure :
    bandes laterales sous 75 % de la mediane). Le SCAN DE FENETRE (etapes 1-2) reste la
    bonne methode ; l'etape de fondu est remplacee par « aucun fondu ».
  4. Le fondu étale le changement de pose sur 12 frames (0,48 s) : la vitesse apparente
     devient INFÉRIEURE au mouvement naturel, donc invisible.
  5. Écrire la source 720p ET la source 4K depuis les MÊMES frames (deux pipes rawvideo
     alimentés par la même boucle Python) : le transfert HP reste aligné au pixel
     (vérifié : écart minimal au décalage (0,0)).
     PIÈGE : ne PAS pré-redimensionner en Python pour un encodeur et pas pour l'autre —
     un pipe déclaré en 3840x2160 qui reçoit du 1280x720 produit « Error submitting
     packet to decoder » et un fichier de 22 frames au lieu de 200. Redimensionner
     côté ffmpeg (-vf scale=...:flags=area).

## Règle n°49  Le modèle de vision hallucine des défauts de cadrage : mesurer les bandes

Sur ce dossier il a affirmé « fond flou et bandes noires sur les côtés » sur une image
sans aucun de ces défauts. Mesure des 5 pixels de bord  : bande gauche moyenne 127 /
Laplacien 5,7, bande droite 44 / 6,1 — une bande noire donnerait ~0 et ~0.
Toujours trancher par les pixels avant de rapporter un défaut de cadrage.

## Règle n°50  Une source 4K native bat une image restaurée (mesuré, même pipeline)

Même voix, même LatentSync, même transfert HP, même unsharp : en passant d'une source
« portrait restauré 4K » à de la vraie vidéo 4K 50 fps (P1002837), la bouche mesurée à
l'échelle d'affichage 1080p passe de 46,1 à 167,7 (x3,64) — et ce malgré un visage
displayé plus grand (26,2 % vs 24,3 % de la largeur, ce qui joue contre, règle 45).
Débits : 9,4 Mbps pour la nouvelle (moins de bruit temporel à encoder) contre 30 Mbps
pour l'ancienne, à CRF 16 et contenu de même durée.
L'unsharp 5:5:0,8 (identique dans les deux) gonfle le Laplacien de x2,67 : mesurer
toujours le rendu AVEC et SANS unsharp quand on veut parler de détail réel.
Sans unsharp, la nouvelle version porte 42 % de l'énergie haute fréquence de sa source
4K en 1080p (l'ancienne : ~11 %). Conséquence pratique : privilégier une vraie prise
de vue 4K plutôt que d'upscaler/restaurer une image fixe.

## Règle n°51  Pipe rawvideo + « -t » : BrokenPipeError côté Python est normal

Quand la vidéo source est plus longue que l'audio (quelques frames), ffmpeg s'arrête
à `-t <duree>` et ferme le pipe : la boucle Python qui pousse les frames lève
`BrokenPipeError: [Errno 32]`. Le fichier de sortie est complet et valide (vérifié :
8117 frames, video 324,680 s / audio 324,672 s). Encadrer `stdin.write` par un
try/except pour que l'erreur n'interrompe pas le script avant ses messages de fin.

## Règle n°52  Jamais de fondu enchaîné sur une source destinée au ping-pong de LatentSync

LatentSync boucle la vidéo en ping-pong (`loop_video` : les boucles impaires sont
inversées), donc la séquence reste continue même si la dernière frame de la source diffère
de la première. Un fondu enchaîné des K dernières frames vers la frame 0 (dans le prep)
fabrique donc un mélange de deux poses — perçu comme un « flou de liaison » sur les côtés —
qui revient à CHAQUE cycle : 12 frames toutes les 8 s, soit ~80 fois sur 5 minutes.
Vérification : Laplacien par frame sur les bandes latérales de la source ; les frames en
fondu tombent sous 75 % de la médiane (mesuré : frames 190-194 sur 200). Retirer le fondu
(option `--no-fade` dans prep_p1002837.py) : le coût réel est une frame dupliquée à chaque
inversion du ping-pong, invisible à l'œil.

## Règle n°53  Transférer le passe-haut 4K sur TOUTE l'image, pas seulement le visage

Masquer le transfert HP à l'ellipse du visage laisse les côtés sur l'upscale 720p : mesuré
38 % de l'énergie haute fréquence de la source en bande latérale (Laplacien 6,4 pour la
version livrée contre 17,0 pour la source). Avec un poids plein cadre (1,0 partout, `keep`
appliqué seulement dans l'ellipse des lèvres) : 21,3 contre 17,0 (1,2x, l'excédent vient du
détail propre de l'upscale), fond lisse à 1,14-1,29x la source, pas de bruit ajouté.
Contrôle : ne pas se fier au modèle de vision sur « bruit/halo » (il répond oui à tout) —
mesurer le Laplacien d'une zone plate (mur, fond) et le comparer à la source.

## Règle n°54  Diction XTTS : valider chaque terme technique par aller-retour Whisper

XTTS-v2 français déforme les termes techniques et le choix de graphie change tout. Méthode
qui marche : générer une phrase courte par variante de graphie (temperature 0,75 et speed 1,0 —
le reglage de livraison, jamais un autre),
transcrire avec faster-whisper (small suffit), garder la graphie qui ressort correctement.
Mesures volet 4 (P1002837) :

| terme | graphie retenue | transcrit | graphie rejetée |
|-------|-----------------|-----------|------------------|
| WP-CLI | double-vé-pé cé-èle-i | « WP-CLI » | WP-C-L-I -> « WBCL-I » |
| nginx | n-jin-x | « Nginx », « EngineX » | ène-jine-ixe -> « NGNIS » |
| MySQL | Maï-Ess-Cu-Elle | « MySQL » | — |
| rsync | Ar-sink | « Arsync » | Ère-sinque -> « R5 » |
| Docker | Dockeur | « Docker » | — |
| WooCommerce | WooCommerce | « ou-commerce » | Wou-Commerce -> « ou commerce » |
| Hermes | Hermesse | « Hermès » | — |

Tournures que XTTS enchaîne mal (à réécrire, pas à corriger) : « je vous montre comment monter
un environnement » sortait en « comment on t'envie mon environnement » ; « le guide » en
« le deal » ; « des modèles réutilisables » en « des mails réutilisables » ; « WordPress
Deployment » en « WordPress the program » ; « Troisième » seul en « GameSkill ». Préférer
« Le troisième : … », « le déploiement WordPress », « la documentation », « des configurations
réutilisables ». Ne pas réciter une commande CLI mot à mot : la renvoyer à la description.
Enfin, vérifier la transcription COMPLÈTE de l'audio final : un trou de 15 s dans Whisper
n'est pas un silence (contrôler le RMS) mais une zone inintelligible — à réécrire.

## Règle n°55  Rendu 10x plus lent : relancer le processus, pas la machine

Symptôme : le même script passe de 3,3 s/par lot de 16 frames à 43-48 s/it, en s'aggravant
(13x). À vérifier dans cet ordre avant de relancer : aucun `PYTORCH_CUDA_ALLOC_CONF`
(règle n°10), clocks au maximum (SM ~1965 MHz, mémoire ~9251 MHz), PCIe 3.0 x16, VRAM du
processus < 6 Go, et surtout un matmul fp16 de contrôle : `torch.randn(4096,4096,fp16) @`
répété -> **41,6 TFLOPS GPU libre** contre 12,8 pendant le calcul lent. Per-process GPU
memory et engine usage via les compteurs Windows :
`Get-Counter '\GPU Process Memory(*)\Local Usage'` et `'\GPU Engine(*)\Utilization Percentage'`
(ont montré 87 % du moteur 3D pour notre process, 0,5 Go pour dwm, rien d'autre).
Conclusion mesurée : la carte était saine, c'est l'ÉTAT DU PROCESSUS qui était dégradé —
le tuer et relancer le même script à l'identique redonne 6,3 s/it immédiatement. Toujours
faire du run script segment-par-segment avec reprise (les segments déjà écrits sont sautés),
c'est ce qui rend ce redémarrage gratuit : n'ont été perdus que les 63/80 lots du segment
en cours.

## Règle n°56  Mesurer l'accentuation en amplitude, pas en variance

Le Laplacien est une variance : un rapport de 3,2x en variance = 1,8x en amplitude. Pour
parler de netteté, mesurer le passe-haut (même sigma) et sortir trois nombres :
  - écart-type du rendu / écart-type de la source = amplification réelle de l'amplitude
  - corrélation normalisée entre les deux passe-haut = fidélité de structure (0,7-0,8 =
vrai détail amplifié ; proche de 0 = bruit ou halos fabriqués)
  - écart-type d'un bloc de 128x128 le plus plat de la source (fond, mur) vs le même bloc
rendu = bruit ajouté (mesuré : 0,09 -> 0,02, donc rien)
Repère obtenu sur le volet 4 (HP pleine image + unsharp 5:5:0,8) : 1,74x d'amplitude sur les
côtés avec 0,7-0,8 de corrélation, densité de contours des lèvres à 1,1-1,3x la source =
accentuation forte mais fidèle, sans fantôme. Un rapport d'amplitude au-delà de ~2x est un
signe de sur-accentuation à corriger (baisser LAMBDA ou l'unsharp, pas les deux à la fois).

## Règle n°57  Bord des lèvres mou : recaler la source, ne pas l'accentuer

Symptôme : la bouche n'est pas floue mais le bord des lèvres est « mal défini / collé ».
Cause mesurée : la bouche régénérée par LatentSync et celle de la source sont décalées de
1 à 3 px ; en transférant le passe-haut de la source à sa position nominale, les deux
contours s'annulent partiellement (gradient du bord mesuré à 0,91x la source).
Toutes les accentuations locales ont été testées et ÉCARTÉES : unsharp local gain 0,8 /
1,5 ou « contour seulement » porte le gradient à 1,36-1,65x mais double la densité de
contours (2,3-2,9x la source) = texture gravée, halos.
Solution retenue : rechercher frame par frame le décalage (dx,dy) dans +/-3 px qui superpose
au mieux les CONTOURS de la source sur ceux du rendu (SSD sur les modules de gradient
floutés, dans la zone des lèvres), puis transférer le passe-haut de la source RECALÉE.
Mesures (même frame) : gradient du bord 0,91x -> 1,10x la source, densité de contours
1,17x -> 1,34x seulement (pas de fantôme), décalage moyen trouvé dx -0,32 px dy +1,49 px
sur 7203 frames — la composante verticale domine, cohérente avec un menton/mâchoire qui
bouge plus que la lèvre haute. Coût : ~10 % de vitesse en plus (25 candidats + 2 flous
sur un patch de 216x158), sans effet sur les côtés.
Piège de mise en œuvre : chercher l'alignement sur le rendu AVANT transfert du passe-haut
(sur la bouche de LatentSync seule). Si on le cherche sur l'image déjà additionnée, le
gradient de la source déjà présent biaise la recherche vers (0,0) et la correction ne fait
rien (mesuré : sortie identique au bit près à la variante sans recadrage).

## Règle n°58  Segmenter LatentSync sur un multiple du cycle ping-pong, sinon la pose saute

Mesuré : avec des segments de 51 s (1275 frames), écart moyen entre frames voisines (MAD
sur 320x180 gris) à 6,5 aux 5 raccords contre 0,71 de médiane, soit x9 — des sauts d'image
visibles. Cause : `loop_video` remet la phase à zéro à CHAQUE appel d'inférence, donc la
suite repart sur la frame 0 de la source au lieu de continuer. Un cycle ping-pong =
2 x 200 frames = 400 frames = 16 s. Avec 48 s (1200 frames = 3 cycles), les raccords
tombent à 0,96-1,22 (médiane 0,71) : plus aucun pic > 4x la médiane. Détection à utiliser :
MAD entre frames voisines sur toute la vidéo + relevé des pics > 4x la médiane et de leur
temps, en regardant les MAD pile aux bornes des segments.
Découper aussi l'audio en échantillons exacts (WAV pcm_s16le) : un `-c copy` sur de l'AAC
coupe sur des trames de 1024 échantillons et décale le raccord de ~21 ms.

## Règle n°59  Voix XTTS : couper le silence de fin de segment avant concaténation

Chaque segment XTTS finit par 560-630 ms de silence : sur 37 joints, 21,3 s de blanc
artificiel, dont plusieurs pauses en pleine phrase (le découpage tombe parfois sur une
virgule) — le rendu s'entend comme « la voix saute ». Couper à 120 ms de fin et 40 ms de
tête (seuil 3 % du RMS du segment) fait passer 287,9 s à 271,2 s et supprime les pauses
parasites (silences > 400 ms : 86 -> 49, total 50,8 -> 29,7 s).
Vérifier au passage qu'il n'y a pas de clics : analyse échantillon à échantillon, max de
|diff| comparé au p99 (0 clic ici) — le défaut n'était pas un clic mais des pauses.

## Règle n°60  LatentSync : la version se lit dans le cache HuggingFace, pas dans le code

`docs/changelog_v1.6.md` (ligne 5) : « *we did not make any changes to the model structure or
training strategy […] the current code is compatible with both LatentSync 1.5 and 1.6. To switch
between versions, you only need to load the corresponding checkpoint and modify the `resolution`
parameter* ». La version vit donc dans le couple (checkpoint, resolution) : **1.5 -> 256,
1.6 -> 512**. Le README (l. 108-111) annonce **8 Go** pour la 1.5 et **18 Go** pour la 1.6.
PIEGE : `inference.sh` livre par defaut `--unet_config_path configs/unet/stage2_512.yaml`, ce qui
fait croire a une 1.6 meme avec un checkpoint 1.5. Methode qui tranche : lire le nom du depot en
cache, `ls ~/.cache/huggingface/hub/ | grep -i latentsync` (`models--ByteDance--LatentSync` =
depot principal/1.5 ; `models--ByteDance--LatentSync-1.6` = 1.6). Le checkpoint ne porte AUCUN
marqueur de version : 1 267 944 644 parametres, 4,723 Go fp32, 1246 tenseurs,
`motion_modules...pos_encoder.pe` en (1, 24, 320) — identique dans les deux configs. Ne pas perdre
de temps a l'inspecter pour trancher. Une demande « 1.5 @ 512 px » est contradictoire : le dire.

## Règle n°61  LatentSync sort a la resolution de la SOURCE, pas en 256/512

`restore_video()` (lipsync_pipeline.py l. 266-279) redimensionne le carre genere en BICUBIQUE a la
taille du visage detecte, puis le recolle dans les images d'origine ; `write_video` ecrit ces
images. Sur une source 4K la sortie est donc **3840x2160**. Consequence : demander « upscaler la
sortie 256/512 a 4K » n'a pas de sens, c'est deja fait — et Real-ESRGAN ne peut pas restituer
l'information detruite a 256 px. Ne pas fabriquer ce livrable : l'expliquer et fournir la mesure.

Deux mecanismes a connaitre avant de preparer les entrees :
  - l'audio est reechantillonne a 16 kHz tout seul (`read_audio` -> `AudioReader(sample_rate=16000,
    mono=True)`) : un WAV 24 kHz mono passe sans conversion ;
  - la video est TRONQUEE a la duree de l'audio (l. 307, `video_frames[:len(whisper_chunks)]`) :
    5,43 s d'audio sur une source de 8 s donnent 137 frames a 25 fps, pas 200.

## Règle n°62  LatentSync regenere TOUT le carre du visage, pas seulement la bouche

Variance du Laplacien en 4K, source vs sortie, meme zone et meme instant :

| instant | haut du visage | bas / bouche |
|---|---|---|
| 1,0 s | 46,9 -> 19,6 (x0,42) | 29,8 -> 4,9 (x0,16) |
| 2,5 s | 64,4 -> 24,8 (x0,39) | 40,8 -> 5,0 (x0,12) |
| 4,0 s | 60,9 -> 35,0 (x0,58) | 32,6 -> 4,7 (x0,14) |

Le haut du visage n'est PAS epargne (x0,4 a x0,6) : le modele regenere le visage entier en 256 px
et ce carre est ensuite etire a ~1072x1512 (~4-6x en bicubique). La perte la plus forte est en bas,
mais conclure « seule la bouche est floue » est faux.
Real-ESRGAN x4 sur le bas du visage fait passer la metrique de 5,0 a 10,6 : c'est un artefact de
re-echantillonnage (la variance du Laplacien n'est pas comparable entre deux echelles), pas un
detail retrouve.

## Règle n°63  LatentSync 1.5 @ 256 px sur 8 Go : references mesurees (19/09/2026)

Run complet, source 4K 25 fps, audio 5,43 s, `--inference_steps 20 --guidance_scale 1.5
--enable_deepcache`, `stage2.yaml` :
  - temps total **259 s** pour **5,48 s** de sortie, soit **47,3x le temps reel** ;
  - 9 blocs de 16 frames a **13,93 s/bloc** (2 min 05 de denoising) ;
  - **VRAM pic 7 800 / 8 192 Mio (95,2 %)** avec 3,6 Go deja pris par le bureau : marge ~390 Mio,
    aucun OOM, aucun spill. Liberer le bureau avant un run long est donc conseille ;
  - temperature GPU 70 degC max ; **aucun `nvlddmkm` ID 153, aucun `Kernel-Power` 41** ;
  - sortie 3840x2160, h264 CRF 18 + AAC 16 kHz mono (l'audio est celui de l'entree).
A annoncer : **~47 min par minute de video finale**, **~2 h 22 pour une video de 3 min**.
Pour un run long, appliquer les regles 41 et 58 (segmentation, multiple du cycle ping-pong).

## Règle n°64  MuseTalk : le chemin 4K est casse par le detecteur s3fd

Mesure sur une frame 4K (RTX 3070 Ti) :
  mmpose (DWPose) frame entiere .... 0,92 s
  s3fd 1280x720 ................... 1,13 s
  s3fd 1920x1080 .................. 1,92 s
  s3fd 3840x2160 .................. 6,57 s
`face_detection.FaceAlignment` (preprocessing.py l. 23) lance `net(imgs)` sur la frame
ENTIERE puis boucle en Python pur sur tous les anchors (detect.py, `for Iindex, hindex,
windex in poss`). En 4K : ~7,5 s/frame -> 25 min pour 200 frames, ET la boite est fausse :
(1654,1147,2252,1721) au lieu de (1372,512,2444,2024) validee par insightface (a 1280 px on
retrouve (1446,546,2385,1833)). Le vrai blocage est la VRAM : avec l'UNet 3,24 Go + VAE +
whisper deja charges (7,5 Go/8 Go), le forward s3fd en 4K reclame des activations de
plusieurs Go -> spill permanent et la 1re frame ne se termine jamais (2 nvlddmkm ID 153
enregistres pendant ces tentatives).
FIX minimal, 2 points d'appel (`get_bbox_range` l. 63 et `get_landmark_and_bbox` l. 104) :
detecter sur une copie <= 1280 px puis remettre la boite a l'echelle. Landmarks de 200
frames : ~65 s au lieu de >40 min. Reversible : `git checkout musetalk/utils/preprocessing.py`.

## Règle n°65  Ne pas conclure « bloque » sur un log fige : mesurer le cout par frame

tqdm vide bien son buffer en redirection (verifie : 447 -> 718 octets en 6 s). Un log fige ne
prouve donc pas un blocage — mais l'inverse non plus. Un run a ete tue a tort a 38 min sur
une intuition, alors qu'un bench d'une frame (0,92 s mmpose + 6,57 s s3fd) donnait 7,5 s/frame,
soit 25 min pour 200 frames : le run etait a ~85 %. Toujours chronometrer UNE frame avec le
meme code avant de conclure, et lancer MuseTalk avec `python -u` pour garder la visibilite.

## Règle n°66  MuseTalk sur 8 Go : batch_size 4, sortie a la resolution de la source

  - `--batch_size 4` : la regle 24 (7,7 Go a batch 8) ne laisse aucune place avec 2,5 Go de
    bureau. Mesure a batch 4 : pic 7 854 / 8 192 Mio (95,9 %), 66 degC, run de 300 s pour
    5,43 s de sortie (landmarks ~65 s, UNet 34 lots de 4, blending 135 frames).
  - la sortie est a la resolution de la SOURCE (3840x2160 ici), pas en 256.
  - l'audio de sortie garde le sample rate d'entree (24 kHz) ; LatentSync reechantillonne en 16 kHz.
  - le nombre de frames suit les chunks whisper (135 frames pour 5,43 s a 25 fps), donc
    legerement different de LatentSync (137) : ne pas s'etonner d'un decalage de 1 a 2 frames.

## Règle n°67  A 4K, LatentSync 1.5 et MuseTalk v1.5 sont a egalite (contredit la regle 40)

Meme source 4K, meme audio, meme cadrage, variance du Laplacien :
  haut du visage : LatentSync 29,6 / 37,8 / 50,4  vs  MuseTalk 32,3 / 36,7 / 48,4  -> egalite
  bas / bouche   : LatentSync  4,9 /  5,0 /  4,7  vs  MuseTalk  4,6 /  4,4 /  4,2  -> +5 a +12 % LatentSync
  source 4K      : haut 53,9 / 74,6 / 70,6, bas 29,8 / 40,8 / 32,6
La regle 40 (« LatentSync 3,8x plus net que MuseTalk sur la bouche ») avait ete mesuree a
**720p natif** : le carre 256 n'y est etire que ~2,8x, contre ~6x en 4K. La resolution de la
source change le classement — c'est un parametre, pas un detail.
RESERVE a enoncer systematiquement : les debits ne sont pas comparables (source 123 Mbps,
LatentSync 29,4 Mbps, MuseTalk 8,9 Mbps). Une part de l'ecart mesure est de la compression,
pas du modele. Pour trancher, la planche visuelle, pas la metrique seule.

## Règle n°68  Greffe hautes frequences sur une sortie 4K : masque `face`, alpha 0,7

`sortie = clip(genere + alpha * (source - flou(source)) * masque, 0, 255)`. La regle 53
decrit un transfert PLEIN CADRE : c'etait juste pour le volet 4, dont TOUTE l'image venait
d'un upscale 720p. Sur une sortie talkie, le FOND est de la vraie 4K — y ajouter du
passe-haut ne restaure rien, ca sur-accentue. **Masquer sur le visage (mask `face`) est le
choix par defaut ici**, et c'est verifiable : le bloc 128x128 le plus texture du fond
(sigma 54,6) reste a 0,72 / 0,60 / 0,67 **a tous les alpha** (contre 0,71 / 0,63 / 0,69 pour
la sortie brute), et le bloc le plus plat reste a 0,00 = aucun bruit ajoute.

Balayage alpha mesure sur LatentSync (blur 5), amplitude du passe-haut du haut du visage
(sigma(rendu)/sigma(source), 1,00 = la source) :

| instant | brut | a0,3 | a0,5 | **a0,7** | a1,0 |
|---|---|---|---|---|---|
| 1,0 s | 0,78 | 0,84 | 0,89 | 0,95 | 1,06 |
| 2,5 s | 0,76 | 0,81 | 0,87 | 0,92 | 1,04 |
| 4,0 s | 0,88 | 0,95 | 1,00 | 1,07 | 1,19 |
| moyenne | 0,81 | 0,87 | 0,92 | **0,98** | 1,10 |

**alpha = 0,7** est le bon compromis : c'est le seul qui ramene l'amplitude sur celle de la
source sans la depasser (0,98 de moyenne). A 1,0 on est au-dessus (1,10-1,19) et la
correlation des levres double (0,19 -> 0,34), donc plus de texture posee au mauvais endroit.
Gain reel a 0,7 : haut du visage x1,2 en amplitude, bouche x2,1 en variance (4,8 -> 9,6 pour
une source a 29,8-40,8), correlation du haut du visage 0,61 -> 0,66 : du detail REEL, pas du
bruit fabrique. `blur 5` (noyau 5x5) est le bon reglage ; sigma derive du ksize.
CE QUE CA NE FAIT PAS : la correlation ne monte que de 0,60 a 0,64-0,74, donc on ajoute du
detail correle a la source mais on n'invente pas ce que le 256 px a perdu — la geometrie du
visage reste celle du modele.

## Règle n°69  MuseTalk : greffer le BAS du visage seulement, et proteger les levres

MuseTalk ne regenere que le bas du visage ; sa moitie haute est la vraie 4K, qui n'a perdu
que ce que l'encodeur a mange (amp 0,76-0,86, et son fond tombe meme a 0,46-0,50 vu son debit
de 8,9 Mbps). Y greffer du passe-haut remonte l'amplitude a 1,04 mais **sur-accentue une zone
qui n'a pas ete regeneree**. Options du script : `--haut-exclu 0.5` (avec rampe verticale
douce, pas de coupe franche) et `--lips-guard 1.6`.

| variante | amp. haut | amp. bouche | corr. levres |
|---|---|---|---|
| MuseTalk + HF, mask=face | 1,01 | 0,49 | 0,08 / 0,13 / 0,28 |
| MuseTalk + HF, bas + garde levres | 0,83 | 0,46 | **-0,00 / -0,01 / -0,00** |

La garde des levres ramene la correlation dans les levres a ZERO (les levres generees ne sont
plus touchees) et la bouche ne perd presque rien (0,46 contre 0,49) : c'est la variante a
preferer pour ne pas risquer la synchronisation labiale. Utiliser `mask=face` quand on veut
une comparaison a armes egales avec LatentSync, `bas + garde levres` quand on livre.
Localisation des levres : points **52-71** du modele 106 points d'insightface (verifie :
0-24 = contour du visage, 72-86 = nez, 87-105 = yeux). Ne pas deviner ces indices.

## Règle n°70  Verifier l'alignement source/sortie AVANT de greffer quoi que ce soit

Risque n°1 (regle 57) : si la sortie ne correspond pas a la source au meme index, la greffe
injecte la texture du mauvais instant et cree des halos. Controle a faire en premier :
chercher dans +/-3 px le decalage du FOND qui minimise l'ecart moyen avec la source, sur une
bande hors visage, pour 5 frames reparties. Mesure du 19/09 : meilleur decalage **(+0,+0)**
partout, ecart 1,35-1,52 (LatentSync) et 1,40-1,48 (MuseTalk) en niveaux de gris, soit le
codec seul. Si le meilleur decalage n'est pas (0,0), s'arreter : le probleme est en amont
(duree d'audio, boucle ping-pong de la source, frames de depart), pas dans la greffe.

## Règle n°71  Post-traitement video ffmpeg : trois pieges qui coutent un run entier

  - **`-shortest` coupe la video sur l'audio.** La sortie de LatentSync est en 137 frames
    (5,48 s) mais son audio dure 5,43 s : avec `-shortest` la video ressort en **133 frames**
    et on perd les dernieres. Utiliser `-frames:v N` (N = nombre de frames du modele) et
    copier l'audio sans `-shortest`. Toujours re-verifier `nb_frames` de la sortie.
  - **Ne pas melanger `os.chdir()` et des chemins relatifs.** Le script fait `os.chdir()`
    pour importer latentsync : tout chemin relatif fourni en argument devient invalide en
    cours de route (symptome : ffprobe passe puis `Error opening input file`). Convertir tous
    les arguments en absolu des le debut avec `os.path.abspath`.
  - **Ne jamais ecrire un cache de detections vide**, sinon le run suivant le recharge et
    croit avoir 0 visage (le log disait `detections : 0/0`). Leve une erreur si
    `ok.sum() == 0` au lieu de sauvegarder.
Pour le reste : pipe `rawvideo` + `bgr24` (jamais cv2.VideoCapture en 4K), et les
`Broken pipe` des decodeurs a la fermeture sont normaux (regle 51).

## Règle n°72  Source « vivante mais molle » : scanner le visage frame par frame AVANT de lancer

Une source avec du mouvement (tête qui bouge, regard qui descend) est le cas normal des
rushes réels, et c'est exactement ce qui casse le pipeline. **LatentSync exige un visage sur
CHAQUE frame** : une seule frame sans visage → `RuntimeError: Face not detected` après une
minute de chargement. MuseTalk tolère un trou, LatentSync non.

Procédure : détecter le visage sur TOUTE la vidéo (insightface buffalo_l, `det_size=512`,
frame pleine résolution = exactement ce que fait LatentSync), écrire un JSON par frame
(ok, det_score, centre, taille), puis ne garder que les fenêtres de N frames **sans aucun
trou** et les classer par score de détection, distance du centre du visage au centre image, et
stabilité (écart-type du centre). Mesuré sur un rush de 511 frames : 13 frames sans visage
(2,5 %), toutes concentrées dans la zone « tête baissée » — et la fenêtre suggérée à l'œil
tombait pile dedans. La meilleure fenêtre (celle qui a 2,3x moins de mouvement et un visage
plus gros) n'était PAS celle qu'on aurait choisie à vue de nez.

Coût du scan : ~22 s pour 511 frames 4K. À faire systématiquement : c'est moins cher que
n'importe quel run raté.

## Règle n°73  Préparer un segment : vérifier les KEYFRAMES avant de choisir la coupe

`ffmpeg -ss <t> -c copy` découpe sur la keyframe précédente, pas sur l'image demandée : le
résultat dépend donc entièrement de la structure GOP du rush. Contrôle préalable obligatoire :

```
ffprobe -v error -select_streams v:0 -show_frames -show_entries frame=pts_time,key_frame -of csv=p=0 FICHIER
```

**Cas 1 — GOP régulier (mesuré : 30 frames, une keyframe toutes les 1,2 s).** Les frames
0/30/60/90/… sont copiables telles quelles. Il faut donc **choisir une fenêtre qui démarre sur
une keyframe** : la coupe est alors sans **aucun** réencodage, ce qui est gratuit en qualité.
Le vérifier par md5 plutôt que le supposer — extraire la frame 0 du segment et la frame N de la
source, et comparer les deux images :

```
ffmpeg -y -v error -i source_v3.mp4 -vf "select=eq(n\,0)" -vsync 0 -frames:v 1 a.png
ffmpeg -y -v error -i rush.mp4     -vf "select=eq(n\,60)" -vsync 0 -frames:v 1 b.png
md5sum a.png b.png     # identiques = coupe a l'image pres, zero perte
```

Choisir un début « propre » qui n'est pas une keyframe coûte forcément un réencodage : sur un
rush de 4K à 84-88 Mb/s, `crf 14` coûte 0,5-0,75 niveau de gris d'écart moyen (mesuré). C'est
acceptable mais évitable, donc chercher la keyframe d'abord et ne réencoder qu'en dernier
recours.

**Cas 2 — keyframe unique (à t=0)**, rencontré sur deux autres rushes : `-c copy` démarre alors
bien avant l'instant demandé et le fichier sort avec le mauvais nombre de frames (156 au lieu de
136 dans le cas mesuré). Réencoder en `-ss` **avant** `-i`, avec `-frames:v N` :

```
ffmpeg -ss 8.0 -i source.mp4 -frames:v 136 -t 5.44 -c:v libx264 -crf 14 -preset slow -pix_fmt yuv420p source_v2.mp4
```

**Dans les deux cas**, vérifier ensuite que la coupe est exacte : détecter le visage sur le
segment et comparer centre/hauteur moyens à ceux de la source complète sur la même plage. Ne
jamais supposer la précision d'un `-ss`.

**PIEGE ffprobe, mesure le 20/09/2026 : `-show_entries frame=pts_time,key_frame` renvoie en
realite `key_frame,pts_time`** (`1,0.000000` puis `0,0.040000`). Un comptage fait sur la
derniere colonne annonce donc **0 keyframe** sur un GOP regulier — de quoi reencoder pour rien
ou croire a une keyframe unique. Parser les deux champs par leur FORME (l'entier 0/1 d'un cote,
le flottant de l'autre), jamais par leur position ; c'est ce que fait `keyframes()` du pipeline.
Controle de coherence qui tranche en une seconde : sur `talkinghead.mp4` (4K, 25 fps, 227
frames) le GOP est de **30 frames** (keyframes 0, 30, 60, ... 210), donc les fenetres 0 et 60
sont copiables telles quelles et la 58 ne l'est pas.

## Règle n°74  Greffe HF : alpha dépend de la NETTETÉ DE LA SOURCE (0,7 nette / 1,0 molle)

L'alpha optimal n'est pas une constante : c'est celui qui ramène l'amplitude du passe-haut
sur celle de la source sans la dépasser. Il dépend donc de la quantité de hautes fréquences
que la source contient réellement.

| | source nette (audit 191) | source molle (audit 79) |
|---|---|---|
| variance du Laplacien, haut du visage | 54,0 | **11,4** |
| passe-haut moyen de la source | — | **0,74 niveau** |
| bruit de réencodage des sorties | — | **1,4 niveau** |
| amplitude max atteignable | 1,00 dès alpha 0,7 | **0,92 à alpha 1,0** |
| alpha retenu | **0,7** | **1,0** |
| corrélation du haut du visage après greffe | 0,64-0,74 | 0,28-0,43 |
| netteté récupérée | — | 89 % (LatentSync), 83 % (MuseTalk) |

**Sur une source molle, le passe-haut transférable est du même ordre que le bruit des
encodeurs** : la corrélation reste basse (0,28-0,43 au lieu de 0,64-0,74), et aucun alpha
n'atteint l'amplitude de la source. Le critère « netteté / pas d'halo » se tranche alors sur
la netteté seule : l'écrêtage mesuré est nul à tous les alpha (0,0000 à 0,0012 % des pixels)
et l'amplitude ne dépasse jamais la source, donc rien ne justifie de doser moins. La
greffe rattrape la netteté perdue par le modèle, elle ne rattrape pas la mollesse du tournage.
Contrepartie à annoncer : la corrélation dans la bouche monte (0,05 → 0,24), du fait de la
règle 57. Toujours livrer 2-3 doses et laisser l'œil trancher.

## Règle n°75  Mesurer une modification sous le bruit du codec : le décalage DC du réencodage

Comparer deux vidéos réencodées en soustrayant les frames extraites **ne mesure pas** la
modification : x264 introduit un **décalage DC systématique** entre deux encodages du même
contenu (mesuré : **-1,55 niveau** de moyenne signée, écart-type 1,09, constant sur toute
l'image, hors zone modifiée). Un décalage constant ne crée pas de hautes fréquences, mais il
écrase complètement la mesure : la dose réelle de la greffe était de 0,23-0,76 niveau, contre
1,55 de décalage. Symptôme typique : des chiffres **identiques à tous les alpha** alors que la
dose varie de 3x. Si ça arrive, la mesure ne mesure pas ce qu'on croit.

La méthode juste : calculer la dose **analytiquement**, sans passer par les vidéos
(`out = clip(brut + alpha*HF)`), et mesurer ainsi le vrai effet et le vrai écrêtage. Mesuré
sur la zone visage : 0,227 / 0,379 / 0,531 / 0,758 niveau de dose moyenne pour alpha
0,3/0,5/0,7/1,0, correspondant à une variance du Laplacien de 7,27 / 9,01 / 11,59 / 17,00
contre 6,20 sans greffe. Autrement dit : **0,23 niveau de modification suffit à faire monter
la variance du Laplacien de 17 %**. La variance du Laplacien est très sensible aux ajouts de
hautes fréquences ; les deux mesures sont vraies et ne répondent pas à la même question —
livrer les deux.

## Règle n°76  La greffe HF ne vaut que ce que la source vaut : prévoir la corrélation avant de lancer

La corrélation mesurée après greffe (fidélité du détail transféré, règle 57) **suit la netteté de
la source**. Trois sources mesurées avec le même pipeline et le même script :

| source | netteté source (var. Laplacien, haut) | corrélation haut après greffe | corrélation bouche | amplitude atteinte |
|---|---|---|---|---|
| propre, studio | 54,0 | 0,64-0,74 | 0,22 | 1,00 dès alpha 0,7 |
| correcte, 4K téléphone | 21,2 | **0,53-0,61** | **0,45-0,52** | 1,08-1,17 à alpha 1,0 |
| molle, floue | 11,4 | 0,28-0,43 | 0,16-0,26 | 0,92 au mieux à alpha 1,0 |

Règle pratique : **au-dessus de ~20 de variance, la greffe restitue du vrai détail (corrélation
~0,6) ; sous ~12, elle ajoute surtout un passe-haut faiblement corrélé (~0,3)**, c'est-à-dire un
accentuation qui peut ressembler à du bruit. Avant de lancer, mesurer la netteté de la source
(variance du Laplacien sur le haut du visage, zone de hf_rapport.py) et annoncer la corrélation
attendue : c'est le meilleur prédicteur de la qualité finale, et il ne coûte qu'un ffprobe.

Corollaire : quand une source est molle, **le premier levier n'est pas de régler la greffe, c'est
de tourner plus net**. Ne pas promettre une restauration que la greffe ne peut pas produire.

Deux limites qui persistent même avec une bonne source : la bouche régénérée reste à ~55 % de la
netteté de la source (le modèle la lisse, la greffe ne peut pas inventer ce qu'il n'a pas
produit), et l'amplitude peut légèrement dépasser 1,0 à alpha=1,0 (mesuré 1,08-1,17) —
alpha≈0,85 la ramène pile à 1,0 si l'on veut une dose strictement neutre.
Confirmation du 20/09/2026 (source 1080p 25 fps, volet 5) : variance du haut du visage 17-18,
corrélation après greffe 0,59-0,61 (haut) et 0,41-0,51 (bouche), amplitude 1,11-1,18 à alpha 1,0 —
même classe que la ligne « correcte » du tableau, fond inchangé (plat 0,55-0,61 → 0,55-0,59).

## Règle n°77  Choisir la fenêtre par SCORE COMPOSITE NORMALISÉ, jamais par un critère dominant

Sur un rush réel, les critères de sélection n'ont pas la même dynamique. Mesuré sur un clip de
227 frames : la stabilité du visage ne variait que de 45 à 58 px et le centrage de 107 à 143 px,
alors que la netteté variait **du simple au double** (9,2 à 21,4) selon la seconde.

Conséquence : classer les fenêtres par « centrage + 2×stabilité » (critère suffisant sur une
autre source) plaçait en tête les frames 0-9, c'est-à-dire **la partie la plus molle du clip**.
La fenêtre retenue in fine (frame 60) était à 0,727 de composite contre 0,700 pour celle que ce
critère désignait — et elle était **la plus nette du clip**.

Méthode : normaliser chaque critère en 0-1 sur l'ensemble des candidats, puis combiner
netteté 0,40 / stabilité 0,25 / centrage 0,20 / mouvement inter-frame 0,15, avec un bonus de
0,10 pour une fenêtre qui démarre sur une keyframe (règle 73). Afficher le classement complet,
ne retenir que ce qui est sans trou de visage, et **relire les 8 fenêtres les plus nettes** avant
de trancher : si elles sont groupées dans une même seconde, c'est là qu'est la bonne matière.

## Règle n°78  Stabiliser le mouvement vertical : SUIVRE le visage, pas retirer les basses fréquences

Modèle qui marche (mesuré, écart-type vertical du centre du visage 28,86 → 11,19 px, soit −61,2 %) :

```
s(t) = k * lissage(y(t) - moyenne)      y_sortie(t) = y(t) - s(t)
```

Erreur à ne pas refaire : `s = k * (y - lissage(y))` (retirer les basses fréquences au lieu de
suivre le visage). Deux symptômes mesurés, tous les deux rédhibitoires : le cadrage suit le bruit
du détecteur à **15-38 px/frame** (le fond flotte) et le décalage saute de **42 à 90 px** à chaque
jonction de boucle — 55 faux raccords sur 5 minutes.

Points de méthode, tous vérifiés par balayage :

- **Signal pilote : la moyenne des 4 repères yeux+bouche**, pas la bbox. La bbox est plus bruitée
  (elle bouge avec la pose) et son bruit se retrouve injecté dans le cadrage.
- **Filtre : Savitzky-Golay (7, 2) plutôt qu'un gaussien.** Un gaussien écrase les vrais
  mouvements rapides, donc le décalage sous-estime le mouvement et la réduction plafonne (55,8 % à
  sigma 2 contre 65,0 % sans filtre). Mesurer la vitesse du cadrage plutôt que la supposer.
- **k = 0,65** avec un recadrage 3456x1944 → 3840x2160 : le zoom de recadrage (1,111) amplifie le
  mouvement résiduel d'autant, donc viser la cible APRÈS zoom ((1-k) × zoom = 0,39 → −61 %).
- **Coût du recadrage** : 11 % de champ et un agrandissement Lanczos de 11 % → netteté inchangée
  sur le haut du visage (×1,002) mais −9 % sur la zone bouche. À annoncer, pas à cacher.
- **Vitesse du cadrage** : viser ~2 px/frame en médiane. Un pic à 20 px/frame est acceptable s'il
  tombe pendant un vrai déplacement de la tête (mesuré : jusqu'à 38 px/frame, frames 39-51) : le
  cadrage est alors synchrone avec le sujet, comme un cadreur qui suit.

**Les repères pris séparément baissent moins que le centre (44 % contre 61 %) — c'est normal, pas
un échec.** Un recadrage retire exactement le mouvement COMMUN (la translation). Ce qui reste sur
les yeux et la bouche est l'animation du visage, qu'il faut conserver. Preuve à produire : la
corrélation yeux/bouche tombe de **+0,78 à −0,15**, la composante rigide a disparu.

**Ne jamais comparer un écart-type mesuré à deux résolutions.** La même vidéo donne 11,19 px en 4K
et 5,62 px en 1080p : le détecteur est plus bruité en 4K. Toute comparaison avant/après ou
boucle/source doit se faire à résolution égale, sinon on croit à une amélioration qui n'existe pas.

## Règle n°79  Boucler 5 s sur 5 min : seul le CHOIX DES POINTS DE COUPE fonctionne

Métrique de référence à calculer d'abord : l'écart moyen (niveaux de gris, absolu) entre deux
frames **consécutives** de la source. Mesurée ici à **2,90**. Une jonction du même ordre est
invisible, 3× se voit, 5× se voit clairement. C'est ce chiffre qui rend les stratégies comparables
autrement qu'à l'œil.

Résultats mesurés (source stabilisée de 136 frames, cycle visé 300 s) :

| stratégie | pire jonction | × référence | verdict |
|---|---|---|---|
| segments réordonnés, ordre optimisé | 3,80 moyen / 9,89 pire | 1,3× / 3,4× | retenu |
| ping-pong | 2,97 | 0,93× | raccord parfait mais mouvement inversé |
| ralentissement 0,85 | 15,35 | 5,28× | inutile |
| boucle simple | 15,35 | 5,28× | témoin |

- **Réordonner des segments uniformes dégrade tout** : l'ordre qui minimise les écarts est l'ordre
  naturel (les jonctions internes redeviennent de vraies transitions). Ne pas croire que
  « mélanger les segments » masque la répétition — ça ajoute des coupes.
- **Ce qui paie : choisir les points de coupe là où les frames se ressemblent** (recherche locale
  sur les positions de début, avec un espacement minimal imposé pour interdire les segments quasi
  identiques : sinon l'optimiseur propose un bégaiement). Gain mesuré : 9,89 au lieu de 15,35.
- **Le prix à annoncer** : un cycle plus court répète plus souvent (3,68 s au lieu de 5,44 s).
- **Ping-pong : écarté pour un talking head.** Le raccord est pixel-parfait mais la bouche repart en
  arrière deux fois par cycle — un visage qui parle à l'envers se repère immédiatement.
- **Ralentir n'apporte rien** : la dernière frame et la première n'ont pas changé, donc la jonction
  de fin de cycle reste identique ; et la synchro labiale dérive de 15 % sans jamais se rattraper.
- **Vérifier sur le fichier RENDU, pas sur le plan** : 9,89 prévu → 9,82 mesuré, mais l'écart peut
  être plus grand selon le réencodage. Comparer la jonction à la frame qui la suit dans le fichier.
- **Cout de la recherche : precalculer la MATRICE des ecarts une fois.** Une descente locale qui
  recompare deux images entieres a chaque candidat fait ~160 000 comparaisons (mesure : plus de
  7 minutes pour 136 frames). En calculant une fois `M[i][j] = |frame_i - frame_j|` sur les
  vignettes 480x270 (n boucles vectorisees sur n frames, quelques secondes), la descente ne fait
  plus que lire la matrice. Lisser la mesure finale, elle, sur les frames pleine resolution :
  c'est ce chiffre-la qui est annonce a l'utilisateur.

## Règle n°80  LatentSync sur une longue durée : le mur est la RAM système, pas la VRAM

Mesure du 20/09/2026 sur 343,88 s de sortie 1080p (8 600 frames, source 1080p, 8 Go de VRAM) :
**14 h 17** au lieu des 4 h 30 annoncés par la règle 63, soit **149,6x le temps réel** contre 47,3x,
et **3,2x la projection**. LatentSync décode TOUTE la vidéo en mémoire : 8 600 frames de
1920x1080x3 ≈ 53 Go théoriques, **49,0 Go observés** sur le processus. Sur 64 Go de RAM il ne
restait que **2,6 Go libres** et le fichier d'échange était à **39 Go sur 82** : la machine a
paginé pendant quatorze heures, et la cadence est passée du nominal à **116-127 s/it**.

Preuve du lien de cause à effet : libérer 2 Go de RAM et 550 Mio de VRAM (fermeture d'un éditeur
vidéo pendant le run) suffit à faire passer la cadence de **127,4 à 116,0 s/it** (−8,9 %), sans
rien changer au modèle. La cadence suit l'état de la mémoire, pas la charge du modèle.

**Conséquence : la projection 47,3x mesurée sur un clip de 5,48 s NE s'extrapole PAS.** Au-delà
d'une minute de sortie, segmenter (règles 41 et 58) : c'est le seul levier qui ramène la RAM par
run à quelques gigaoctets. Avant de lancer, vérifier l'espace du fichier d'échange et fermer les
applications lourdes — la différence se compte en heures.

## Règle n°81  Notifier un run long : texte sans chevron, et lire la BONNE barre de progression

Deux bugs indépendants ont rendu un moniteur muet pendant 14 h, au point que le run a été déclaré
arrêté à tort :

  - **`parse_mode=HTML` sur un texte qui contient l'ETA de tqdm** (`01:55<00:00 restant`) : le `<`
    brut ouvre une balise et Telegram rejette TOUT le message en `HTTP Error 400: Bad Request`.
    Seul un message sans chevron passe. Envoyer sans `parse_mode` (ou échapper), et **tester le
    premier envoi** : un canal cassé ressemble exactement à un run mort.
  - **Un motif de lecture qui prend la DERNIÈRE barre tqdm vue** attrape la barre intérieure
    (« Sample frames: 16 », ~21 fois par itération) au lieu de la barre extérieure
    (« Doing inference... », une fois). Le pourcentage affiché oscille alors (55 %, 100 %) sans
    rapport avec la progression réelle. Ancrer le motif sur le **libellé de la boucle extérieure**.
  - **En run segmenté, la barre repart de 0 à chaque tranche** : lire en plus les lignes
    `=== segment i/N ===` du script de tranches, sinon le pourcentage affiché recule de 100 à 0
    huit fois de suite (le moniteur affiche « tranche : 3/8 » et un avancement global).
  - **Tuer l'ARBRE de processus à l'arrêt d'urgence.** En run segmenté, l'enfant du moniteur est
    le script de tranches et le processus d'inférence est son petit-fils : un `proc.kill()` laisse
    le GPU occupé alors que le rapport annonce l'arrêt. `taskkill /PID <pid> /T /F`.

Et un défaut de conception : un watchdog qui surveille la vivacité du moniteur reste muet si tous
les envois échouent. Le watchdog doit vérifier le **canal** (dernier envoi réussi), pas seulement
le processus. Parade retenue : un alerteur séparé qui lit le **log** (source fiable), écrit du
texte sans chevron, et ne parle qu'à +3 % de progression ou après 45 min.

**Correctif applique le 20/09/2026** (un seul moniteur, generique, dans
`LatentSync\tests\surveiller_latentsync.py` ; `v4_talking_head_v5\surveiller_latentsync_v5.py`
n'est plus qu'un lanceur qui conserve l'invocation historique) :

  - envoi **sans `parse_mode`**, apres retrait de nos propres balises — le chevron de l'ETA
    traverse intact, ce qui est desormais le controle que le canal fonctionne :
    `venv\Scripts\python.exe tests\tester_moniteur.py --envoi-reel` doit journaliser `OK HTTP 200` ;
  - lecture ancree sur `^\s*(?P<libelle>[^:]+):\s*(?P<pct>\d+)%\|...` avec le libelle exige
    `Doing inference` : la barre `Sample frames: 16:` ne peut pas matcher (un libelle ne contient
    pas de `:`), donc plus d'oscillation 0-100 % ;
  - **chaque** envoi est journalise (`envois_<volet>.log`, une ligne par envoi) et un envoi
    reussi ecrit `dernier_envoi_<volet>.json` — c'est le battement de coeur qu'un watchdog
    externe doit lire, au lieu de surveiller la vivacite du processus.

  - `--commande-json FICHIER` fait surveiller un run SEGMENTE (`run_latentsync_segments.py`) au
    lieu de l'inference simple : meme surveillance GPU, meme statut, progression par tranche ;
  - l'arret d'urgence tue l'arbre de processus (voir ci-dessus) : sans ca, un arret en run
    segmente laisse l'inference tourner.

Tests sur cas fictifs, sans GPU et sans relancer LatentSync, a relancer apres toute modification
du moniteur :
  - `tests\tester_moniteur.py` rejoue les **23 085 fragments du log reel du volet 5** : 540 barres
    externes retenues sur 540, pourcentage monotone, derniere barre 538/538 a 100 %, quand
    l'ancien motif produisait **1 072 reculs** ; il verifie aussi la lecture des lignes de tranche
    et l'affichage de l'avancement global ;
  - `tests\tester_segments.py` verifie la taille des tranches (multiple du cycle, 60 % de la RAM
    libre en mode auto), le cablage de l'etape f (la commande du moniteur porte
    `--commande-json`, aucune inference n'est lancee) et le plan reel sur la boucle du volet 5.

## Checklist avant lancement GPU

- nvidia-smi  VRAM < 1500 Mo
- AUCUNE variable PYTORCH_CUDA_ALLOC_CONF (règle n°10 : la définir rend le rendu x22 plus lent)
- --source-max-dim 320 (jamais 512/384)
- Fichier source existe et lisible (ffprobe OK)
- Dossier de sortie vide
- Log prévu (Tee-Object -FilePath run.log)
- 2e terminal pour monitoring VRAM

## Checklist pendant l'exécution

- VRAM entre 4 et 6 Go (jamais 7+)
- GPU util entre 80 et 100 %
- Fichier de sortie qui grossit
- Aucun autre process GPU lancé

## Références de vitesse (RTX 3070 Ti, 8 Go)

LivePortrait 512p : 1,3 img/s (1h38, thrashing)
LivePortrait 320p : 3 img/s (44 min)
LivePortrait segmenté 320p : 5 img/s (26 min)
Wav2Lip HD : 40 fps (3 min)
Real-ESRGAN x4 tile=400 : 2,5 f/s (52 min)
libx265 CRF 18 : 1-3 fps CPU (45-90 min)

Total pipeline optimisé : ~2h (contre 4h sans optimisation).

## Compréhension

Thrashing : quand la VRAM est saturée, PyTorch déplace des tenseurs vers la RAM système. Chaque transfert PCIe coûte ~10 ms  des heures de latence.

Segmentation : chaque segment libère la VRAM. Reste à ~5 Go au lieu de 7,7 Go.

320p vs 512p : LivePortrait est entraîné sur des crops 256-512px. À 320px, différence après upscale 4K < 5%.

Moov atom : Wav2Lip lit le fichier entier pour compter les frames. Sans moov atom  division par zéro.