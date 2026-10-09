---
name: diffusion-lora-training
description: "Use when training a local SDXL or SD 1.5 LoRA."
version: 1.1.0
license: MIT
platforms: [windows, linux]
metadata:
  hermes:
    tags: [lora, sdxl, sd15, stable-diffusion, diffusers, dreambooth, kohya, sd-scripts,
           dataset-curation, captions, insightface, face-triage, video-source, wsl2, vram, training]
    related_skills: [llm-ops, tts-voice-cloning, python-dependency-guard]
---

# Local diffusion LoRA training (face / style)

Building a dataset, training an SDXL or SD1.5 LoRA locally, and deciding with measurements whether
the chain is viable on this machine BEFORE committing hours of GPU or a photo session.
The detail lives in `references/`; this file carries only the rules that must not be lost.

## Standing rules for this user

- **One dedicated venv per chain**, under `%LOCALAPPDATA%\hermes\data\<chain>\venv`. Never install
  into the existing AI venvs (LatentSync, XTTS, LTX-2.3, RAG) and never touch Hermes `config.yaml`.
- **Downloads are budgeted and announced.** Measure the real download before starting: torch alone can
  be 2.5 GB before the model. Price it and check the pip cache first — a wheel already cached costs
  nothing and leaves the whole budget for the model weight: `references/dependency-budget-and-pins.md`.
- **Pin the library set in one command before installing anything else**, and never let a major
  version float: a fresh venv resolves the newest of everything, which is how a working chain breaks.
- **Short trial before any long run** (~300 steps, or 3 steps when diagnosing). No asset collection
  (photo session, dataset purchase) until the chain has produced a checkpoint.
- **On a dependency conflict: stop and report the exact error.** Do not improvise a workaround, and
  do not escalate to a heavier alternative (Docker, another framework) without an explicit go-ahead.
- **Report measured numbers only.** No checkpoint produced means "no images" — never describe or
  extrapolate a generated image, and never invent a duration, a VRAM figure or a loss.

## Order that is not negotiable

1. **Triage the dataset before touching a trainer.** A LoRA is only as good as the mix it sees.
2. **Benchmark 3 steps before any long run** — never launch 500+ steps without a measured
   seconds-per-step from the exact same configuration.
3. **Report the end-of-run aggregate** (total elapsed ÷ completed steps), never a mid-run sample.
4. **Never buy the corpus before the pipeline runs** — more photos do not fix a broken stack.

## Step 1 — triage the corpus on FACE size, not image resolution

A 6000x4000 frame where the subject stands 5 m away yields a 400 px face and is unusable; a phone shot
with a 1000 px face is ideal. Full rules and thresholds: `references/face-triage.md`.

- Detect the face (InsightFace). Exactly one face, small side >= 512 px, large side >= 700 px.
- Sharpness = variance of the Laplacian **inside the face box**, renormalised to a fixed 256x256
  (INTER_AREA) before any comparison — raw values silently favour the lowest-resolution source.
- **Never** cut on a median threshold: use an absolute floor (~40) and report the distribution.
- Exposure: reject when more than ~2 % of the face area is clipped at 0 or 255.
- **Measure the angles**, do not classify them: InsightFace `face.pose` gives (pitch, yaw, roll) in
  degrees. Target ~35 % face / 30 % three-quarter / 20 % profile / 15 % high-low. A frontal-only set
  caps identity, and no number of extra steps fixes it.
- 25-35 images, 2-3 per burst. For a video source: `references/video-source-audit.md`.

## Step 2 — captions

- Form: `<trigger>, photo of <name>, <angle>, <expression>, <background>`; one trigger word, reused
  verbatim on every caption.
- **Captions live in a folder separate from the images** with the diffusers example (it opens every
  entry of the instance dir as an image); the kohya layout wants the `.txt` beside its image.
- Doubt handling, crop and rebalance rules: `references/face-triage.md`.

## Step 3 — model prep, and where to train

- **SD 1.5 at 512 px on Windows is the validated path on 8 GB** (1.8 s/step, 1800 steps validated);
  **SDXL at 1024 px is the case for WSL2.** Both hold by condition, not by preference.
- **Two kohya repositories**: `bmaltais/kohya_ss` is GUI-only, `kohya-ss/sd-scripts` carries the CLI.
  Alternative: the official diffusers DreamBooth example on the released PyPI diffusers.
- **Model format follows the trainer**: single-file `.safetensors` for kohya, diffusers-format folder
  for the example script (convert locally, `from_single_file(...).save_pretrained(...)`).
- Pin the quartet first: `transformers==4.57.6` + `diffusers==0.36.0` + `peft>=0.17` + `accelerate>=1.4`.
  Stack, dataset layout, benchmark command and failure table: `references/kohya-sd-scripts.md`;
  detailed procedure: `references/model-prep.md`.

## Step 4 — launch

- Launch under a hard `timeout` and pair it with a background VRAM sampler
  (`scripts/sampler_vram.sh`); keep `--checkpointing_steps` low enough that a trial writes an artifact.
- Archive the run log before the next attempt overwrites it — an eight-line traceback is the diagnosis.
- Full command and the SD 1.5 flag pitfalls (`--dataloader_num_workers=0`, `metadata.jsonl`,
  `lora_alpha`, `--checkpoints_total_limit`, `--random_flip`): `references/launch.md`.

## Step 5 — decide with measurements, never with impressions

- Measure per trial: **s/step as total ÷ completed steps**, VRAM max, loss first/last, steps reached,
  and every error verbatim.
- Sample `nvidia-smi` DURING the run: 100 % GPU with ~1 % memory rules out paging and points at compute.
- Change ONE variable per trial. If VRAM is identical across two resolutions, memory is not the
  bottleneck — SD 1.5 fixes OOM, not speed.
- Evaluation (weight sweep 0.6/0.8/1.0, plateau by correlation > 0.98, dataset beats steps, yaw
  measured on the output, contact sheet over a vision verdict): `references/measurement-discipline.md`.

## Hard rules

- **Pin `transformers` below 5** for anything touching diffusers, peft, LTX or SDXL — transformers 5.x
  breaks diffusers and peft imports with messages that name peft, not transformers.
- **Keep the new toolchain in its own venv**; never install into an existing AI venv.
- **Count the download budget before starting** — cu12x torch wheels bundle the CUDA runtime, so no
  CUDA toolkit is needed (~3 GB saved). Check the pip cache with a `--dry-run` first.

## Measurement discipline

- **Do not declare a long installation failed while it is still running.** A distro install queried too
  early answers `WSL_E_DISTRO_NOT_FOUND`, indistinguishable from a real failure, and the retry races
  the first attempt. Confirm completion before changing strategy.
- **The published s/step is the end-of-run aggregate.** The progress bar is a liveness check only: a
  bar read early gave "53 s/step" for a run whose final line said `485.88s/it` — a 9x error.
- **The library carries three divergent s/step figures for the same SDXL 1024 px configuration**
  (486 / 207 / 50-107) and a contradicted resolution effect: they are kept with their sources and
  flagged in `references/measurement-discipline.md`. **Do not publish a duration before re-measuring.**
- Report measurements as delivered, including correcting your own earlier figure; never fill a gap with
  a plausible value.
- **Drive measurements from a re-runnable `.py` file**, not inline code, with a flag that re-measures
  already-produced intermediates.

## Support files

- `references/face-triage.md` — face-size triage, renormalised sharpness, angle measurement, image count, crop, rebalance, captions.
- `references/model-prep.md` — Windows vs WSL2, the two kohya repos, model format, pins.
- `references/launch.md` — reference launch command, VRAM sampler, SD 1.5 flag pitfalls.
- `references/measurement-discipline.md` — what to measure, the divergent s/step figures, evaluation.
- `references/pitfalls.md` — WDDM spill, nvlddmkm, xFormers, diffusers-script traps, kohya rows.
- `references/training-speed-diagnostics.md` — slow-step decision table: symptom, what it rules out, the measurement to take next, plus the reference measurements.
- `references/dependency-budget-and-pins.md` — caching and download-budget recipe, known-good pin sets, and why a dependency traceback usually names the wrong package.
- `references/kohya-sd-scripts.md` — the WSL2 stack (Ubuntu import, venv, torch, sd-scripts), the kohya dataset layout, the 3-step benchmark command, and the trainer failure table.
- `references/video-source-audit.md` — auditing a clip as a face-dataset source: ffprobe spec reading, VFR check, even frame sampling, InsightFace pose, sharpness renormalisation, the face-px usability call, and Telegram preview delivery.
- `scripts/sampler_vram.sh` — background VRAM sampler to pair with any launch.
