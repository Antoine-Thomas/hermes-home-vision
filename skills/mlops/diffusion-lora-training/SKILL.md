---
name: diffusion-lora-training
description: Use when training a local diffusion LoRA.
version: 1.0.0
license: MIT
platforms: [windows, linux]
metadata:
  hermes:
    tags: [lora, sdxl, stable-diffusion, diffusers, dreambooth, dataset-curation, insightface, vram, training]
    related_skills: [llm-ops, tts-voice-cloning, python-dependency-guard]
---

# Local diffusion LoRA training (face / style)

Building a dataset, training an SDXL or SD1.5 LoRA locally, and deciding with measurements whether
the chain is viable on this machine BEFORE committing hours of GPU or a photo session.

## Standing rules for this user

- **One dedicated venv per chain**, under `%LOCALAPPDATA%\hermes\data\<chain>\venv`. Never install
  into the existing AI venvs (LatentSync, XTTS, LTX-2.3, RAG) and never touch Hermes `config.yaml`.
- **Downloads are budgeted and announced.** Measure the real download before starting: torch alone
  can be 2.5 GB before the model. Price it and check the pip cache first — a wheel already cached
  costs nothing and leaves the whole budget for the model weight. Recipe and pin discipline:
  `references/dependency-budget-and-pins.md`.
- **Pin the library set in one command before installing anything else**, and never let a major
  version float: a fresh venv resolves the newest of everything, which is how a working chain breaks.
- **Short trial before any long run** (~300 steps, or 3 steps when diagnosing). No asset collection
  (photo session, dataset purchase) until the chain has produced a checkpoint.
- **On a dependency conflict: stop and report the exact error.** Do not improvise a workaround, and
  do not escalate to a heavier alternative (Docker, another framework) without an explicit go-ahead.
- **Report measured numbers only.** No checkpoint produced means "no images" — never describe,
  invent or extrapolate a generated image, and never invent a duration, a VRAM figure or a loss.

## Step 1 — triage the corpus on FACE size, not image resolution

A 6000x4000 frame where the subject stands 5 m away yields a 400 px face and is unusable; a phone
shot with a 1000 px face is ideal. Filtering on image resolution selects the wrong photos.

- Detect the face (InsightFace, well provided by the LatentSync venv). Require exactly one face,
  small side >= 512 px, large side >= 700 px.
- Sharpness = variance of the Laplacian measured **inside the face box**, never on the whole image.
- Exposure: reject when more than ~2 % of the face area is clipped at 0 or 255.
- Calibrating the sharpness threshold on the corpus median mechanically removes about half the
  corpus. That is acceptable as a first pass, but say it out loud: Laplacian variance is not
  comparable between a 24 Mpx close-up and a phone photo, so the cut is partly arbitrary.
- Classify the kept photos with a vision model in parallel batches (one subagent per <= 8 images,
  returning compact JSON): angle, expression, background, framing, and one `doute` boolean. Expect
  the vision model to contradict itself between passes — record the doubt instead of faking certainty.
- **Check the angle mix before training, not after.** Target for identity: ~35 % face, ~30 %
  three-quarter, ~20 % profile, ~15 % high/low angle. A corpus that is 75 % frontal trains a
  frontal-only identity; say so and let the user decide rather than reporting success.
- Crop a square centred on the face with ~1.5x the face size as margin, resize to the training
  resolution (1024 for SDXL), and keep the source photos read-only.

## Step 2 — captions

One caption per image: a unique trigger token plus the attributes read off the image (angle,
expression, light/background). **Keep the caption files in a folder OUTSIDE the image folder** —
see the pitfall below.

## Step 3 — model prep

- **kohya_ss no longer ships the command-line training scripts**: a clone gives the GUI only. Do not
  build a chain on it. Use the official diffusers example script instead
  (`examples/dreambooth/train_dreambooth_lora_sdxl.py`), which runs on the released PyPI diffusers.
- **Pin the library quartet before anything else**: `transformers<5` with the pair proven on the
  machine — `transformers==4.57.6` + `diffusers==0.36.0` + `peft>=0.17` + `accelerate>=1.4`. Letting
  transformers 5.x in breaks the diffusers and peft imports with messages that name peft and hide
  the real cause. Full rule in `mlops/llm-ops`.
- The example script needs the model in **diffusers format** (a folder), not a single-file
  checkpoint. Convert locally — no extra download:
  `StableDiffusionXLPipeline.from_single_file(src, torch_dtype=torch.float16).save_pretrained(dst)`.

## Step 4 — launch

```bash
V="$LOCALAPPDATA/hermes/data/sdxl_lora"
cd "$V" && "$V/venv/Scripts/python.exe" -m accelerate.commands.launch \
  --num_processes 1 --mixed_precision fp16 "$V/train_lora_sdxl.py" \
  --pretrained_model_name_or_path="$V/sdxl_base_diffusers" \
  --instance_data_dir="<images only>" --instance_prompt="<trigger>" \
  --resolution=1024 --train_batch_size=1 --gradient_accumulation_steps=4 \
  --gradient_checkpointing --optimizer=adafactor \
  --learning_rate=1e-4 --lr_scheduler=cosine --lr_warmup_steps=100 \
  --max_train_steps=3 --rank=16 --checkpointing_steps=500 --seed=42 \
  --output_dir="$V/lora_essai" --mixed_precision=fp16 --report_to=tensorboard
```

- Wrap the launch in `timeout <seconds>` for a hard cap, and sample VRAM independently in the
  background (`nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits` every 30 s into a
  file) so the max survives even if the run is killed at the cap. A ready-made sampler lives in
  `scripts/sampler_vram.sh`.
- Set `--checkpointing_steps` low enough that a trial actually writes something to test; a 500-step
  interval on a 3-step trial produces no artifact at all.
- Capture the run's log to a file and archive it before the next attempt overwrites it — an
  eight-line traceback is the whole diagnosis.

## Step 5 — decide with measurements, never with impressions

Measure, per trial: seconds per step (progress-bar timestamps), VRAM max (sampler file), loss
first/last, steps reached, and any error verbatim.

- **Sample `nvidia-smi` DURING the run and read `utilization.gpu` against `utilization.memory`.**
  100 % GPU with ~1 % memory means the kernels are slow, not the data path — that rules out
  swap/paging and points at compute.
- **Change one variable per trial and re-measure.** On a RTX 3070 Ti 8 GB, SDXL LoRA at 1024 px
  measured ~50 s/step and ~7.97 GB VRAM identically with 8-bit Adam/fp16, adafactor/fp16 and
  adafactor/bf16+tf32; at 768 px the VRAM was unchanged and the step was slower still.
- **If VRAM is identical across two resolutions, memory is not the bottleneck** — so a smaller
  model (SD 1.5) fixes OOM, not speed. Do not spend a download on the wrong axis, and say so when
  the obvious next move is the wrong one.
- Run 3 steps to price a step; only launch hundreds of steps once the per-step cost fits the time
  budget. The remaining axis when optimizer, precision and resolution are all ruled out is
  compute-side — see `references/training-speed-diagnostics.md`.

## Pitfalls

- **The diffusers example script treats every entry of `--instance_data_dir` as an image.** A `.txt`
  caption beside the images raises `UnidentifiedImageError`; a `captions/` subfolder raises
  `PermissionError`. The instance dir must contain images only, nothing else.
- **The example script's version guard rejects a PyPI install**: it raises
  "This example requires a source install from HuggingFace diffusers" through
  `check_min_version("<next>.dev0")`, because the released version is lower than a `.dev0`. No need
  to install from source — neutralize that single line and the script runs on the pinned release.
- **`--report_to=none` is not a valid value for accelerate 1.4** (`ValueError: Unsupported logging
  capability: none`). Install tensorboard and pass `tensorboard`.
- **Check a flag exists in the script's own argparse before using it.** `--use_adafactor` does not
  exist; the accepted form is `--optimizer=adafactor`. A guessed flag fails after the model load and
  wastes a full cycle.
- **A flag accepted by one version of accelerate is not accepted by another**: values that a tool
  documents as "none" or "off" may be rejected outright, and the error surfaces from the launcher,
  not from your script — read the traceback bottom-up to find whose parser refused it.
- **Do not present an untested hypothesis as a fix.** When optimizer, precision and resolution are
  all measured as irrelevant, report "the cause is compute-side, one variable at a time" — do not
  tell the user a specific option will solve it before it has been measured.

## Support files

- `references/training-speed-diagnostics.md` — slow-step decision table: symptom, what it rules out,
  the measurement to take next, plus the reference measurements above.
- `references/dependency-budget-and-pins.md` — caching and download-budget recipe, known-good pin
  sets, and why a dependency traceback usually names the wrong package.
- `scripts/sampler_vram.sh` — background VRAM sampler to pair with any launch.
