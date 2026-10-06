---
name: talking-head-video
description: Lip-sync a portrait to audio into a talking-head video.
version: 1.2.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [wav2lip, lip-sync, talking-head, video, youtube, torch, ffmpeg, tts]
---

# Talking-Head / Lip-Sync Video (Wav2Lip)

## When to Use

- Turn a single portrait/selfie + a narration audio into a video where the lips
  move with the speech (YouTube "faceless" avatar, explainer, promo).
- Pair with a cloned TTS voice (see `tts-voice-cloning`) for a fully AI-narrated video.
- NOT for photorealistic deepfakes — both tools produce clearly-AI output. Set
  that expectation up front: neither is true 4K (Wav2Lip ~720p, SadTalker 512×512;
  a 4K full-screen result is an upscale that goes soft).

## Choosing the tool

- **Wav2Lip** — lips-only: STATIC face, moving lips (96×96 mouth). Lighter/faster.
- **SadTalker** — full talking head: head pose + eyes/blink + neck + lips from a
  single image. Heavier (~2.5 GB models, ~8 GB VRAM, slow). Use when the user asks
  for "eyes, neck, head" movement, not just lips. Known to look a bit **rigid**.
  - **Checkpoint format:** Use `.safetensors` (SadTalker_V0.0.2_512.safetensors) — loads without missing `.pth` files.
  - **Output location:** Results appear in `repo/results/<timestamp>/` subdirectory.
  - **Old version flag:** Use `--old_version` when loading older checkpoint formats.
- **EchoMimicV2** — best free audio-driven talking head (Ant Group): natural
  half-body motion + hand gestures, markedly LESS RIGID than SadTalker; 2026
  reviews place it above Hallo2. Needs a **driving pose sequence** on top of
  image+audio (~12 GB models, ~6 GB VRAM fp16 on 8 GB). See `## EchoMimicV2` +
  `references/echomimic-v2-setup.md`.
- **LivePortrait** — best quality for re-enactment (driving video + source image):
  - **V7 settings (validated on RTX 3070 Ti 8 GB VRAM):**
    `--flag-stitching --flag-do-crop --flag-relative-motion --source-max-dim 512`
  - `--batch-size` is NOT a valid flag for `app.py`/`inference.py`/`run_liveportrait.py` — omit.
  - Source image should be square (512×512 or 1024×1024); driving video from SadTalker works well.
  - Output: `face_liveportrait.mp4` in `--output_dir`.
  - Patches for insightface CPU fallback already in place (CUDA 13.3 incompatible with onnxruntime-gpu 1.18).
- **MuseTalk v1.5** — lips-only redubbing, fast and light (~8.3 it/s UNet on the 3070 Ti).
  Keeps only **16 %** of the source's lower-face (mouth/chin) sharpness: the mouth is
  generated at 256×256, so the detail is not in the output at all. Setup procedure,
  blocking dependency pins and the required weight list: `references/musetalk-setup.md`.
  Runtime reality on 8 GB: ~55 min for a 5-min output, peak ~7.7 GB VRAM.
  - **LatentSync version trap:** on 8 GB VRAM only **1.5** (~6.5–8 GB) is viable.
    **1.6 needs ~18 GB** — check the version before starting a multi-GB download.
- **LatentSync 1.5** — best quality of the local lip-sync engines, heaviest. Keeps **58 %**
  of the source's lower-face sharpness — **3.6× MuseTalk** — so prefer it whenever mouth
  sharpness is the priority. Needs its own venv: its `requirements.txt` pins
  `torch==2.5.1`/cu121, incompatible with MuseTalk's 2.0.1/cu118. The repo's `main` branch,
  its `setup_env.sh` and its default `inference.sh` config are all **1.6** — the 1.5
  weights live in a separate HF repo and the default 512px config OOMs on 8 GB. Install
  order, the weight set and the config to swap in: `references/latentsync-setup.md`.
  Runtime reality on 8 GB (measured): peak ~7.9 GB VRAM, no batch-size flag exposed,
  and throughput degrades during the run (3.8 → 8.2 s/it over 25 min) — the tqdm ETA
  is optimistic, so budget roughly double what it shows.
- **MiniMax H3 (cloud API)** — image + text → talking portrait with no local
  GPU. Async: `POST https://api.minimax.io/v2/video_generation` (model
  `MiniMax-H3`) → poll `/v2/query/video_generation` for the URL. Requires a
  valid `eyJ...`-style MiniMax key (a `Sk-api-` key is rejected 1004 on every
  host). Full recipe in the `omniroute-gateway` skill's
  `references/minimax-provider.md`.

## LivePortrait (Recommended for Realism)

- **Best for Motion Control:** VIDEO-DRIVEN (not audio-driven). Uses a driving
  video (e.g. a SadTalker output) to transfer natural expressions + head movement
  onto a 1024×1024 source portrait.
- **Workflow:** 1. Generate driving video (SadTalker/EchoMimic) with audio -> 2. Transfer to 1024 portrait with LivePortrait.
- **Paramètres optimisés :**
  - `--flag_stitching` et `--flag_do_crop` : pour un meilleur alignement.
  - `--flag_relative_motion` : booléen, **défaut = True**. Le mouvement relatif normalise l'amplitude → bouche fermée (« dents serrées ») + jitter frame-à-frame (« l'image saute »). Pour une bouche ouverte et stable : `--no-flag_relative_motion` (mouvement absolu) + `--driving_multiplier 1.2` (amplification de la bouche). Retirer le flag NE suffit PAS — le défaut est déjà True.
  - `--flag_pasteback` : **CRITIQUE** pour éliminer les effets de miroir/clignotement sur les bords en réintégrant le visage dans le cadre original.
  - `--source_max_dim 512` : privilégier 512 pour la fluidité sur 8GB VRAM.
  - **Stabilisation (Denoising) :** LivePortrait est extrêmement sensible au jitter de la vidéo de conduite. Appliquez toujours un filtre de débruitage temporel (ex: `FFmpeg -vf hqdn3d=1.5:1.5:6:6`) sur la vidéo de conduite *avant* l'inférence.

## Identifier la provenance d'une video deja produite

Avant toute analyse d'image, lire la **signature du conteneur** : c'est la seule preuve dure
(Lap/vision ne prouvent rien seuls).

- **Pipeline local (ffmpeg)** : `major_brand isom` + `encoder Lavf<ver>` +
  `Lavc<ver> libx264` + audio **mono**. C'est ce qu'ecrivent MuseTalk, LatentSync, SadTalker,
  wav2lip, LivePortrait sur cette machine.
- **Export NLE (Adobe Premiere, encodeur MainConcept)** : `major_brand mp42` +
  `encoder "AVC Coding"` + `handler_name "Mainconcept ... Media Handler"` + audio **stereo**.
- **Un export NLE efface les tags de l'outil d'origine.** Apres un passage en montage, l'outil
  source n'est plus identifiable par les tags : repondre « non determinable » plutot qu'inventer.
- Indice complementaire : la presence du projet `.prproj` et des caches
  `Adobe Premiere Pro (Beta) *` dans le meme dossier, horodates juste avant le fichier, prouve
  l'export.

**Detecter un visage basse resolution recolle** (signature MuseTalk) : comparer la variance du
Laplacien du crop visage a celle d'un **patch de fond de meme taille**, les deux ramenes au meme
cote (256 px). Visage **plus mou** que le fond = visage genere petit puis upscale. Visage **plus
net** que le fond = profondeur de champ courte, donc pas de collage, donc pas MuseTalk.

**Une prise de vue reelle se reconnait au mouvement** : tete baissant jusqu'a sortir presque du
cadre, yeux qui se ferment, balayage de pitch de -77 a +19 deg. Un generateur pilote par un
portrait unique garde la tete dans le cadre (il perdrait le visage).

**Identite** : embeddings buffalo_l (`w600k_r50`), cosinus >= 0,55 = meme personne.

## Lessons and Pitfalls

- **Résoudre le chemin réel d'un asset AVANT de conclure qu'il manque.** Un chemin cité dans la
  demande peut être inexact : un **espace parasite avant l'extension** (`phototetepourHErmesANIMA .jpg`
  au lieu de `...ANIMA.jpg`) est courant dans les dossiers de cet utilisateur. Lister le dossier
  parent (`ls -la`) et reconstruire le chemin exact ; annoncer le chemin résolu avant de produire.
  Sous bash/MSYS utiliser `ls`, jamais `dir /b` (builtin cmd) : un `cannot access '/b'` ne dit rien
  de la présence du fichier.
- **Verifier la NARRATION avant de lancer le lip-sync, et ne jamais conclure d'un decodage fichier entier.** Un mot physiquement present peut ressortir absent du decodage global (memes octets, transcription differente selon la fenetre decodee) : localiser la phrase-ancres dans les jetons horodates et re-decoder la seule fenetre concernee avant de declarer une absence. Les scripts de verification prennent le chemin de l'audio ET les noms de log/json en arguments et estampillent chemin/md5/taille/date dans le JSON — sinon deux runs sur deux versions differentes du meme wav se confondent et les mesures d'une version sont attribuees a l'autre. Enfin la similarite brute (difflib) n'est pas un verdict : sigles epeles, noms propres, nombres en toutes lettres et composes doivent etre canonicalises des DEUX cotes avant de mesurer. Recettes et pieges : `references/verification-voix.md`.
- **Structure d'un volet de la série Hermes** (sauf indication contraire) : intro = salut + numéro du
  volet et sujet ; corps = explication technique adossée au schéma d'architecture fourni, en citant
  les composants/ports réels lus dans le `README`/`docs\` du projet (jamais inventés) ; clôture =
  CTA like/partage/abonnement + lien du dépôt affiché en grand. Durée : 5-6 min de voix (≈750-900 mots),
  16:9 YouTube. Compter les mots parlés en excluant les en-têtes (`grep -v '^#' fichier.md | grep -v '^---' | grep -v '^$' | wc -w`) : le total brut compte les titres et fausse l'estimation. Le montage (fond, logo en coin) est géré par `video-assembly`.
- **Avant de lancer un run de production, vérifier FFmpeg, les poids des modèles (`<outil>/repo/checkpoints/`), la photo source et l'audio, puis signaler les manquants et s'arrêter pour le GO.** L'utilisateur fait ces vidéos par étapes gatées et attend un rapport après chaque étape ; ne pas enchaîner directement sur un rendu long.
- **Driving Video Mismatch:** NEVER reuse an old driving video (from a previous script) for a new audio track. Lip-sync is tied to the driving video's timing; using an old one will result in \"mismatched mouth\" syndrome. Always re-run the audio-driven stage (SadTalker) before the video-driven stage (LivePortrait) when audio changes.
- **Plusieurs WAV de narration : concaténer et convertir AVANT le lip-sync.** Utiliser le demuxer concat d'ffmpeg puis rééchantillonner en mono 16 kHz PCM (ce que SadTalker attend) : `ffmpeg -f concat -safe 0 -i liste.txt -ar 16000 -ac 1 voix.wav`. Les moteurs ne prennent pas une liste de fichiers.
- **Verify LivePortrait flags against `argument_config.py` before running.** AI-generated commands carry non-existent flags (`--flag_use_cuda`, `--flag_absolute_motion`, `--mouth_ratio`, `--lip_sync_strength`, `--frame_smooth_window`, `--output_fps`). The real list is the `ArgumentConfig` dataclass (`src/config/argument_config.py`); CUDA is the default (the inverse is `--flag_force_cpu`). An unknown flag makes tyro fail immediately.
- **ONNX/CUDA Conflict (Windows):** Windows systems with CUDA 13.3+ and `onnxruntime-gpu` < 1.19 will crash if `insightface` or `HumanLandmark` try to use `CUDAExecutionProvider`.
  - **Fix:** Patch `model_zoo.py` (insightface) and `cropper.py` (LivePortrait) to force `providers=['CPUExecutionProvider']`. See `references/liveportrait-troubleshooting.md`.
- **Dents invisibles / bouche « fermée » :** SadTalker SANS `--enhancer gfpgan` rend les dents floues → impression de bouche fermée. Toujours `--enhancer gfpgan --preprocess full --size 512 --still` pour des dents nettes. La bouche ne s'ouvre qu'aux voyelles (moments de parole) — vérifier plusieurs frames. Source 1024×1024 nette (une source 512 floue donne un visage flou après upscale).
- **Sorties SadTalker (`--preprocess full`) :** deux mp4 sont produits — `...mp4` (crop 512×512, visage seul) et `..._full.mp4` (1024×1024, visage + fond). Pour l'assemblage fond flou, utiliser le `_full.mp4` : visage plus net (moins d'upscale) + fond propre à flouter.
- **Cadrage YouTube (photo source) :** recadrer/adapter la photo au format de la fenêtre YouTube (16:9 / vignette) AVANT l'animation — un simple crop centré ne suffit pas. Vérifier le cadrage final à l'écran YouTube.
- **Diction Issues:** Words like "Hermes Agent" may be cut. Use phonetic spelling (e.g., "Hermès ... Agent") in the TTS script.
- **VRAM Exhaustion (SadTalker/LivePortrait):** Sur 8GB VRAM, une saturation entraîne des échecs d'écriture du fichier final (`moov` atom absent). Vérifiez `nvidia-smi` avant tout rendu long.
- **Fluidité de lecture (Assembly):** PAS de `-r 30` en ENTRÉE — sur une source 25 fps, `-r 30 -i FACE` force 30 fps et TRONQUE la durée (376 s → 313 s, ratio 1.2). Laisser l'entrée à son fps natif ; `-r 30` uniquement en SORTIE (duplication de frames).
- **Fond d'assemblage : flou, pas miroir.** Le reflet vertical (vflip + vstack + scale) étire le visage en largeur et paraît déformé. L'utilisateur préfère un fond classique flou : visage net centré (1080×1080) sur un arrière-plan `gblur=sigma=30` de la même image étirée en 1920×1080.
- **Persist pipeline state to memory before launching a long render.** The chain (TTS → SadTalker → LivePortrait → assemble) runs ~1h and sessions get interrupted; un-persisted state forces the next session to re-derive commands and re-hit already-known errors. Before launching, save the current stage + exact commands + known issues to memory — this is a standing user requirement.
- **Prove a freshly installed tool by loading its models, not by checking that paths exist.** A `Test-Path` / `ls` on the venv python and the main checkpoint stays green through mmcv-version, mmpose-build and huggingface-hub-pin breakages — all three leave those files in place and fail only at import. Run the model-loading snippet (or a short inference) before reporting an install as done; a path check is not a verification.
- **When a spec or another AI hands you PowerShell cmdlets, translate them before running.** The Hermes terminal on this host is bash/MSYS, not PowerShell: `Test-Path` → `test -e`, `Get-PSDrive C` → `df -h /c`, `Get-ChildItem` → `ls`/`find`, `$env:X = "y"` → `export X=y`, `Select-Object`/`Format-List` → `grep`/`head`. Batch the translations into one `for` loop with a per-path OK/NOT-FOUND echo rather than firing one failing command per path.

- **Before running step N of a multi-step install, confirm step N-1's artifacts exist on disk.** A request for the "download the checkpoints" step does not imply the clone/venv step ran — the download then just creates an empty target dir in a repo that isn't there. Check the prerequisite first (`test -e <repo>/<venv>/Scripts/python.exe`), and when it is missing, say so and run it rather than proceeding. Never infer that a previous step happened.

- **"The mouth is blurry" is measured against the SOURCE VIDEO, not against a restored photo.** This user benchmarks lip-sync output against the original footage: a portrait that went through GFPGAN + Real-ESRGAN is *not* the reference. Measure Laplacian variance on the mouth/chin band of the output vs the same band of the source, and always report the **ratio** — the absolute value is meaningless without its display size.
- **Measure an engine's mouth quality on a short test BEFORE committing to a long render.** Both engines are hour-scale and neither exposes a batch knob to fix a bad run; a 10-second test clip through the same pipeline answers "is this engine good enough" in minutes. Do not discover the answer after the full render.
- **Both MuseTalk and LatentSync loop a short source in ping-pong, and build each output frame on the looped source frame.** `img, img[::-1], img, img[::-1]...` truncated to the audio length (MuseTalk `frame_list_cycle`; LatentSync `loop_video()` in `latentsync/pipelines/lipsync_pipeline.py`). Re-read the formula in the code rather than reciting it: `cycle = 2*n_src; j = i % cycle; k = j % n_src; src_idx = k if (j//n_src) even else n_src-1-k`. Because the mapping is deterministic, the source's real detail can be transferred onto the output — see `references/mouth-sharpness.md`.
- **Un pilote au moins aussi long que l'audio supprime le ping-pong.** Tant que `i < n_src`, `i % len(frame_list_cycle)` rend les frames dans l'ordre : la sortie est la tete de la source, tronquee a la duree de l'audio. Mesure : source etendue de 7 530 frames / 301,200 s + audio de 294,119 s -> 7 352 frames / 294,080 s, aucun rebouclage. Pour atteindre cette longueur depuis un clip court : `setpts=N*PTS` (ralenti) puis INTERPOLER vers le fps de livraison (`minterpolate=fps=25:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1`), puis repeter par `-stream_loop 4 -c copy` — un simple `fps=25` apres l'etirement ne fait que dupliquer des frames (image figee). Meme interpole, un ralenti 6x d'une prise a 60 fps rendue en 25 fps garde quelques pour cent de paires quasi identiques (mesure 250/7 528 = 3,3 %) : c'est inherent au ralenti et ca ne se juge pas sur la source — le critere « aucune image figee » se mesure sur la SORTIE du moteur (mesure 0/7 350 paires sous 0,05 de difference moyenne sur 0-255).
- **LatentSync par SEGMENTS : la sortie fait +2 frames par segment.** `latentsync/whisper/audio2feature.py::feature2chunks` boucle `while start_idx <= len(feature_array)` et le pipeline genere 1 frame par chunk : pour une tranche de N frames audio il sort N+2 frames. Consequence mesuree : chaque segment se cale sur l'audio a `19,6k` s mais se place dans la video a `19,68k` s, soit +80 ms de derive par segment (+1,2 s sur 15 segments) — la video finale depasse l'audio de 1,28 s. Corriger SANS reencodage : `ffmpeg -y -i out.mp4 -map 0 -c copy -frames:v <N> out_trim.mp4` (verifie : 490 frames / 19,600 s exact). `-c copy -t 19.6` NE coupe PAS (il laisse 492 frames) — seul `-frames:v` tranche, et c'est aussi ce qui rend la reprise (`tranche_video_valide`) compatible.
- **LatentSync 1.5, chiffres mesures (source 1920x1080, visage ~500 px, RTX 3070 Ti, stage2.yaml = resolution 256).** 490 frames en **217,5 s = 11,1x temps reel** — PAS 47,3x : ~50 s de chargement+passe de detection, ~130 s d'inference (31 fenetres de 16 frames), ~40 s d'ecriture tmp + muxage ffmpeg (GPU retombe a 0-37 %). RAM systeme pic 31,2 Go sur 63,9 (base 14,8 Go ; plateau 22,7 Go pendant l'inference, le pic tombe pendant l'ecriture video) ; VRAM pic 7867 Mio / 151 Mio libres, 72 degC. Les 2,84 Go de frames ne representent donc PAS le besoin : ajouter le checkpoint 5,07 Go dans torch, le contexte CUDA et les buffers pipeline. A retenir : diviser la duree cible par 47,3 surestime le run d'un facteur 4 ; mesurer le premier segment avant de projeter.
- **Options reelles de `scripts/inference.py` (LatentSync) :** `unet_config_path`, `inference_ckpt_path`, `video_path`, `audio_path`, `video_out_path`, `inference_steps`, `guidance_scale`, `temp_dir`, `seed`, `enable_deepcache`. `--resolution` et `--inference_pp_path` N'EXISTENT PAS — ne pas les passer, et `configs/unet/stage2_512.yaml` (resolution 512) fait sauter les 8 Go deja saturees par la config 256 (151 Mio libres au pic).
- **La nettete de la bouche d'une sortie LatentSync se mesure AVEC TEMOIN de codec.** Meme source, meme CRF, sans traitement : ici un reencodage CRF 18 rend 99,7 % de la source sur le visage, donc tout l'ecart restant est au modele. Mesure sur une tranche de 490 frames (source tres nette, 1920x1080, crops ramenes a 256 px de large) : visage entier 19,6 % de la source, bande basse bouche+menton **7,0 %**, fond 30,9 %. Le « 58 % de preservation du bas du visage » qui justifie le choix de LatentSync n'est PAS reproductible tel quel : le ratio n'est pas portable d'une source a l'autre (lapvar de la bande basse = 748 ici, contre 200-320 annonces pour du 1080p natif). Sur une source tres nette, attendre la greffe hautes frequences comme etape PORTEUSE, pas comme finition de confort.
- **MuseTalk, longue sortie 1080p : chiffres de reference et double encodage final.** 7 352 frames a 3,75 it/s (32 min 25 d'inference), ~78 min au total, landmarks ~6 it/s, ~20 Go de PNG ecrits par l'extraction de la source (verifier le disque avant). Le mux final de `scripts/inference.py` (`ffmpeg -i audio -i temp_vid out.mp4`, sans `-c:v copy`) RE-ENCODE la video puis supprime le temporaire : mesure 1,71 Mb/s en 1920x1080 alors que le temporaire etait en CRF 18. Quand le pique compte, conserver le temporaire et remuxer en copie de flux. VRAM pendant tout le run : 7 914 Mio / 8 192 — 104 Mio libres, ca tient, mais ne rien laisser d'autre sur le GPU.
- **Vérifier la synchro labiale sans voir l'image : une seule de quatre métriques tranche.** (1) mouvement de la moitié basse contre l'enveloppe audio : dominé par le mouvement de tête, 0,03-0,06 — non concluant. (2) contraste parole/silence sur la zone régénérée : rapport X1,03 (et X0,76 sur l'image entière) — non concluant, la tête ralentie bouge autant en silence. (3) l'audio de sortie est-il celui de la source ? décoder en PCM et corréler : 0,9997 au décalage 0 ms — nécessaire, mais ne prouve que l'absence de glissement audio. (4) corréler PIXEL PAR PIXEL la variation entre images consécutives avec l'enveloppe audio : la bouche se désigne elle-même. Mesuré max +0,209 contre une médiane de +0,048 sur l'image, les 8 pixels les plus corrélés groupés en un amas compact (la bouche), maximum au décalage 0,00 s ; contrôle avec l'audio décalé de +10 s : max +0,123 et AUCUN pixel au-dessus de 0,15. C'est la preuve à produire. Script prêt à l'emploi : `scripts/qa_tete_parlante.py`.
- **Check the source's loop seam before a long render.** A 5-6 s source reboucles ~50 times over a 5-min narration; if the first and last frames diverge, the jump repeats 50 times. Compare those two frames first.
- **Real sharpness gains come from magnification and real high frequencies, not from generative restoration.** Reducing the on-screen face square (e.g. 1080 → 720) multiplied on-screen mouth sharpness ×3.6 for free; GFPGAN gave 7 % and Real-ESRGAN 13-37 % for 30 min to 2 h. Un aller-retour lanczos upscale->downscale ne cree AUCUN detail (il ne fait que redistribuer l'existant) : le seul gain vient de la restauration. Et `GFPGANer(upscale=2, bg_upsampler=None)` sort a **2x** la taille d'entree — ce 2x EST l'etape « upscale » d'un aller-retour 4K, RealESRGAN est inutile pour cette moitie. Recipe, decision tables and the validated transfer parameters: `references/mouth-sharpness.md`.
- **`cv2.Laplacian` refuses float32 with `CV_64F`** ("Unsupported combination of source format (=5), and destination format (=6)"). Convert to uint8 and use `CV_32F` — this bites every sharpness script otherwise.
- **Keep the coordinate space straight when measuring.** Three coexist in this pipeline (source frame, face crop, 1920×1080 canvas). Measure inside the crop's own frame and add the overlay offset only for the canvas — a 1080-wide crop image given canvas coordinates yields an empty region and silently invalidates every number.
- **`GFPGANer.enhance()` returns 3 values, `RealESRGANer.enhance()` returns 2.** Unpacking 3 from the latter raises `ValueError: not enough values to unpack`.
- **The Laplacian alone can lie.** Ghost/duplicate contours add high-frequency energy and inflate the score — a version measured at 90 % of the source was in fact covered in double lip edges. Confirm every sharpness number with a visual check on a frame with the mouth OPEN.

- **Ne PAS utiliser le test « bas du visage vs haut du visage » pour detecter une signature de
  basse resolution.** Teste le 19/09 : le controle positif (sortie MuseTalk connue, montee en
  1080p) donne 1,376, soit le meme ratio qu'une vraie prise de vue (1,365), alors que les sources
  reelles donnent 0,53-0,59. Le test est confondu par le montage : il ne permet aucune conclusion.
  Ne pas le rejouer.
- **La periodicite de boucle (ping-pong 2N) n'est pas toujours detectable dans la sortie.**
  Autocorrelation temporelle testee sur 4 videos : aucun creux marque, y compris sur des sorties
  de moteurs. Son absence **n'exclut pas** MuseTalk/LatentSync (la bouche est regeneree a chaque
  cycle). Ne pas conclure de l'absence.
- **La variance du Laplacien depend de l'echelle : normaliser avant toute comparaison.** A netete
  egale, un visage de 1000 px mesure ~8x moins qu'un visage de 350 px. Compare a l'oeil, un lot
  4K annoncait un ecart x13 avec une 720p ; apres recalage du crop a 256x256 l'ecart reel etait
  x1,25. Sans normalisation on inverse la conclusion. Le raccourci « 720p plus nette que du 4K »
  est presque toujours un artefact de mesure.
- **`find /c/ -maxdepth 6` ne trouve PAS les outils installe : ils sont sous
  `data\video_youtube\<outil>`, soit une profondeur 8 depuis `C:\`.** Chercher avec `maxdepth 8`
  ou lister directement `data\video_youtube\*/` — sinon on conclut a tort « non installe » et on
  recommande une installation qui n'a pas lieu d'etre.
- **Les poids des modèles sont sous `<outil>/repo/checkpoints/`, pas `<outil>/checkpoints/`.** Un `checkpoints/` absent à la racine de l'outil ne prouve pas que l'outil est incomplet : lister `sadtalker/repo/checkpoints/` (epoch_20.pth, SadTalker_V0.0.2_512.safetensors), `wav2lip/repo/checkpoints/` (wav2lip_gan.pth) et `LatentSync/checkpoints/` avant de conclure.
- **Prouver qu'un outil est installe par `import torch` dans son venv, pas par `ls`.** Le
  repertoire survit a toutes les casses d'import ; un `ls` vert ne prouve rien. Verifier aussi que
  `torch.cuda.is_available()` est True avant d'annoncer que l'outil est pret.

- **Dependances du venv : ne JAMAIS `pip install numpy` sans pin.** Le venv LatentSync est en
  Python 3.10 ; numpy 2.x (roue cp311) casse `cv2` (`No module named 'numpy._core._multiarray_umath'`,
  le suffixe cp311 est le diagnostic) et numpy 2.x casse `scikit-image` 0.22.0
  (`numpy.dtype size changed ... Expected 96 from C header, got 88`). Etat verifie : Python 3.10.11 +
  numpy 1.26.4 + scikit-image 0.22.0, a installer par le fichier de contraintes
  `data\video_youtube\requirements-latentsync.txt` (tableau de compatibilite et commandes de
  verification : `tts-voice-cloning/references/dependances-venv.md`).
- **Un graphe ffmpeg avec des images en `-loop 1` doit porter `-shortest` (ou `-t`), sinon
  l'encodage ne finit JAMAIS.** Les entrees image sont infinies : sans borne ffmpeg encode jusqu'a
  l'arret force, le fichier grossit sans limite et l'index `moov` n'est ecrit qu'a la toute fin —
  `ffprobe` repond `moov atom not found` sur le fichier livre. C'est la cause reelle des
  « assemblages qui prennent 1 h a 3 h » : le meme rendu de 336 s finit en ~6 min avec `-shortest`,
  contre 2 h 31 sans (4 h 48 de video generee, `speed=1.91x`). Controle AVANT de lancer : la ligne
  de progression (`time=`) ne doit pas depasser la duree de l'audio, sinon le graphe est non borne.
  Controle APRES : fin = plus aucun process `ffmpeg` **et** taille stable 60 s, puis `ffprobe` du
  fichier **final** (jamais de l'entree), avec `nb_frames` = `duration x fps`. Ne pas deduire la
  taille attendue d'un run precedent non borne. Detail : `references/pipeline-bugs.md`.
- **Chainer des filtres ffmpeg en Python : la variable porte le nom, pas les crochets.**
  `cour = "0:v"` puis `f"[{cour}][{idx}:v]overlay=..."` ; `cour = "[0:v]"` produit `[[0:v]][1:v]` et
  ffmpeg repond `Error parsing filterchain` / `Trailing garbage after a filter`. Test A/B sans
  fichier de sortie (`-f null -`) : `references/pipeline-bugs.md`.
- **Une image statique en boucle se decode a 1 im/s, pas a 25.** `["-loop", "1", "-framerate",
  "1", "-i", png]` pour chaque PNG d'incrustation : 5 PNG a 25 im/s = 125 decodages/s pour rien.
  Le framerate de sortie reste `-r 25` (l'overlay repete la derniere image).
- **Reglages d'encodage YouTube par defaut : `-preset fast -crf 20`** (jamais `medium`/`crf 18`) :
  meme qualite visuelle, 3-5x plus rapide (le volet 6 a passe 2 h 30 la-dessus). Consequence a
  accepter : 217 Mo pour 336 s — la fourchette « 400-700 Mo » venait de runs non bornes.
- **Un `ffmpeg` lance par `subprocess.run` survit a l'echec du script et garde un coeur pendant des
  heures** (volet 6 : deux ffmpeg infinis en parallele, 2 h 30 au lieu de 15 min). Envelopper
  l'appel et tuer l'orphelin :
  `except: subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], capture_output=True); raise`.
- **La duree cible d'un volet est la duree reelle du dernier `sortie_latentsync_<volet>*.mp4`**
  (greffe `_hf` prioritaire), lue par `ffprobe` et passee en `-t` en plus de `-shortest` : jamais
  une valeur ronde. Volet 6 : 336,44 s.
- **La reference de format et de duree est le volet precedent publie, verifiee `>= 60 s` au
  demarrage du run.** Mesure du 23/09 : `tutotete19.mp4` (donne comme reference) dure 19,12 s alors
  que le volet precedent reel (`tutotete20_jev_llmwiki.mp4`) dure 336,40 s. Sous 60 s : arreter et
  demander la bonne reference.
- **Versionner les scripts du pipeline** : `data\video_youtube\` est gitignore, donc un correctif
  applique seulement la-bas ne survit pas a une reinstallation. Copier (jamais deplacer) le gabarit
  dans `%LOCALAPPDATA%\hermes\scripts\video\` apres chaque correction.
- **Mesurer la forme racine d'un JSON produit par un autre outil avant de le parcourir.**
  `for k, v in x.items()` sur `mesures_hf.json` (une **liste** d'un dict par instant, ecrite par
  `hf_rapport.py`) lève `AttributeError: 'list' object has no attribute 'items'` a l'etape i, apres
  les heures de calcul. `print(type(d).__name__, len(d))` sur un fichier reel coute 5 secondes.

- **MuseTalk : la version 1.5 (2025-03-28) EST la derniere publiee — il n'existe pas de v2.**
  Verifier avant de proposer une mise a jour : `ls models/musetalkV15/` (unet.pth + musetalk.json)
  et `git log -1` sur le depot. `--version v15` etait deja passe sur les runs ANIMA (config
  `configs/inference/anima_v7.yaml`).
- **MuseTalk v1.5 : `--bbox_shift` est un leurre, le code le force a 0.** `scripts/inference.py`
  fait `if args.version == "v15": bbox_shift = 0  # v15 uses fixed bbox_shift`. Les deux seuls
  leviers restants sont `--extra_margin` (marge basse du recadrage) et la position du visage —
  aucun ne touche la resolution. Ne pas promettre un gain de nettete par `--bbox_shift`.
- **La resolution de la bouche de MuseTalk se lit dans le code, pas dans la doc :
  `scripts/inference.py` fait `crop_frame = cv2.resize(crop_frame, (256,256), INTER_LANCZOS4)`
  sur la bbox du visage.** Consequence directe : **agrandir la bbox ne peut que DILUER la
  bouche** (meme grille de 256 pour une zone plus grande). C'est la preuve dure a citer quand on
  demande « plus de nettete » a MuseTalk. Le README lui-meme renvoie a un modele de
  super-resolution pour depasser 256x256.
- **Une passe de restauration (GFPGAN / Real-ESRGAN) ne peut pas sauver une bouche generee a
  256x256, et un aller-retour upscale->downscale est un no-op de detail.** Donc une « methode 2 »
  du type upscaler la source x2 avant MuseTalk ne change rien : le crop est ramene a 256x256
  quelle que soit la resolution d'entree.
- **Un visage PLEIN CADRE n'est pas toujours une magnification.** Verifier la chaine reelle :
  ici `scale=1920:1080` sur une source deja 1920x1080 est un NO-OP, donc `crop=640:1080` est un
  recadrage 1:1 et passer en plein cadre sans crop garde l'echelle 1:1 — le gain de nettete de la
  correction bouche survit. La regle « la nettete chute au carre de l'agrandissement » ne
  s'applique qu'a un zoom/recadrage effectif. Lire la chaine de filtre avant d'annoncer une perte.
- **`-vsync` a ete SUPPRIME de ffmpeg (n9) : `Unrecognized option 'vsync'`.** Utiliser
  `-fps_mode passthrough` (ou `cfr`/`vfr`). Erreur classique en extrayant une frame par
  `select=eq(n\,N)`.
- **insightface tourne sur GPU ici : ne pas forcer le CPU par reflexe.** Avec onnxruntime 1.21
  (`get_available_providers()` -> Tensorrt/CUDA/CPU) et `providers=["CUDAExecutionProvider","CPUExecutionProvider"]`,
  la detection tombe a **0,024 s/frame (2,9 min pour 7352 frames)** contre 0,49 s/frame en CPU
  (60 min) — bbox et det_score identiques. Le patch « forcage CPU » ne concerne que
  onnxruntime-gpu < 1.19.
- **`select='between(n,N0,N1)'` reedecode depuis la frame 0 a chaque appel.** Pour sonder
  quelques instants, extraire les frames UNE fois en PNG (`-vf select='eq(n\,A)+eq(n\,B)...'
  -fps_mode passthrough`) et lire les PNG ensuite : sinon chaque mesure relance un decodage
  complet et la cadence s'effondre avec l'indice des frames.
- **`vision_analyze` n'est pas un instrument de mesure de nettete.** Sur une planche
  SOURCE | brut | 3 doses, il a classe la SOURCE comme la PLUS FLOUE (mesure : lapvar 244,9
  contre 15,0) et invente des halos sur la variante qui n'en a pas. Sur un agrandissement
  nearest x6 il hallucine des contours doubles partout. S'en servir pour lire un cadrage, jamais
  pour trancher une nettete ou un fantome : mesurer, puis faire trancher l'oeil humain.
- **Le parametre de delai de l'outil terminal est `timeout`, pas `timeout_s`.** `timeout_s`
  appartient a l'outil navigateur et est ignore silencieusement : la commande retombe au defaut
  et est coupee a 180 s, ce qui ressemble a un plantage du script.
- **Contre-controler une mesure AVANT de conclure : meme fichier, meme CRF, sans le traitement.**
  Comparer les pics de gradient d'un brut CRF 23 a une sortie CRF 16 mesure le codec, pas la
  greffe — premier passage de ce test, il faisait apparaitre un faux fantome. Encoder un
  temoin sans traitement au meme CRF, puis mesurer `corr(sortie - temoin, hp_source)` : c'est ce
  qui distingue de l'information injectee d'un bruit de prediction x264.
- **Une trame horizoncale du visage n'est pas la zone des levres.** Les bandes `levre_sup` /
  `levre_inf` couvrent toute la largeur du visage : elles incluent les joues. Sur le fichier
  livre elles affichaient 94 % / 66 % alors que la boite des levres (landmarks) affichait 7,1 %.
  Mesurer la boite des landmarks, et annoncer les deux.
- **Verifier a propos de la zone de test demandee par l'utilisateur qu'elle contient bien ce
  qu'il croit.** `x 900-1050, y 500-600` sur ANIMA 1920x1080 tombe sur le nez/philtrum : les
  levres sont a y 640-712 selon la frame. Mesurer la zone demandee ET la vraie boite de la
  bouche, et signaler l'ecart plutot que de repondre uniquement sur la zone nommee.

## Post-traitement d'une video deja rendue (GFPGAN / Real-ESRGAN)

- **Les poids GFPGAN/facexlib se resolvent par rapport au CWD, pas a l'installation.** `GFPGANer`
  vaut `model_rootpath='gfpgan/weights'` : lancer la passe depuis un dossier sans `gfpgan/weights/`
  fait echouer le chargement (poids de detection/parsing/alignment introuvables). Placer les 4
  fichiers — `GFPGANv1.4.pth`, `parsing_parsenet.pth`, `detection_Resnet50_Final.pth`,
  `alignment_WFLW_4HG.pth` — dans `<cwd>/gfpgan/weights/` ; ils sont deja tous dans
  `sadtalker/repo/gfpgan/weights/`. Les **lier en dur** (`os.link`, meme volume) plutot que les
  copier : plusieurs centaines de Mo dupliques pour rien.
- **Ne jamais lancer une passe GFPGAN/Real-ESRGAN pendant qu'un rendu SadTalker occupe le GPU.**
  Sur 8 Go le rendu culmine deja a ~5,8 Go et l'enhancer demande 1-2 Go de plus : enchainer, pas
  parallelliser. Declencher la passe sur le **marqueur d'achevement** du run (le JSON de rapport
  contenant `fin` et le `sha256` du mp4 livre), jamais sur la vivacite du process ni sur l'ETA
  affichee ; et prevoir une sortie de secours si aucun fichier de log ne bouge pendant plusieurs
  minutes (run mort).
- **Valider le code d'une passe post-traitement sur CPU pendant que le rendu tient le GPU.**
  3 images d'un clip court suffisent : chargement des poids, detection du visage, **forme de la
  sortie** et bbox du visage (a reutiliser comme zone de mesure de nettete). C'est ce controle qui
  revele les erreurs de forme. En revanche la cadence CPU (mesuree ~29 s/image) n'est PAS une ETA
  GPU : ne jamais la citer comme duree de la passe.
- **Une passe sur 10 000 images ne se fait pas en PNG.** Extraire puis relire chaque frame en PNG
  4K (~16 Mo piece) sature le disque : alimenter ffmpeg par un pipe `rawvideo`
  (`-f rawvideo -pix_fmt bgr24 -s WxH -r 25 -i -`) avec l'mp4 d'origine en 2e entree pour
  recuperer l'audio. `scripts/gfpgan_upscale.py` utilise le chemin PNG (fichiers temporaires) :
  acceptable sur un clip court, a eviter sur une narration complete.

## Reference Files
- `references/echomimic-v2-setup.md`
- `references/mouth-sharpness.md` (measuring + restoring mouth sharpness)
- `references/latentsync-setup.md`
- `references/pipeline-bugs.md` (bugs du pipeline talking head : `_taille_segment`, `m.items()` sur
  une liste, double crochet ffmpeg, graphe non borne / `moov` absent, PNG a 25 im/s, ffmpeg
  orphelin, reference de 19 s et duree cible reelle)
- `references/models-and-deps.md`
- `references/musetalk-setup.md`
- `references/verification-voix.md` (verifier une narration avant le lip-sync : tracabilite du run,
  decodage cible d'un mot, canonicalisation des familles OOV, chiffres a rapporter)
- `references/liveportrait-troubleshooting.md` (ONNX/CUDA patches)
- `scripts/gfpgan_upscale.py`
- `scripts/qa_tete_parlante.py` (contrôle d'une sortie de tête parlante : conteneur, images
  figées, glissement audio, synchro labiale par corrélation pixel/enveloppe + contrôle décalé)
