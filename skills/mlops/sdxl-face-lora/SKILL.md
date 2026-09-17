---
name: sdxl-face-lora
description: Use when training an SDXL face LoRA on 8 GB VRAM.
---

# SDXL face LoRA on 8 GB VRAM

## Verdict measured on this machine (Windows 11, RTX 3070 Ti 8 GB)

| Config | s/step | VRAM |
|---|---|---|
| fp16 + 8-bit Adam @1024 | ~486 | 7970 Mo |
| fp16 + adafactor @1024 | 486 | 7979 Mo |
| bf16 + tf32 + adafactor @1024 | **767** | 7971 Mo |

300 steps = 40 h, 1500 steps = 8 days. **Not viable on Windows.** bf16 is 1.6x SLOWER
than fp16 here. VRAM is identical at 768 px and 1024 px and identical whatever the optimizer
— the bottleneck is the compute path, not memory. Same hardware under Linux runs SDXL LoRA at
3-8 s/step: **the fix is WSL2, not a bigger card.**

Never quote a progress-bar read taken mid-run as a per-step figure — read the FINAL average
(`3/3 [24:17<00:00, 485.88s/it]`). A partial reading overestimated speed 10x once.

## Chain (diffusers, not kohya)

`bmaltais/kohya_ss` no longer ships CLI training scripts; use the official diffusers example
`examples/dreambooth/train_dreambooth_lora_sdxl.py`. Versions that work together:
`transformers==4.57.6` + `diffusers==0.36.0` + `peft>=0.17` + `accelerate>=1.4` + `torch 2.4.1+cu118`.
Install torch from the pip cache (`--index-url .../cu118`) — cu121 downloads 2.45 GB more.
A single-file SDXL `.safetensors` must first be converted to a diffusers folder
(`StableDiffusionXLPipeline.from_single_file(...).save_pretrained(dir)`).

## Four pitfalls that each cost a run

1. `ImportError: This example requires a source install` → the script's `check_min_version("X.dev0")`
   refuses the released PyPI version. Neutralise that call; no source install needed.
2. `ValueError: Unsupported logging capability: none` → accelerate 1.4 rejects `--report_to=none`.
   Install tensorboard, use `--report_to=tensorboard`.
3. The script opens EVERY entry of the instance dir as an image: per-image `.txt` captions AND any
   subfolder crash it (`PIL.UnidentifiedImageError` / `PermissionError`). Keep the instance dir
   strictly image-only and pass the caption through `--instance_prompt`.
4. `--use_adafactor` does not exist in current examples — the flag is `--optimizer=adafactor`.

## Corpus triage — judge the FACE, not the image

A 6000x4000 shot taken from 5 m gives a 400x400 face (useless); a 1958x1958 portrait with a
1000x1000 face is ideal. Measure the detected face box: reject no face, >1 face, small side
<512 px, long side <700 px. Whatever the sharpness threshold, a median split mechanically removes
half the corpus — say so before applying it.

Angle variety matters more than count: 26 photos that are 77 % frontal yield a model that cannot
do profiles. Ask for profiles/three-quarters BEFORE committing to a full run.
