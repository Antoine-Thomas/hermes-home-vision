---
name: lora-training
description: "Use when training an image-model LoRA (SDXL, SD 1.5)."
version: 1.0.0
platforms: [windows, linux]
metadata:
  hermes:
    tags: [lora, sdxl, kohya, sd-scripts, dataset, captions, finetune, wsl2]
    related_skills: [llm-ops, tts-voice-cloning]
---

# LoRA training for image models

Training an identity/style LoRA (SDXL, SD 1.5) on a local corpus: dataset triage, captioning,
toolchain setup, and the benchmark that decides whether a long run is worth starting.

## Order that is not negotiable

1. **Triage the dataset before touching a trainer.** A LoRA is only as good as the mix it sees.
2. **Benchmark 3 steps before any long run.** Never launch 500+ steps without a measured
   seconds-per-step from the exact same configuration. Three steps cost minutes and either
   green-light the real run or save hours.
3. **Report the end-of-run aggregate, never a mid-run sample.** See the measurement pitfall below.
4. **Never buy the corpus before the pipeline runs.** Do not run a photo session for more
   training material while the trainer itself is unproven — more photos do not fix a broken stack.

## Dataset triage — judge by FACE, not by image

- **Measure the detected face bounding box in pixels, not the image resolution.** A 6000x4000
  frame shot from 5 m gives a ~400x400 px face and is unusable; a 1958x1958 frame with a
  1000x1000 px face is perfect. Use a face detector (InsightFace) to get the box.
- Reject: no face, more than one face, small side < 512 px, long side < 700 px.
- Sharpness: variance of the Laplacian **inside the face box only**, never the whole image.
  Calibrate the threshold on the corpus median — and say plainly that a median threshold
  removes half the corpus by construction. Offer to lower it rather than silently discarding
  photos that are probably fine.
- Exposure: reject if any region of the face sits at 0 or 255 over more than ~2 % of its area.
- **Enforce an angle/expression mix or you will not get one.** Count the angles after triage.
  A corpus that is ~77 % frontal trains a model that only renders frontal faces: state the
  distribution and its consequence instead of declaring the dataset "fine".
- Aim for 25-35 images; keep 2-3 per burst, never 10 from the same series.
- Vision classification of angle/expression can contradict itself between passes. Keep the modal
  value, flag the photo, and list the doubtful ones for the user to arbitrate — do not hide the
  uncertainty, and do not treat a doubtful label as fact when building the captions.

## Captions

- Default form: `<trigger>, photo of <name>, <angle>, <expression>, <background>`.
- Pick one short unique trigger word and reuse it verbatim.
- **Keep the caption files in a folder separate from the images** when the trainer is the
  diffusers DreamBooth example — that script opens every entry of the instance directory as an
  image. See the failure table in `references/kohya-sd-scripts.md`.

## Where to train

- **Windows is the wrong host for SDXL LoRA.** Measured on a RTX 3070 Ti (8 GB, fp16, batch 1,
  gradient checkpointing): ~486 s/step at 1024 px, with **identical VRAM (~7970 MB) at 1024 px
  and at 768 px**. Changing the optimizer (8-bit Adam vs adafactor), the precision (fp16 vs
  bf16 + tf32) and the resolution moved the step time by under 2 %. The GPU sat at 100 %
  utilisation with the memory controller at ~1 % — a compute-side pathology, not a memory
  ceiling. Do not spend an evening tuning flags on Windows to fix it: move to WSL2.
- **WSL2 is the path.** GPU passthrough works out of the box (the Windows driver serves CUDA
  inside WSL) and `torch.cuda.is_available()` returns True without any driver work. Setup and
  exact commands: `references/kohya-sd-scripts.md`.
- Everything below the trainer is verified; the WSL training **speed** still has to be measured
  with the 3-step benchmark before promising a user a completion time.

## Hard rules

- **Pin `transformers` below 5** for anything touching diffusers, peft, LTX or SDXL.
  transformers 5.x breaks diffusers and peft imports with messages that name peft, not
  transformers. Proven pair on this machine: `transformers==4.57.6` + `diffusers==0.36.0`
  (+ `peft>=0.17`, `accelerate>=1.4`).
- **Keep the new toolchain in its own venv** and never install into an existing AI venv
  (XTTS, LatentSync, LTX-2.3 and the ComfyUI embedded python stay untouched).
- **Count the download budget before starting.** A CUDA toolkit from NVIDIA's repo is not needed
  when you use `cu12x` torch wheels (they bundle the CUDA runtime, and WSL supplies
  `libcuda.so`) — skipping it saves ~3 GB. Prefer a torch wheel already in the pip cache: check
  with a `--dry-run` install before downloading anything large.
- A trainer that accepts a **single-file `.safetensors`** checkpoint avoids the whole class of
  "diffusers-format folder is incomplete" failures. Prefer it when both are available.

## Measurement discipline (this cost two wrong reports)

- **Read the end-of-run aggregate, not a mid-run progress bar.** A live bar read early and
  divided by hand gave "53 s/step" for a run whose final line said `3/3 [24:17, 485.88s/it]` —
  a 9x error already reported before it was caught. Read the final summary line, or divide total
  elapsed by completed steps, and say which one you did.
- **Do not declare a long installation failed while it is still running.** A distro install
  queried too early answers `WSL_E_DISTRO_NOT_FOUND`, indistinguishable from a real failure; the
  retry then races the first attempt and wastes work. Confirm completion before changing strategy.
- Report measurements as delivered, including correcting your own earlier figure. Say which
  number is verified and which is an estimate; never fill a gap with a plausible value.

## References

- `references/kohya-sd-scripts.md` — the WSL2 stack (Ubuntu import, venv, torch, sd-scripts),
  the kohya dataset layout, the 3-step benchmark command, and the trainer failure table.
