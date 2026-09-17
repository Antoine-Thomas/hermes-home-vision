---
name: talking-head-video
description: Lip-sync a portrait to audio into a talking-head video.
version: 1.1.0
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
  for \"eyes, neck, head\" movement, not just lips. Known to look a bit **rigid**.
- **EchoMimicV2** — best free audio-driven talking head (Ant Group): natural
  half-body motion + hand gestures, markedly LESS RIGID than SadTalker; 2026
  reviews place it above Hallo2. Needs a **driving pose sequence** on top of
  image+audio (~12 GB models, ~6 GB VRAM fp16 on 8 GB). See `## EchoMimicV2` +
  `references/echomimic-v2-setup.md`.

## LivePortrait (Recommended for Realism)

- **Best for Motion Control:** VIDEO-DRIVEN (not audio-driven). Uses a driving
  video (e.g. a SadTalker output) to transfer natural expressions + head movement
  onto a 1024×1024 source portrait.
- **Workflow:** 1. Generate driving video (SadTalker/EchoMimic) with audio -> 2. Transfer to 1024 portrait with LivePortrait.
- **Paramètres optimisés :**
  - `--flag_stitching` et `--flag_do_crop` : pour un meilleur alignement.
  - `--flag_relative_motion` (ex: 0.8) : pour des mouvements plus fluides.
  - `--flag_pasteback` : **CRITIQUE** pour éliminer les effets de miroir/clignotement sur les bords en réintégrant le visage dans le cadre original.
  - `--source_max_dim 512` (ou 1024) : pour limiter la distorsion sur les sources haute résolution.

## Lessons and Pitfalls

- **Driving Video Mismatch:** NEVER reuse an old driving video (from a previous script) for a new audio track. Lip-sync is tied to the driving video's timing; using an old one will result in \"mismatched mouth\" syndrome. Always re-run the audio-driven stage (SadTalker) before the video-driven stage (LivePortrait) when audio changes.
- **ONNX/CUDA Conflict (Windows):** Windows systems with CUDA 13.3+ and `onnxruntime-gpu` < 1.19 will crash if `insightface` or `HumanLandmark` try to use `CUDAExecutionProvider`.
  - **Fix:** Patch `model_zoo.py` (insightface) and `cropper.py` (LivePortrait) to force `providers=['CPUExecutionProvider']`. See `references/liveportrait-troubleshooting.md`.
- **Diction Issues:** Words like \"Hermes Agent\" may be cut. Use phonetic spelling (e.g., \"Hermès ... Agent\") in the TTS script.
- **VRAM Exhaustion (SadTalker):** On 8GB cards, SadTalker 512 may thrash. Patch `make_animation.py` to move the generator to CPU (`.cpu()`) after weight loading. It increases render time (~1.3s/it) but prevents total OOM/thrash (from 14h down to 1h for 5min video).
- **LivePortrait render time scales steeply with `--source_max_dim`:** at 1024 a 5-min render can stall for hours on 8GB VRAM (GPU util drops, the output MP4 never gets its `moov` atom — kill it); at 512 the same render finishes in ~40min. Prefer `--source_max_dim 512` for full-length videos; use 1024 only for short clips or when the extra sharpness justifies the risk.
- **Persist pipeline state to memory before launching a long render.** The chain (TTS → SadTalker → LivePortrait → assemble) runs ~1h and sessions get interrupted; un-persisted state forces the next session to re-derive commands and re-hit already-known errors. Before launching, save the current stage + exact commands + known issues to memory — this is a standing user requirement.

## Reference Files
- `references/echomimic-v2-setup.md`
- `references/models-and-deps.md`
- `references/liveportrait-troubleshooting.md` (ONNX/CUDA patches)
- `scripts/gfpgan_upscale.py`
