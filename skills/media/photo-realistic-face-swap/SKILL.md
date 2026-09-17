---
name: photo-realistic-face-swap
description: "Swap a face in a portrait and animate it via motion control."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [face-swap, insightface, motion-control, liveportrait, video, youtube]
    related_skills: [talking-head-video]
---

# Photo-Realistic Face Swap + Motion Control

## When to Use

- Replace the face in a portrait while keeping the body, pose, lighting and
  background, then animate the result with a driving video for a talking-head video.
- Legitimate use: swap the user's OWN portrait to a fictional/described face
  (privacy, avatar). NOT for non-consensual deepfakes.

## Workflow

```
source image + new face  →  face-swapped portrait  →  motion control (driving video)  →  assemble (bg + logo + audio)
```

### 1. Face swap (local, free)

Two DISTINCT cases — do not conflate them:

**A) Swap with a REFERENCE face (a real photo of another person):**
InsightFace `inswapper_128` (local, GPU via onnxruntime-gpu). See
`scripts/face_swap.py`. Detects faces in source + reference, then swaps.

**B) Generate a face from a TEXT DESCRIPTION ("homme barbu de 30 ans aux yeux verts"):**
InsightFace CANNOT do this — it swaps an EXISTING face, it does not generate one.
You need a text-to-image model FIRST:
- SD/FLUX + IP-Adapter (face conditioning), or
- SD/FLUX + ControlNet (keeps pose/background) to regenerate the portrait.
Then optionally swap with InsightFace. This path needs a diffusion model
(~4-7 GB) — NOT installed by default (ComfyUI is NOT installed on this box).

### 2. Motion control

- **Local (preferred, already set up):** LivePortrait at
  `data/video_youtube/liveportrait/` — driving video → animate the face
  (1024×1024). See `scripts/motion_control.py` and the `talking-head-video` skill
  (the incremental-write patch is REQUIRED for long videos).
- **Cloud (need API keys + internet):** Higgsfield Genjutsu, MiniMax, Kling.
  NOT local despite claims; MiniMax/Kling are paid/rate-limited cloud APIs.

### 3. Assembly (ffmpeg)

Concat animated video + looping Hermes background + logo + audio, 1080p NVENC.
Reuse `assemble_final_v4.py` or `assemble_liveportrait_final.py` in
`data/video_youtube/`.

## Setup (local face swap)

```bash
# in the LivePortrait venv (already has torch/numpy/opencv/onnxruntime)
uv pip install --python <liveportrait>/repo/venv/Scripts/python.exe insightface onnxruntime-gpu
# inswapper_128.onnx is NOT bundled — download from HF (e.g. deepinsight mirror)
# place it next to scripts/face_swap.py or pass the path
```

## Pitfalls

- `inswapper_128.onnx` is NOT bundled with insightface — download separately
  (~530 MB) from a HuggingFace mirror.
- Description→face is NOT an InsightFace feature; it needs SD/FLUX text-to-image.
- `onnxruntime-gpu` needs a CUDA build matching the CUDA toolkit; if it fails,
  fall back to CPU `onnxruntime` (slower but works).
- Cloud motion-control (Higgsfield/MiniMax/Kling) needs API keys and is not free/local.
- Screen-filming tips (60 Hz + 1/60 shutter, screen 50-60%, manual expo/WB 6000 K,
  slight off-axis for moiré) are for physical camera work, not this pipeline.

## Scripts

- `scripts/face_swap.py` — `replace_face(source, reference, output)` via InsightFace.
- `scripts/motion_control.py` — `animate_face(image, driving_video)` via LivePortrait.
