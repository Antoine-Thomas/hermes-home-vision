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

- **Driving Video Mismatch:** NEVER reuse an old driving video (from a previous script) for a new audio track. Lip-sync is tied to the driving video's timing; using an old one will result in \"mismatched mouth\" syndrome. Always re-run the audio-driven stage (SadTalker) before the video-driven stage (LivePortrait) when audio changes.
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
- **Check the source's loop seam before a long render.** A 5-6 s source reboucles ~50 times over a 5-min narration; if the first and last frames diverge, the jump repeats 50 times. Compare those two frames first.
- **Real sharpness gains come from magnification and real high frequencies, not from generative restoration.** Reducing the on-screen face square (e.g. 1080 → 720) multiplied on-screen mouth sharpness ×3.6 for free; GFPGAN gave 7 % and Real-ESRGAN 13-37 % for 30 min to 2 h. Recipe, decision tables and the validated transfer parameters: `references/mouth-sharpness.md`.
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
- **Un MP4 grossit pendant tout l'encodage sans etre lisible.** Un assemblage interrompu (taskkill,
  fin de session) laisse un fichier a la taille credible mais sans `moov` : `ffprobe` repond
  `moov atom not found`. Toujours `ffprobe` le fichier **final** avant de l'annoncer livre.
- **Chainer des filtres ffmpeg en Python : la variable porte le nom, pas les crochets.**
  `cour = "0:v"` puis `f"[{cour}][{idx}:v]overlay=..."` ; `cour = "[0:v]"` produit `[[0:v]][1:v]` et
  ffmpeg repond `Error parsing filterchain` / `Trailing garbage after a filter`. Test A/B sans
  fichier de sortie (`-f null -`) : `references/pipeline-bugs.md`.
- **Mesurer la forme racine d'un JSON produit par un autre outil avant de le parcourir.**
  `for k, v in x.items()` sur `mesures_hf.json` (une **liste** d'un dict par instant, ecrite par
  `hf_rapport.py`) lève `AttributeError: 'list' object has no attribute 'items'` a l'etape i, apres
  les heures de calcul. `print(type(d).__name__, len(d))` sur un fichier reel coute 5 secondes.

## Reference Files
- `references/echomimic-v2-setup.md`
- `references/mouth-sharpness.md` (measuring + restoring mouth sharpness)
- `references/latentsync-setup.md`
- `references/pipeline-bugs.md` (bugs du pipeline volet 6 : `_taille_segment`, `m.items()` sur une
  liste, double crochet ffmpeg, MP4 sans `moov`)
- `references/models-and-deps.md`
- `references/musetalk-setup.md`
- `references/liveportrait-troubleshooting.md` (ONNX/CUDA patches)
- `scripts/gfpgan_upscale.py`
